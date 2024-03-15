# author: picklez
# version: 0.1.1
# purpose: this program runs the precheck functionality for
# the core runner program. It returns a config_dictionary
# and a truth_table_dictionary. It also updates all files if
# desired via the run_precheck function; to update use True.

# operational imports
import os
import time
from tqdm import tqdm
from datetime import datetime
from yahoo_fin.stock_info import *

# used to ignore get_ warnings for yahoo_fin
import warnings
warnings.filterwarnings("ignore")

cwd = os.getcwd()
config_name = "config.txt"
stock_list_name = "stock_list.txt"

class config:
    def create_default_config():
        # creates a default config file for us to reference
        write_config = open(config_name, "w")
        write_config.write('file_1=\'\\\\resource_files\\\\\''+
                            '\nfile_2=\'\\\\output_files\\\\\''+
                            '\nfile_3=\'\\\\resource_files\\div_data\\\\\''+
                            '\nfile_4=\'\\\\resource_files\\splits_data\\\\\''+
                            '\nfile_5=\'\\\\resource_files\\stock_data\\\\\''+
                            '\nfile_6=\'\\\\output_files\\graphs\\\\\''+
                            '\nfile_7=\'\\\\output_files\\log_files\\\\\''+
                            '\nfile_8=\'\\\\output_files\\reports\\\\\''+
                            '\nfile_9=\'\\\\output_files\\data_files\\\\\''+
                            '\npng=\'.png\''+
                            '\ncsv=\'.csv\''+
                            '\npdf=\'.pdf\''+
                            '\nupdate=\'False\'')
        write_config.close()
        return
    
    def get_config_dict():
        # reads the config file into a dictionary for us to reference
        config_dict = {}
        read_config = open(config_name, "r")
        config_contents = read_config.read().split("\n")
        read_config.close()
        # now we need to load the config into the dictionary
        for line in config_contents:
            # each line of the config contains a variable and a value, they are separated by a '='
            variable, value = line.split("=")
            # the ' helps us determine if the variable loaded is an integer or string
            if value[0] != "'":
                value = int(value)
            else:
                value = value.replace("'","")
            # once we have made the value the appropriate type, we append it to the dictionary
            if "file_" in variable:
                config_dict[variable] = cwd+value
            else:
                config_dict[variable] = value
        return config_dict
        
    def read_config():
        config_dict = {}
        if config_name not in os.listdir():
            config.create_default_config()
            config_dict = config.get_config_dict()
        else:
            config_dict = config.get_config_dict()
        return config_dict
        
    def ensure_file_structure(config_dict):
        f_str = "file_"
        for key in config_dict:
            if f_str in key:
                if os.path.exists(config_dict[key]):
                    pass
                else:
                    os.mkdir(config_dict[key])
            else:
                pass
        return

class truth_table: 
    def read_stock_list(config_dict):
        if stock_list_name not in os.listdir():
            truth_table.no_stock_list_error()
        else:
            truth_table_dict = truth_table.create_truth_table()
            truth_table_dict = truth_table.update_truth_table(truth_table_dict, config_dict)
            return truth_table_dict
        return
    
    def create_truth_table():
        truth_table_dict = {}
        read_stock_list = open(cwd+"\\"+stock_list_name, "r")
        stock_list_contents = read_stock_list.read().split("\n")
        read_stock_list.close()
        for line in stock_list_contents:
            truth_table_hold = [0, 0, 0]
            truth_table_dict[line] = truth_table_hold.copy()
        return truth_table_dict
        
    def get_truth_online(stock):
        sub_truth = [0, 0, 0]
        
        # test to see if it has dividend data
        test_value_1 = 1
        try:
            get_dividends(stock)
        except:
            test_value_1 = 0
            pass
        if test_value_1 == 1:
            sub_truth[0] = 1
            
        # test to see if it has split data
        test_value_2 = 1
        try:
            get_splits(stock)
        except:
            test_value_2 = 0
            pass
        if test_value_2 == 1:
            sub_truth[1] = 1
            
        # test to see if it has stock data at all
        test_value_3 = 1
        try:
            get_data(stock)
        except:
            test_value_3 = 0
            pass
        if test_value_3 == 1:
            sub_truth[2] = 1
        
        return sub_truth
        
    def update_truth_table(truth_table_dict, config_dict):
        for key in truth_table_dict:
            prexisting_truth = truth_table.check_directories_for(key, config_dict)
            if prexisting_truth[0] == 0 and prexisting_truth[1] == 0 and prexisting_truth[2] == 0 or prexisting_truth[2] == 0:
                online_truth = truth_table.get_truth_online(key)
                if online_truth[0] == 0 and online_truth[1] == 0 and online_truth[2] == 0:
                    print(key+" does not have any stock data.")
                truth_table_dict[key] = online_truth.copy()
            else:
                truth_table_dict[key] = prexisting_truth.copy()
        return truth_table_dict
    
    def check_directories_for(stock, config_dict):
        sub_truth = [0, 0, 0]
        fn_to_search = stock+config_dict["csv"]
        dir_1 = config_dict["file_3"]
        dir_2 = config_dict["file_4"]
        dir_3 = config_dict["file_5"]
        
        if fn_to_search in os.listdir(dir_1):
            sub_truth[0] = 1
        if fn_to_search in os.listdir(dir_2):
            sub_truth[1] = 1
        if fn_to_search in os.listdir(dir_3):
            sub_truth[2] = 1
        
        return sub_truth
    
    def no_stock_list_error():
        print("No stock_list.txt in cwd")
        print("Please create/add stock_list.txt")
        exit()
        return

