# author: picklez
# version: 1.2.0
# purpose: this file contains helper classes and functions for
# the main runner script!

# imports
import os
import psutil
import sys
import multiprocessing
import threading
import time
from tqdm import tqdm
import math
from datetime import datetime
import copy
import matplotlib.pyplot as plt
import matplotlib
from datetime import date, timedelta
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import LETTER
from textwrap import wrap
from pypdf import PdfMerger

matplotlib.rc('font', size=6)
matplotlib.use('agg')
cwd = os.getcwd()
amt_to_buy = 1
amt_to_buy_funds = 15
date_to_start_at = 2000
funds_to_compare_to = ["^IXIC", "^DJI", "^GSPC"]
process_count = 8

class kicker2:
    def get_wb_distro_days(ticker, config_dict): # returns worst, best day as tuple
        # find the log we want 1st
        log_fldr = config_dict["file_7"]
        log_2_find = ticker+"_"
        log_fn = ""
        for log in os.listdir(log_fldr):
            if log_2_find in log:
                if ticker[0] == log[0] and log[len(ticker)] == "_":
                    log_fn = log_fldr+log
        # then we need to open it and find the worst/best day 2nd
        r_log = open(log_fn, "r")
        hold_1 = {}
        hold_5 = {}
        re = r_log.read().split("\n")
        re.pop(-1)
        for line in re:
            h = []
            h = line.split(": ")
            if "1" in h[0]:
                hold_1[int(h[1])] = h[0]
            if "5" in h[0]:
                hold_5[int(h[1])] = h[0]
        return hold_1[list(sorted(hold_1))[-1]][0:3], hold_5[list(sorted(hold_5))[-1]][0:3]
        
    def get_wb_vectors(ticker, config_dict, worst, best):
        src_vector_file = config_dict["file_9"]+ticker+config_dict["csv"]
        whole_vector_dict = kicker.parse_prexisting_dictionary(src_vector_file)
        worst_dict = {}
        best_dict = {}
        for key in whole_vector_dict:
            worst_dict[key] = whole_vector_dict[key][worst]
            best_dict[key] = whole_vector_dict[key][best]
        return worst_dict, best_dict
    
    def get_info_to_put_in_pdf(ticker, config_dict):
        # basically this function returns all the information that we would like to be able to put into a pdf
        worst_day, best_day = kicker2.get_wb_distro_days(ticker, config_dict)
        # we also will want to return the worst/best vectors from source files
        # so that we can use them in comparison in another function when creating
        # the executive summary
        worst_dict, best_dict = kicker2.get_wb_vectors(ticker, config_dict, worst_day, best_day)
        return worst_day, best_day, worst_dict, best_dict
        
    def get_timelist_for_comparison(config_dict):
        start_dt = date(2000,1,1)
        end_dt = date.today()
        delta = timedelta(days=1)
        dates = []
        while start_dt < end_dt:
            if start_dt.weekday() != 5 and start_dt.weekday() != 6:
                dates.append(start_dt.isoformat())
            start_dt += delta
        return dates
        
    def pdf_summary15_creator(config_dict, truth_table):
        # this will be the function that creates the executive summary stuff
        # it will make 2 versions; 1 with overall best, and 1 with overall best with dividends
        # first, we read in the data we want to compare...
        all_analysis_dict = {}
        div_analysis_dict = {}
        for ticker in truth_table:
            worst_day, best_day, worst_dict, best_dict = kicker2.get_info_to_put_in_pdf(ticker, config_dict)
            all_analysis_dict[ticker] = [worst_day, best_day, worst_dict, best_dict]
            if truth_table[ticker][0] == 1:
                div_analysis_dict[ticker] = [worst_day, best_day, worst_dict, best_dict]
        # now we need to get the timelist for comparison and iterating through...
        timelist = kicker2.get_timelist_for_comparison(config_dict)
        funds_dict = {}
        for fund_ticker in funds_to_compare_to:
            funds_dict[fund_ticker] = all_analysis_dict.pop(fund_ticker)
            div_analysis_dict.pop(fund_ticker)
        
        # alrighty, now that we have a timelist that we can use for look up, we are good!
        # time to start ranking!
        all_rankings = {"worst":{},"best":{}}
        div_rankings = {"worst":{},"best":{}}
        for date in timelist:
            all_rankings["worst"][date] = {}
            all_rankings["best"][date] = {}
            div_rankings["worst"][date] = {}
            div_rankings["best"][date] = {}
            for ticker in all_analysis_dict:
                if date in all_analysis_dict[ticker][2]:
                    all_rankings["worst"][date][ticker] = all_analysis_dict[ticker][2][date][3]
                if date in all_analysis_dict[ticker][3]:
                    all_rankings["best"][date][ticker] = all_analysis_dict[ticker][3][date][3]
            for ticker in div_analysis_dict:
                if date in div_analysis_dict[ticker][2]:
                    div_rankings["worst"][date][ticker] = div_analysis_dict[ticker][2][date][3]
                if date in div_analysis_dict[ticker][3]:
                    div_rankings["best"][date][ticker] = div_analysis_dict[ticker][3][date][3]
            
            # time to reorder and make properly ranked!
            all_rankings["worst"][date] = sorted(all_rankings["worst"][date].items(), key=lambda x:x[1], reverse=True)
            all_rankings["best"][date] = sorted(all_rankings["best"][date].items(), key=lambda x:x[1], reverse=True)
            div_rankings["worst"][date] = sorted(div_rankings["worst"][date].items(), key=lambda x:x[1], reverse=True)
            div_rankings["best"][date] = sorted(div_rankings["best"][date].items(), key=lambda x:x[1], reverse=True)
        
        for date in reversed(timelist): # this removes all blank data!
            if len(all_rankings["worst"][date]) == 0 and len(all_rankings["best"][date]) == 0 and len(div_rankings["worst"][date]) == 0 and len(div_rankings["best"][date]) == 0:
                timelist.pop(timelist.index(date))
                del all_rankings["worst"][date]
                del all_rankings["best"][date]
                del div_rankings["worst"][date]
                del div_rankings["best"][date]
        
        # now that everything is sorted, it is time to start making an executvie summary of the 15 best...
        all_best_15 = {"worst":{},"best":{}}
        div_best_15 = {"worst":{},"best":{}}
        for date in all_rankings["worst"]:
            all_best_15["worst"][date] = all_rankings["worst"][date][:15]
        for date in all_rankings["best"]:
            all_best_15["best"][date] = all_rankings["best"][date][:15]
        for date in div_rankings["worst"]:
            div_best_15["worst"][date] = div_rankings["worst"][date][:15]
        for date in all_rankings["best"]:
            div_best_15["best"][date] = div_rankings["best"][date][:15]
            
        # now we need to find the # of occurences that each thing was in the top 15...
        all_total_count = {"worst":{},"best":{}}
        div_total_count = {"worst":{},"best":{}}
        # now lets initialize targets so we don't get pesky errors
        for ticker in all_analysis_dict:
            all_total_count["worst"][ticker] = 0
            all_total_count["best"][ticker] = 0
        for ticker in div_analysis_dict:
            div_total_count["worst"][ticker] = 0
            div_total_count["best"][ticker] = 0
        # now lets count all occurences!
        for date in all_best_15["worst"]:
            for item in all_best_15["worst"][date]:
                all_total_count["worst"][item[0]] += 1
        for date in all_best_15["best"]:
            for item in all_best_15["best"][date]:
                all_total_count["best"][item[0]] += 1
        for date in div_best_15["worst"]:
            for item in div_best_15["worst"][date]:
                div_total_count["worst"][item[0]] += 1
        for date in div_best_15["best"]:
            for item in div_best_15["best"][date]:
                div_total_count["best"][item[0]] += 1
        # now lets remove all 0 counts!
        to_remove = []
        for ticker in all_total_count["worst"]:
            if all_total_count["worst"][ticker] == 0:
                to_remove.append(ticker)
        for item in to_remove:
            del all_total_count["worst"][item]
        to_remove = []
        for ticker in all_total_count["best"]:
            if all_total_count["best"][ticker] == 0:
                to_remove.append(ticker)
        for item in to_remove:
            del all_total_count["best"][item]
        to_remove = []
        for ticker in div_total_count["worst"]:
            if div_total_count["worst"][ticker] == 0:
                to_remove.append(ticker)
        for item in to_remove:
            del div_total_count["worst"][item]
        to_remove = []
        for ticker in div_total_count["best"]:
            if div_total_count["best"][ticker] == 0:
                to_remove.append(ticker)
        for item in to_remove:
            del div_total_count["best"][item]
        # now lets sort it all
        all_total_count["worst"] = sorted(all_total_count["worst"].items(), key=lambda x:x[1], reverse=True)
        all_total_count["best"] = sorted(all_total_count["best"].items(), key=lambda x:x[1], reverse=True)
        div_total_count["worst"] = sorted(div_total_count["worst"].items(), key=lambda x:x[1], reverse=True)
        div_total_count["best"] = sorted(div_total_count["best"].items(), key=lambda x:x[1], reverse=True)
        
        # we need a master list of all of the things that we need to append to the document without collisions... basically at least...
        master_list = {}
        sub_lists = [all_total_count["worst"], all_total_count["best"], div_total_count["worst"], div_total_count["best"]]
        for list in sub_lists:
            for tuple in list:
                if tuple[0] not in master_list:
                    master_list[tuple[0]] = tuple[1]
                if tuple[0] in master_list:
                    if master_list[tuple[0]] > tuple[1]:
                        master_list[tuple[0]] = tuple[1]
        master_list = sorted(master_list.items(), key=lambda x:x[1], reverse=True)
        composite_best_15 = master_list[:15]
        
        # time to start making the executive summary pdf!
        canvas = Canvas("executive_summary.pdf", pagesize=LETTER)
        canvas.setFont("Times-Roman",12)
        # remember canvas is 8.5 inch by 11 inch!
        title_for_pdf = "SPI_Research_4 - Executive Summary of Processed Data"
        
        # we need figures for stuff based on our data!
        figure_making.create_composite_figure_v2(config_dict, all_analysis_dict, composite_best_15, timelist, funds_dict)
        
        canvas.setFont("Times-Roman",12)
        canvas.drawCentredString((4.25*inch), (10*inch), title_for_pdf)
        canvas.drawInlineImage(config_dict["file_6"]+"composite_growth_vector_chart"+config_dict["png"],(0.5*inch),(5*inch),(8*inch),(5*inch))
        canvas.showPage()
        
        canvas.setFont("Times-Roman",12)
        canvas.drawInlineImage(config_dict["file_6"]+"composite_buy_days_table"+config_dict["png"],(0.25*inch),(5.5*inch),(8*inch),(5*inch))
        canvas.drawInlineImage(config_dict["file_6"]+"composite_growth_vector_table"+config_dict["png"],(0.25*inch),(0.5*inch),(8*inch),(5*inch))
        canvas.drawCentredString((4.25*inch), (9.5*inch), "Top 15 Best & Worst Days to Buy On")
        canvas.drawCentredString((4.25*inch), (5.5*inch), "Composite Growth Vector % Return to Most Recent Date")
        canvas.drawCentredString((4.25*inch), (10*inch), title_for_pdf)
        canvas.showPage()
        
        canvas.setFont("Times-Roman",12)
        canvas.drawInlineImage(config_dict["file_6"]+"funds_buy_days_table"+config_dict["png"],(0.25*inch),(5.5*inch),(8*inch),(5*inch))
        canvas.drawInlineImage(config_dict["file_6"]+"funds_growth_vector_table"+config_dict["png"],(0.25*inch),(0.5*inch),(8*inch),(5*inch))
        canvas.drawCentredString((4.25*inch), (5.5*inch), "Funds Growth Vector % Return to Most Recent Date")
        canvas.drawCentredString((4.25*inch), (8.5*inch), "Funds Best & Worst Days to Buy On")
        canvas.drawCentredString((4.25*inch), (10*inch), title_for_pdf)
        canvas.showPage()
        
        canvas.save()
        
        if "cover_page.pdf" in os.listdir():
            pdf_merger = PdfMerger()
            pdf_merger.append(cwd+"\\cover_page.pdf")
            pdf_merger.append(cwd+"\\executive_summary.pdf")
            pdf_merger.write(cwd+"\\executive_summary.pdf")
        
        return

