# author: picklez
# version: 1.3.1
# purpose: To be the core runner for the research program (stock market simulation)

# imports
import precheck
from helper import *
import time
import argparse

if __name__ == '__main__':
    # start the clock!
    start_time = time.time()
    do_update = False
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--update', action="store_true", help="This updates the data files to the current date!")
    args = parser.parse_args()
    if args.update == True:
        do_update = True
    
    # escalate to admin/realtime to start
    admin_esc.admin_checker()
    # initialize prechecks (set to true for update)
    config_dict, truth_table = precheck.run_precheck(do_update)
    
    # construct master file dictionary
    master_dict = reader.read_master_dict(config_dict, truth_table)
    
    print("Data compiled! Starting processing!")
    # do threading/process assignment
    multi_me.create_processes(config_dict, truth_table, master_dict)
    
    # stop the clock for simulations!
    print("\n\n\n\n\n\n\n\n\n")
    print("It took " + str(round((time.time() - start_time),2)) + "s to run simulation and graphs! Time to compare all!")
    # start the clock for time to generate pdfs!
    start_time_2 = time.time()
    kicker2.pdf_summary15_creator(config_dict, truth_table)
    print("It took " + str(round((time.time() - start_time_2),2)) + "s to generate pdfs!")
    print("It took a total elapsed time of "+ str(round((time.time() - start_time),2)) + "s to run all processes!")