class updater:
    def update_stock_data(config_dict, truth_table_dict):
        #for key in truth_table_dict:
        for key in tqdm(truth_table_dict):
            # predefine these to just make it easier upon every iteration
            div_file_ref = config_dict["file_3"]+key+config_dict["csv"]
            spl_file_ref = config_dict["file_4"]+key+config_dict["csv"]
            sto_file_ref = config_dict["file_5"]+key+config_dict["csv"]
            
            # Dividend data operations
            if truth_table_dict[key][0] == 1:
                if os.path.exists(div_file_ref) is True:
                    # detect_n_merge
                    updater.detect_n_merge(div_file_ref, key)
                else:
                    # fetch from online
                    div_data_frame = get_dividends(key)
                    div_data_frame.to_csv(path_or_buf=div_file_ref, sep=",", mode="w")
            
            # Split data operations
            if truth_table_dict[key][1] == 1: 
                if os.path.exists(spl_file_ref) is True:
                    # detect_n_merge
                    updater.detect_n_merge(spl_file_ref, key)
                else:
                    # fetch from online
                    spl_data_frame = get_splits(key)
                    spl_data_frame.to_csv(path_or_buf=spl_file_ref, sep=",", mode="w")
                    
            # Stock data operations
            if truth_table_dict[key][2] == 1: 
                if os.path.exists(sto_file_ref) is True:
                    # detect_n_merge
                    updater.detect_n_merge(sto_file_ref, key)
                else:
                    # fetch from online
                    sto_data_frame = get_data(key)
                    sto_data_frame.to_csv(path_or_buf=sto_file_ref, sep=",", mode="w")
        return
    
    def get_last_date(file_ref):
        read_given = open(file_ref, "r")
        hold = read_given.read().split("\n")
        read_given.close()
        hold.pop() # removes blank line
        if len(hold) > 1:
            last_line = hold[len(hold)-1].split(",")
            last_date = last_line[0]
            return last_date
        return False
    
    def delta_now_n_date(given_date): # returns positive for delta in the past
        from datetime import datetime
        str_ls = str(datetime.now()).split(" ")
        current_date = str(str_ls[0])
        d1 = datetime.strptime(current_date, "%Y-%m-%d")
        d2 = datetime.strptime(given_date, "%Y-%m-%d")
        delta = d1 - d2
        delta_hold = str(delta).split(" ")
        if delta_hold[0] == '0:00:00':
            return False, False
        delta_formated = int(delta_hold[0])
        return delta_formated, current_date
    
    def detect_n_merge(file_ref, ticker):
        # operation 1: last_date and validation
        last_date = updater.get_last_date(file_ref)
        if last_date is False or last_date == '0:00:00':
            return
        
        # operation 2: figuring how much data needs to be updated
        day_delta, current_date = updater.delta_now_n_date(last_date)
        if day_delta == False:
            return
        
        # operation 3: time to actual update the files!
        if day_delta != 0:
            # initialize variables for operations (holds the contents to be merged)
            sd_merge_request_dateframe = 0
            
            # operations change based on what file_ref is used (this is the online fetch requests)
            if "div_data" in file_ref:
                sd_merge_request_dateframe = get_dividends(ticker, start_date=last_date, end_date=current_date)
            elif "splits_data" in file_ref:
                sd_merge_request_dateframe = get_splits(ticker, start_date=last_date, end_date=current_date)
            elif "stock_data" in file_ref:
                sd_merge_request_dateframe = get_data(ticker, start_date=last_date, end_date=current_date, interval="1d")
        
            # operation 4: merge gotten data (transform dataframe to record to string to file)
            df_to_records = sd_merge_request_dateframe.to_records()
            target_file = open(file_ref, "a")
            for record in df_to_records:
                record_to_str = str(record)
                record_to_str = record_to_str.replace("T00:00:00.000000000\'","").replace("(","").replace(")","").replace("\'","").replace(" ","")
                if last_date in record_to_str:
                    continue
                target_file.write(record_to_str+"\n")
            target_file.close()
        return

def run_precheck(update):
    config_dict = config.read_config()
    if update == True:
        config_dict["update"] = "True"
    config.ensure_file_structure(config_dict)
    truth_table_dict = truth_table.read_stock_list(config_dict)
    if config_dict["update"] == "True":
        print("Updating files!")
        updater.update_stock_data(config_dict, truth_table_dict)
        print("Update complete!")
    return config_dict, truth_table_dict