class figure_making:
    def get_year_axis_lines(timelist, x):
        # recieves x & timelist so that we can make reference points for the graphs...
        year_lines = []
        for date in timelist:
            year, month, day = str(date).split("-")
            if month == '01' and int(day) <= 4:
                year_lines.append(date)
        begin_year_of_ls = int(list(str(year_lines[0]).split("-"))[0])
        end_year_of_ls = int(list(str(year_lines[len(year_lines)-1]).split("-"))[0])
        to_remove = []
        for i in range(begin_year_of_ls, end_year_of_ls+1):
            sub_items = []
            for item in year_lines:
                if str(str(i)+"-") in item:
                    sub_items.append(item)
            if len(sub_items) > 1:
                for sitem in range(1,len(sub_items)):
                    to_remove.append(sub_items[sitem])
        for thing_to_remove in to_remove:
            year_lines.pop(year_lines.index(thing_to_remove))
        x_tl_index = []
        for first_year_date in year_lines:
            x_tl_index.append(x[timelist.index(first_year_date)])
        return year_lines, x_tl_index
        
    def write_composite_reports(worst_dict, best_dict, config_dict):
        write_file_fn = config_dict["file_8"]+"composite_best_15_output"+config_dict["csv"]
        write_file = open(write_file_fn, "w")
        for date in worst_dict:
            write_file.write(date+", "+str(worst_dict[date][0])+", "+str(worst_dict[date][1])+", "+str(best_dict[date][0])+", "+str(best_dict[date][1])+"\n")
        write_file.close()
        return
    
    def create_composite_figure_v2(config_dict, all_analysis_dict, composite_best_15, timelist, funds_dict): # ignore for right now...
        # we first need to get our time axis...
        x = []
        for i in range(len(timelist)):
            x.append(i)
        x = reversed(x)
        x = list(x)
        year_lines, x_tl_index = figure_making.get_year_axis_lines(timelist, x)
        
        # we need to process worst/best vectors for each of our funds...
        NASDAQ_worst_dict = funds_dict["^IXIC"][2]
        NASDAQ_best_dict = funds_dict["^IXIC"][3]
        DJIA_worst_dict = funds_dict["^DJI"][2]
        DJIA_best_dict = funds_dict["^DJI"][3]
        SMP500_worst_dict = funds_dict["^GSPC"][2]
        SMP500_best_dict = funds_dict["^GSPC"][3]
        
        funds_weekdays = []
        funds_weekdays.append(["NASDAQ", str(funds_dict["^IXIC"][0]), str(funds_dict["^IXIC"][1])])
        funds_weekdays.append(["DJIA", str(funds_dict["^DJI"][0]), str(funds_dict["^DJI"][1])])
        funds_weekdays.append(["S&P500", str(funds_dict["^GSPC"][0]), str(funds_dict["^GSPC"][1])])
        
        NASDAQ_worst_vector = []
        NASDAQ_best_vector = []
        DJIA_worst_vector = []
        DJIA_best_vector = []
        SMP500_worst_vector = []
        SMP500_best_vector = []
        
        for date in NASDAQ_worst_dict:
            NASDAQ_worst_vector.append(round(((NASDAQ_worst_dict[date][1]/(NASDAQ_worst_dict[date][2]+0.000000000001))-1)*100,2))
        for date in NASDAQ_best_dict:
            NASDAQ_best_vector.append(round(((NASDAQ_best_dict[date][1]/(NASDAQ_best_dict[date][2]+0.000000000001))-1)*100,2))
        for date in DJIA_worst_dict:
            DJIA_worst_vector.append(round(((DJIA_worst_dict[date][1]/(DJIA_worst_dict[date][2]+0.000000000001))-1)*100,2))
        for date in DJIA_best_dict:
            DJIA_best_vector.append(round(((DJIA_best_dict[date][1]/(DJIA_best_dict[date][2]+0.000000000001))-1)*100,2))
        for date in SMP500_worst_dict:
            SMP500_worst_vector.append(round(((SMP500_worst_dict[date][1]/(SMP500_worst_dict[date][2]+0.000000000001))-1)*100,2))
        for date in SMP500_best_dict:
            SMP500_best_vector.append(round(((SMP500_best_dict[date][1]/(SMP500_best_dict[date][2]+0.000000000001))-1)*100,2))
        
        # now we need to make our worst and best aggregate vector axis lines...
        worst = {}
        best = {}
        composite_output = []
        # aggregation vector loop
        for ticker_tuple in composite_best_15:
            worst_dict = all_analysis_dict[ticker_tuple[0]][2]
            best_dict = all_analysis_dict[ticker_tuple[0]][3]
            for date in worst_dict:
                if date in worst and date in best:
                    # do that addition...
                    worst[date][0] = round(worst[date][0]+worst_dict[date][1],2)
                    worst[date][1] = round(worst[date][1]+worst_dict[date][2],2)
                    best[date][0] = round(best[date][0]+best_dict[date][1],2)
                    best[date][1] = round(best[date][1]+best_dict[date][2],2)
                else:
                    # add the addition...
                    worst[date] = [0, 0]
                    best[date] = [0, 0]
                    worst[date][0] = round(worst[date][0]+worst_dict[date][1],2)
                    worst[date][1] = round(worst[date][1]+worst_dict[date][2],2)
                    best[date][0] = round(best[date][0]+best_dict[date][1],2)
                    best[date][1] = round(best[date][1]+best_dict[date][2],2)
            composite_output.append([str(ticker_tuple[0]), str(all_analysis_dict[ticker_tuple[0]][0]), str(all_analysis_dict[ticker_tuple[0]][1])])
        # growth vector determinations
        ymax = 0
        worst_growth_vector = []
        best_growth_vector = []
        for date in worst:
            worst_growth_vector.append(round(((worst[date][0]/worst[date][1])-1)*100,2))
            if round(((worst[date][0]/(worst[date][1]+0.000000000001))-1)*100,2) > ymax:
                ymax = round(((worst[date][0]/(worst[date][1]+0.000000000001))-1)*100,2)
        for date in best:
            best_growth_vector.append(round(((best[date][0]/best[date][1])-1)*100,2))
            if round(((best[date][0]/best[date][1])-1)*100,2) > ymax:
                ymax = round(((best[date][0]/best[date][1])-1)*100,2)
        
        # now we generate a growth vector figure for humans to understand!
        growth_vector_fig = plt.plot(x, best_growth_vector, x, worst_growth_vector, linewidth=0.5, color="g", label="BBI")
        growth_vector_fig = plt.plot(x, NASDAQ_worst_vector, x, NASDAQ_best_vector, linewidth=0.5, color="m", label="NASDAQ")
        growth_vector_fig = plt.plot(x, DJIA_worst_vector, x, DJIA_best_vector, linewidth=0.5, color="b", label="Dow Jones")
        growth_vector_fig = plt.plot(x, SMP500_worst_vector, x, SMP500_worst_vector, linewidth=0.5, color="y", label="S&P500")
        growth_vector_fig = plt.legend(loc="upper left")
        growth_vector_fig = plt.title("Composite Growth Vectors for Investment $ Cost Avg/Time (Jan 1, 2000 to Present)")
        growth_vector_fig = plt.xlabel("N Days Considered in Vector")
        growth_vector_fig = plt.ylabel("Total % Growth")
        growth_vector_fig = plt.axhline(y=0, linestyle="--")
        growth_vector_fig = plt.vlines(x=x_tl_index, ymin=0, ymax=ymax, linestyle="--", color="r", linewidth=0.1)
        growth_vector_fig = plt.savefig(config_dict["file_6"]+"composite_growth_vector_chart"+config_dict["png"], dpi=1000)
        growth_vector_fig = plt.close()
        growth_vector_fig = plt.clf()
        plt.close(growth_vector_fig)
        plt.pause(0.1)
        time.sleep(0.1)
        
        # now lets output a data table!
        labels = ["Year Vector Start", "N days Considered Total", "% Growth on Worst Vector", "% Growth on Best Vector"]
        all_output = []
        for x_date_point in x_tl_index:
            sub_output = []
            sub_output.append(str(year_lines[x_tl_index.index(x_date_point)]))
            sub_output.append(str(x_date_point))
            sub_output.append(str(list(reversed(worst_growth_vector))[x_date_point])+"%")
            sub_output.append(str(list(reversed(best_growth_vector))[x_date_point])+"%")
            all_output.append(sub_output)
        table_figure = plt.table(cellText=all_output, colLabels=labels, loc="center")
        ax = plt.gca()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        table_figure = plt.box(on=None)
        table_figure = plt.savefig(config_dict["file_6"]+"composite_growth_vector_table"+config_dict["png"], dpi=1000)
        table_figure = plt.clf()
        plt.close(table_figure)
        plt.pause(0.1)
        time.sleep(0.1)
        
        # now lets output the composite output table!
        labels = ["Stock Ticker", "Worst Day to Buy Stock", "Best Day to Buy Stock"]
        composite_figure = plt.table(cellText=composite_output, colLabels=labels, loc="center")
        ax = plt.gca()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        composite_figure = plt.box(on=None)
        composite_figure = plt.savefig(config_dict["file_6"]+"composite_buy_days_table"+config_dict["png"], dpi=1000)
        composite_figure = plt.clf()
        plt.close(composite_figure)
        plt.pause(0.1)
        time.sleep(0.1)
        
        figure_making.write_composite_reports(worst, best, config_dict)
        
        funds_labels = ["Year Vector Start", "N days Considered Total", "% Growth WV-NASDAQ", "% Growth BV-NASDAQ", "% Growth WV-DJIA", "% Growth BV-DJIA", "% Growth WV-S&P500", "% Growth BV-S&P500"]
        funds_all_output = []
        for x_date_point in x_tl_index:
            sub_output = []
            sub_output.append(str(year_lines[x_tl_index.index(x_date_point)]))
            sub_output.append(str(x_date_point))
            sub_output.append(str(list(reversed(NASDAQ_worst_dict))[x_date_point])+"%")
            sub_output.append(str(list(reversed(NASDAQ_best_dict))[x_date_point])+"%")
            sub_output.append(str(list(reversed(DJIA_worst_dict))[x_date_point])+"%")
            sub_output.append(str(list(reversed(DJIA_best_vector))[x_date_point])+"%")
            sub_output.append(str(list(reversed(SMP500_worst_vector))[x_date_point])+"%")
            sub_output.append(str(list(reversed(SMP500_best_vector))[x_date_point])+"%")
            funds_all_output.append(sub_output)
        table_figure_funds = plt.table(cellText=funds_all_output, colLabels=funds_labels, loc="center")
        ax = plt.gca()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        table_figure_funds = plt.box(on=None)
        table_figure_funds = plt.savefig(config_dict["file_6"]+"funds_growth_vector_table"+config_dict["png"], dpi=1000)
        table_figure_funds = plt.clf()
        plt.close(table_figure_funds)
        plt.pause(0.1)
        time.sleep(0.1)
        
        funds_labels = ["Fund", "Worst Day to Buy Stock", "Best Day to Buy Stock"]
        fund_figure = plt.table(cellText=funds_weekdays, colLabels=funds_labels, loc="center")
        ax = plt.gca()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        fund_figure = plt.box(on=None)
        fund_figure = plt.savefig(config_dict["file_6"]+"funds_buy_days_table"+config_dict["png"], dpi=1000)
        fund_figure = plt.clf()
        plt.close(fund_figure)
        plt.pause(0.1)
        time.sleep(0.1)
        
        return

class kicker:
    def main_task(ticker, config_dict, truth_table, master_dict, pid_index):
        # lets localize some things to simplify
        ticker_truth = truth_table[ticker]
        ticker_dict = master_dict[ticker]
        
        # lets make a function that lets us see if it has already done this stock; if so then it will skip it
        precheck_file_name = config_dict["file_9"]+ticker+config_dict["csv"]
        if os.path.isfile(precheck_file_name) is True:
            # lets open the prexisting file
            read_prexisting_output_file = open(precheck_file_name, "r")
            # lets get the length of the prexisting file
            pre_of_len = len(read_prexisting_output_file.readlines())
            # then we can close the file
            read_prexisting_output_file.close()
            # now lets get the length of our current dictionary
            length_of_dict = len(list(ticker_dict["stock"].keys()))
            
            # finally, we can determine if we need to just skip entirely or update the prexisting vectors
            if pre_of_len == length_of_dict: # we can assume that if the dataset hasn't already been outputted then no other files have been outputted!
                #parsed_prexisting_dict = kicker.parse_prexisting_dictionary(precheck_file_name)
                return
            if pre_of_len < length_of_dict:
                # we need to process an update vector rather than process full from scratch...
                # we need to make a slice of the master_dict to do a subprocessing step...
                # first we need to parse the prexisting dictionary so that it matches the same structure as
                # one of the output dictionaries...
                parsed_prexisting_dict = kicker.parse_prexisting_dictionary(precheck_file_name)
                
                # last day in the file dict (vector to update)
                lf_day = list(parsed_prexisting_dict.keys())[-1]
                
                # first things first, we need to make a copy of the stock_dict and slice it down and just process the update vector...
                # essentially, figuring out where the file leaves off and updating it with the update vector generated
                days_list = list(ticker_dict["stock"].keys())
                update_vector_list = days_list[days_list.index(lf_day):] 
                # include the lf_day in it so that if there is missing time, buys can be applied properly to make up for
                # need to make sure we have our dictionary setup...
                update_v1_dict = {}
                update_v1_dict["stock"] = {}
                if "split" in ticker_dict:
                    update_v1_dict["split"] = ticker_dict["split"]
                if "div" in ticker_dict:
                    update_v1_dict["div"] = ticker_dict["div"]
                    
                # now get the content for the update vector
                for day in update_vector_list:
                    update_v1_dict["stock"][day] = ticker_dict["stock"][day]
                
                # now that we have an update vector, lets get the dictionary to update the whole dictionary...
                update_v1_vector_dict = kicker.iterate_through_v1(ticker, config_dict, ticker_truth, update_v1_dict, pid_index)
                
                # now that we have that generated as an update vector dictionary, we need to backwards update all the instances in the file dictionary,
                # then we can reoutput it to file!
                # the only part of the output vector that we need to use for the update is the first instance in the update vector
                # we need to remove the actual first before though, because it will be the last of the other previous vector and will create collisions otherwise
                update_v1_vector_dict.pop(list(update_v1_vector_dict.keys())[0])
                first_instance_of_update_vector = update_v1_vector_dict[list(update_v1_vector_dict.keys())[0]]
                
                # also going to need a reference dictionary to lookup stuff in order to process the updates to % stuff
                lookup_dict = {}
                if ticker in funds_to_compare_to:
                    lookup_dict = kicker.get_reference_dict_v1(ticker_dict, amt_to_buy_funds)
                else:
                    lookup_dict = kicker.get_reference_dict_v1(ticker_dict, amt_to_buy)
                avg_price = lookup_dict[list(lookup_dict)[-1]][0]
                
                # now let us apply and update to the prexisting vector!
                for date_key in parsed_prexisting_dict:
                    if first_instance_of_update_vector["Mon"][2] != 0:
                        parsed_prexisting_dict[date_key]["Mon"][0] = round(parsed_prexisting_dict[date_key]["Mon"][0]+first_instance_of_update_vector["Mon"][0],8)
                        parsed_prexisting_dict[date_key]["Mon"][2] = round(parsed_prexisting_dict[date_key]["Mon"][2]+first_instance_of_update_vector["Mon"][2],8)
                        parsed_prexisting_dict[date_key]["Mon"][1] = round(parsed_prexisting_dict[date_key]["Mon"][0]*avg_price, 2)
                        if parsed_prexisting_dict[date_key]["Mon"][1] != 0 and parsed_prexisting_dict[date_key]["Mon"][2] != 0:
                            parsed_prexisting_dict[date_key]["Mon"][3] = round((((parsed_prexisting_dict[date_key]["Mon"][1] / parsed_prexisting_dict[date_key]["Mon"][2]) + 0.000000001))-1, 2)
                        else:
                            parsed_prexisting_dict[date_key]["Mon"][3] = 0
                    if first_instance_of_update_vector["Tue"][2] != 0:
                        parsed_prexisting_dict[date_key]["Tue"][0] = round(parsed_prexisting_dict[date_key]["Tue"][0]+first_instance_of_update_vector["Tue"][0],8)
                        parsed_prexisting_dict[date_key]["Tue"][2] = round(parsed_prexisting_dict[date_key]["Tue"][2]+first_instance_of_update_vector["Tue"][2],8)
                        parsed_prexisting_dict[date_key]["Tue"][1] = round(parsed_prexisting_dict[date_key]["Tue"][0]*avg_price, 2)
                        if parsed_prexisting_dict[date_key]["Tue"][1] != 0 and parsed_prexisting_dict[date_key]["Tue"][2] != 0:
                            parsed_prexisting_dict[date_key]["Tue"][3] = round((((parsed_prexisting_dict[date_key]["Tue"][1] / parsed_prexisting_dict[date_key]["Tue"][2]) + 0.000000001))-1, 2)
                        else:
                            parsed_prexisting_dict[date_key]["Tue"][3] = 0
                    if first_instance_of_update_vector["Wed"][2] != 0:
                        parsed_prexisting_dict[date_key]["Wed"][0] = round(parsed_prexisting_dict[date_key]["Wed"][0]+first_instance_of_update_vector["Wed"][0],8)
                        parsed_prexisting_dict[date_key]["Wed"][2] = round(parsed_prexisting_dict[date_key]["Wed"][2]+first_instance_of_update_vector["Wed"][2],8)
                        parsed_prexisting_dict[date_key]["Wed"][1] = round(parsed_prexisting_dict[date_key]["Wed"][0]*avg_price, 2)
                        if parsed_prexisting_dict[date_key]["Wed"][1] != 0 and parsed_prexisting_dict[date_key]["Wed"][2] != 0:
                            parsed_prexisting_dict[date_key]["Wed"][3] = round((((parsed_prexisting_dict[date_key]["Wed"][1] / parsed_prexisting_dict[date_key]["Wed"][2]) + 0.000000001))-1, 2)
                        else:
                            parsed_prexisting_dict[date_key]["Wed"][3] = 0
                    if first_instance_of_update_vector["Thu"][2] != 0:
                        parsed_prexisting_dict[date_key]["Thu"][0] = round(parsed_prexisting_dict[date_key]["Thu"][0]+first_instance_of_update_vector["Thu"][0],8)
                        parsed_prexisting_dict[date_key]["Thu"][2] = round(parsed_prexisting_dict[date_key]["Thu"][2]+first_instance_of_update_vector["Thu"][2],8)
                        parsed_prexisting_dict[date_key]["Thu"][1] = round(parsed_prexisting_dict[date_key]["Thu"][0]*avg_price, 2)
                        if parsed_prexisting_dict[date_key]["Thu"][1] != 0 and parsed_prexisting_dict[date_key]["Thu"][2] != 0:
                            parsed_prexisting_dict[date_key]["Thu"][3] = round((((parsed_prexisting_dict[date_key]["Thu"][1] / parsed_prexisting_dict[date_key]["Thu"][2]) + 0.000000001))-1, 2)
                        else:
                            parsed_prexisting_dict[date_key]["Thu"][3] = 0
                    if first_instance_of_update_vector["Fri"][2] != 0:
                        parsed_prexisting_dict[date_key]["Fri"][0] = round(parsed_prexisting_dict[date_key]["Fri"][0]+first_instance_of_update_vector["Fri"][0],8)
                        parsed_prexisting_dict[date_key]["Fri"][2] = round(parsed_prexisting_dict[date_key]["Fri"][2]+first_instance_of_update_vector["Fri"][2],8)
                        parsed_prexisting_dict[date_key]["Fri"][1] = round(parsed_prexisting_dict[date_key]["Fri"][0]*avg_price, 2)
                        if parsed_prexisting_dict[date_key]["Fri"][1] != 0 and parsed_prexisting_dict[date_key]["Fri"][2] != 0:
                            parsed_prexisting_dict[date_key]["Fri"][3] = round((((parsed_prexisting_dict[date_key]["Fri"][1] / parsed_prexisting_dict[date_key]["Fri"][2]) + 0.000000001))-1, 2)
                        else:
                            parse_prexisting_dictionary[date_key]["Fri"][3] = 0
                
                # now we need to merge the update vector...
                for date_key_in_update in update_v1_vector_dict:
                    parsed_prexisting_dict[date_key_in_update] = update_v1_vector_dict[date_key_in_update]
                    
                # finally, we can write the update to file & terminate this action sequence    
                kicker.write_v1_dict(ticker, config_dict, parsed_prexisting_dict)
                return
        
        # else, we just run the thing like normal...
        v1_dict = kicker.iterate_through_v1(ticker, config_dict, ticker_truth, ticker_dict, pid_index)
        kicker.write_v1_dict(ticker, config_dict, v1_dict)
        return
    
    def parse_prexisting_dictionary(prexisting_file_name):
        parsed_dict = {}
        file_contents = open(prexisting_file_name, "r")
        file_contents = file_contents.read().split("\n")
        file_contents.pop(-1)
        for line in file_contents:
            line_hold = line.split(", {")
            date_key = line_hold[0]
            remainder_1 = str(line_hold[1])
            remainder_1 = remainder_1.replace("}","")
            remainder_1 = remainder_1.replace("[","")
            remainder_1 = remainder_1.replace("]","")
            line_hold_2 = remainder_1.split(", '")
            week_sub_dict = {}
            for sub_day in line_hold_2:
                line_hold_3 = str(sub_day)
                line_hold_3 = line_hold_3.replace("'","")
                line_hold_3 = line_hold_3.split(":")
                day_of_week = line_hold_3[0]
                day_data = str(line_hold_3[1]).split(",")
                for i in range(len(day_data)):
                    day_data[i] = float(day_data[i])
                week_sub_dict[day_of_week] = day_data
            parsed_dict[date_key] = week_sub_dict
        return parsed_dict
    
    def write_v1_dict(ticker, config_dict, v1_dict):
        # needs to also handle log file writing...
        share_rankings = {'Mon':[], 'Tue':[], 'Wed':[], 'Thu':[], 'Fri':[]}
        for key in v1_dict:
            share_dict = {}
            share_dict["Mon"] = v1_dict[key]["Mon"][0]
            share_dict["Tue"] = v1_dict[key]["Tue"][0]
            share_dict["Wed"] = v1_dict[key]["Wed"][0]
            share_dict["Thu"] = v1_dict[key]["Thu"][0]
            share_dict["Fri"] = v1_dict[key]["Fri"][0]
            share_dict = dict(sorted(share_dict.items(), key=lambda x:x[1]))
            share_rankings["Mon"].append(list(share_dict).index("Mon")+1)
            share_rankings["Tue"].append(list(share_dict).index("Tue")+1)
            share_rankings["Wed"].append(list(share_dict).index("Wed")+1)
            share_rankings["Thu"].append(list(share_dict).index("Thu")+1)
            share_rankings["Fri"].append(list(share_dict).index("Fri")+1)
        
        mon_share_rankings = kicker.count_distros(share_rankings["Mon"])
        tue_share_rankings = kicker.count_distros(share_rankings["Tue"])
        wed_share_rankings = kicker.count_distros(share_rankings["Wed"])
        thu_share_rankings = kicker.count_distros(share_rankings["Thu"])
        fri_share_rankings = kicker.count_distros(share_rankings["Fri"])
        
        distro_log_fn = config_dict["file_7"]+ticker+"_distro_log.txt"
        distro_log = open(distro_log_fn, "w")
        for i in range(5):
            distro_log.write("Mon Rank "+str(i+1)+" Quantity: "+str(mon_share_rankings[i]))
            distro_log.write("\n")
        for i in range(5):
            distro_log.write("Tue Rank "+str(i+1)+" Quantity: "+str(tue_share_rankings[i]))
            distro_log.write("\n")
        for i in range(5):
            distro_log.write("Wed Rank "+str(i+1)+" Quantity: "+str(wed_share_rankings[i]))
            distro_log.write("\n")
        for i in range(5):
            distro_log.write("Thu Rank "+str(i+1)+" Quantity: "+str(thu_share_rankings[i]))
            distro_log.write("\n")
        for i in range(5):
            distro_log.write("Fri Rank "+str(i+1)+" Quantity: "+str(fri_share_rankings[i]))
            distro_log.write("\n")
        distro_log.close()
        
        destination = config_dict["file_9"] + ticker + config_dict["csv"]
        writing = open(destination, "w")
        for day in v1_dict:
            writing.write(day+", "+str(v1_dict[day])+"\n")
        time.sleep(1)
        writing.close()
        return
    
    def count_distros(array_to_count):
        counts = [0]*5
        for num in array_to_count:
            counts[num-1] += 1
        return counts  
    
    def get_reference_dict_v1(ticker_dict, amt_to_buy_local):
        # we need a dictionary containing {date_key: [avg_price, avg_share, do_mon, do_tue, do_wed, do_thu, do_fri]}
        # this will be like a precomputed mirror of ticker_dict...
        lookup_dict = {}
        date_key_list = list(ticker_dict["stock"].keys())
        for date in ticker_dict["stock"]:
            day_before = False
            current_date_index = date_key_list.index(date)
            if current_date_index-1 >= 0:
                day_before = date_key_list[current_date_index-1]
            
            reference_data = [0, 0, False, False, False, False, False]
            reference_data[0] = kicker.get_average_price(ticker_dict["stock"][date][0], ticker_dict["stock"][date][1], ticker_dict["stock"][date][2], ticker_dict["stock"][date][3])
            reference_data[1] = kicker.get_average_share(amt_to_buy_local, ticker_dict["stock"][date][0], ticker_dict["stock"][date][1], ticker_dict["stock"][date][2], ticker_dict["stock"][date][3])
            dm, dt, dw, dth, df = kicker.day_delta_determination_n_buys((datetime.strptime(date, "%Y-%m-%d").weekday()), day_before)
            reference_data[2] = dm
            reference_data[3] = dt
            reference_data[4] = dw
            reference_data[5] = dth
            reference_data[6] = df
            lookup_dict[date] = reference_data
        return lookup_dict
    
    def day_delta_determination_n_buys(DoW, day_before):
        do_mon = False
        do_tue = False
        do_wed = False
        do_thu = False
        do_fri = False
        if day_before != False:
            what_DoW_was_day_before = datetime.strptime(day_before, "%Y-%m-%d").weekday()
            match DoW:
                case 0:
                    do_mon = True
                    match what_DoW_was_day_before:
                        case 0:
                            do_tue = True
                            do_wed = True
                            do_thu = True
                            do_fri = True
                        case 1:
                            do_wed = True
                            do_thu = True
                            do_fri = True
                        case 2:
                            do_thu = True
                            do_fri = True
                        case 3:
                            do_fri = True
                case 1:
                    do_tue = True
                    match what_DoW_was_day_before:
                        case 1:
                            do_mon = True
                            do_wed = True
                            do_thu = True
                            do_fri = True
                        case 2:
                            do_mon = True
                            do_thu = True
                            do_fri = True
                        case 3:
                            do_mon = True
                            do_fri = True
                        case 4:
                            do_mon = True
                case 2:
                    do_wed = True
                    match what_DoW_was_day_before:
                        case 0:
                            do_tue = True
                        case 2:
                            do_mon = True
                            do_tue = True
                            do_thu = True
                            do_fri = True
                        case 3:
                            do_mon = True
                            do_tue = True
                            do_fri = True
                        case 4:
                            do_mon = True
                            do_tue = True
                case 3:
                    do_thu = True
                    match what_DoW_was_day_before:
                        case 0:
                            do_tue = True
                            do_wed = True
                        case 1:
                            do_wed = True
                        case 3:
                            do_mon = True
                            do_tue = True
                            do_wed = True
                            do_fri = True
                        case 4:
                            do_mon = True
                            do_tue = True
                            do_wed = True
                case 4:
                    do_fri = True
                    match what_DoW_was_day_before:
                        case 0:
                            do_tue = True
                            do_wed = True
                            do_thu = True
                        case 1:
                            do_wed = True
                            do_thu = True
                        case 2:
                            do_thu = True
                        case 4:
                            do_mon = True
                            do_tue = True
                            do_wed = True
                            do_thu = True
        if day_before == False:
            match DoW:
                case 0:
                    do_mon = True
                case 1:
                    do_tue = True
                case 2:
                    do_wed = True
                case 3:
                    do_thu = True
                case 4:
                    do_fri = True
        return do_mon, do_tue, do_wed, do_thu, do_fri
    
    def iterate_through_v1(ticker, config_dict, ticker_truth, ticker_dict, pid_index):
        lookup_dict = {}
        amt_to_buy_local = amt_to_buy
        if ticker in funds_to_compare_to:
            lookup_dict = kicker.get_reference_dict_v1(ticker_dict, amt_to_buy_funds)
            amt_to_buy_local = amt_to_buy_funds
        else:
            lookup_dict = kicker.get_reference_dict_v1(ticker_dict, amt_to_buy_local)
        output_dict = {}
        date_key_list = list(ticker_dict["stock"].keys())
        avg_price_final = lookup_dict[list(lookup_dict)[-1]][0]
        for date_key_1 in tqdm(ticker_dict["stock"], desc=ticker, position=pid_index, delay=5):
            # this will be a running total dictionary; [running shares, running value, total buy amt, growth]
            weekday_dict = {"Mon":[0,0,0,0], "Tue":[0,0,0,0], "Wed":[0,0,0,0], "Thu":[0,0,0,0], "Fri":[0,0,0,0]}
            for date_key_2 in date_key_list:
                # need to account for it being the 1st datekey...
                do_mon = lookup_dict[date_key_2][2]
                do_tue = lookup_dict[date_key_2][3]
                do_wed = lookup_dict[date_key_2][4]
                do_thu = lookup_dict[date_key_2][5]
                do_fri = lookup_dict[date_key_2][6]
                
                # preform the rest of operations
                if "div" in ticker_dict:
                    if date_key_2 in ticker_dict["div"]:
                        # apply dividends!
                        div_yield = float(ticker_dict["div"][date_key_2])
                        for day in weekday_dict:
                            avg_price = lookup_dict[date_key_2][0]
                            weekday_dict[day][0] += round(weekday_dict[day][0] * (div_yield / avg_price), 8)
                        pass
                if "split" in ticker_dict:
                    if date_key_2 in ticker_dict["split"]:
                        # apply stock split!
                        split_array = str(ticker_dict["split"][date_key_2]).split(":")
                        for day in weekday_dict:
                            split_ratio = float(split_array[1]) / float(split_array[0])
                            previous_shares = copy.deepcopy(weekday_dict[day][0])
                            weekday_dict[day][0] = round(previous_shares * split_ratio, 8)
                        pass
                
                # once div and split checks occur, and day_before madness occur, here is our stock processing:
                avg_share = lookup_dict[date_key_2][1]
                if do_mon == True:
                    # apply weekday_dict["Mon"] buy
                    weekday_dict["Mon"][0] = round(weekday_dict["Mon"][0] + avg_share, 8)
                    weekday_dict["Mon"][2] = round(weekday_dict["Mon"][2] + amt_to_buy_local, 2)
                if do_tue == True:
                    # apply weekday_dict["Tue"] buy
                    weekday_dict["Tue"][0] = round(weekday_dict["Tue"][0] + avg_share, 8)
                    weekday_dict["Tue"][2] = round(weekday_dict["Tue"][2] + amt_to_buy_local, 2)
                if do_wed == True:
                    # apply weekday_dict["Wed"] buy
                    weekday_dict["Wed"][0] = round(weekday_dict["Wed"][0] + avg_share, 8)
                    weekday_dict["Wed"][2] = round(weekday_dict["Wed"][2] + amt_to_buy_local, 2)
                if do_thu == True:
                    # apply weekday_dict["Thu"] buy
                    weekday_dict["Thu"][0] = round(weekday_dict["Thu"][0] + avg_share, 8)
                    weekday_dict["Thu"][2] = round(weekday_dict["Thu"][2] + amt_to_buy_local, 2)
                if do_fri == True:
                    # apply weekday_dict["Fri"] buy
                    weekday_dict["Fri"][0] = round(weekday_dict["Fri"][0] + avg_share, 8)
                    weekday_dict["Fri"][2] = round(weekday_dict["Fri"][2] + amt_to_buy_local, 2)
                # operations at the end of our second for loop
            # update all values (regardless of DoW)
            weekday_dict["Mon"][1] = round(weekday_dict["Mon"][0] * avg_price_final, 2)
            weekday_dict["Tue"][1] = round(weekday_dict["Tue"][0] * avg_price_final, 2)
            weekday_dict["Wed"][1] = round(weekday_dict["Wed"][0] * avg_price_final, 2)
            weekday_dict["Thu"][1] = round(weekday_dict["Thu"][0] * avg_price_final, 2)
            weekday_dict["Fri"][1] = round(weekday_dict["Fri"][0] * avg_price_final, 2)
            
            # update all growth values (regardless of DoW)
            if weekday_dict["Mon"][1] != 0 and weekday_dict["Mon"][2] != 0:
                weekday_dict["Mon"][3] = round((weekday_dict["Mon"][1] / (weekday_dict["Mon"][2] + 0.0001))-1, 2)
            if weekday_dict["Tue"][1] != 0 and weekday_dict["Tue"][2] != 0:
                    weekday_dict["Tue"][3] = round((weekday_dict["Tue"][1] / (weekday_dict["Tue"][2] + 0.0001))-1, 2)
            if weekday_dict["Wed"][1] != 0 and weekday_dict["Wed"][2] != 0:
                    weekday_dict["Wed"][3] = round((weekday_dict["Wed"][1] / (weekday_dict["Wed"][2] + 0.0001))-1, 2)
            if weekday_dict["Thu"][1] != 0 and weekday_dict["Thu"][2] != 0:
                    weekday_dict["Thu"][3] = round((weekday_dict["Thu"][1] / (weekday_dict["Thu"][2] + 0.0001))-1, 2)
            if weekday_dict["Fri"][1] != 0 and weekday_dict["Fri"][2] != 0:
                    weekday_dict["Fri"][3] = round((weekday_dict["Fri"][1] / (weekday_dict["Fri"][2] + 0.0001))-1, 2)
            # operations at the end of our first for loop
            date_key_list.pop(0)
            output_dict[date_key_1] = copy.deepcopy(weekday_dict)
        return output_dict
    
    def get_average_price(open, high, low, close):
        return round((open+high+low+close)/4, 2)
        
    def get_average_share(amt, open, high, low, close):
        amt_o = round( amt / (open + 0.00000000001), 8)
        amt_h = round( amt / (high + 0.00000000001), 8)
        amt_l = round( amt / (low + 0.00000000001), 8)
        amt_c = round( amt / (close + 0.00000000001), 8)
        return round((amt_o+amt_h+amt_l+amt_c)/4, 8)

class multi_me:
    def distribute_lists(truth_table_dict, config_dict):
        #process_count = 8
        len_of_ttd = len(truth_table_dict)
        distro = [[] for _ in range(process_count)]
        iteration_counter = 0
        for key in truth_table_dict:
            distro[iteration_counter].append(key)
            iteration_counter += 1
            if iteration_counter == process_count:
                iteration_counter = 0
        return distro
        
    def create_processes(config_dict, truth_table, master_dict):
        distro = multi_me.distribute_lists(truth_table, config_dict)
        all_processes = []
        
        for list in distro:
            pid_index = distro.index(list)
            new_process = multiprocessing.Process(target=multi_me.substepping_threads, args=(list, config_dict, truth_table, master_dict, pid_index,))
            all_processes.append(new_process)
        
        for process in all_processes:
            process.start()
        for process in all_processes:
            process.join()
        return
        
    def substepping_threads(list, config_dict, truth_table, master_dict, pid_index):
        admin_esc.admin_checker()
        for ticker in list:
            ticker_thread = threading.Thread(target=kicker.main_task, args=(ticker, config_dict, truth_table, master_dict, pid_index,))
            ticker_thread.start()
            ticker_thread.join()
        return

class admin_esc:
    def admin_checker():
        run_check = admin_esc.has_admin()
        if run_check[1] == True:
            admin_esc.set_process_to_high()
    
    def set_process_to_high(): # contributed by bfontaine & XO-user-OX of stackoverflow
        os_used = sys.platform
        process = psutil.Process(os.getpid())  # Set highest priority for the python script for the CPU
        if os_used == "win32":  # Windows (either 32-bit or 64-bit)
            process.nice(psutil.REALTIME_PRIORITY_CLASS)
        elif os_used == "linux":  # linux
            process.nice(psutil.IOPRIO_HIGH)
        else:  # MAC OS X or other
            process.nice(20)
        
    def has_admin(): # contributed by taleinat & tahoar of stackoverflow
        if os.name == 'nt':
            try:
                # only windows users with admin privileges can read the C:\windows\temp
                temp = os.listdir(os.sep.join([os.environ.get('SystemRoot','C:\\windows'),'temp']))
            except:
                return (os.environ['USERNAME'],False)
            else:
                return (os.environ['USERNAME'],True)
        else:
            if 'SUDO_USER' in os.environ and os.geteuid() == 0:
                return (os.environ['SUDO_USER'],True)
            else:
                return (os.environ['USERNAME'],False)

class reader:
    def read_master_dict(config_dict, truth_table):
        master_dict = {}
        for key in truth_table:
            sub_dict = {}
            
            if truth_table[key][0] == 1:
                sub_dict["div"] = reader.read_div_csv(config_dict["file_3"]+key+config_dict["csv"])
            if truth_table[key][1] == 1:
                sub_dict["split"] = reader.read_spl_csv(config_dict["file_4"]+key+config_dict["csv"])
            if truth_table[key][2] == 1:
                sub_dict["stock"] = reader.read_sto_csv(config_dict["file_5"]+key+config_dict["csv"])
                
            master_dict[key] = sub_dict.copy()
        return master_dict
    
    def read_div_csv(file_ref):
        read_file = open(file_ref,"r")
        hold = []
        hold = read_file.read().split("\n")
        read_file.close()
        hold3 = {}
        hold.pop(0)
        hold.pop()
        for line in hold:
            hold2 = line.split(",")
            hold3[hold2[0]] = hold2[1]
        return hold3
        
    def read_spl_csv(file_ref):
        read_file = open(file_ref,"r")
        hold = []
        hold = read_file.read().split("\n")
        read_file.close()
        hold3 = {}
        hold.pop(0)
        hold.pop()
        for line in hold:
            hold2 = line.split(",")
            hold3[hold2[0]] = hold2[1]
        return hold3
        
    def read_sto_csv(file_ref):
        read_file = open(file_ref,"r")
        hold = []
        hold = read_file.read().split("\n")
        read_file.close()
        hold3 = {}
        hold.pop(0)
        hold.pop()
        for line in hold:
            hold2 = line.split(",")
            date = str(hold2[0]).split("-")
            if int(date[0]) < date_to_start_at:
                continue
            for i in range(5):
                if i != 0:
                    hold2[i] = round(float(hold2[i]),2)
            hold3[hold2[0]] = hold2[1:5]
        return hold3