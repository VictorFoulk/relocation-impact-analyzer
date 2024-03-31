"""
Analyser Class

Author: Victor Foulk
License: MIT License
Date: 2024-03-15
Version: 0.0.1 Pre-Alpha

The Analyzer class is the central component of the Relocation Impact Analyzer tool. It orchestrates various analyses related to the impacts of office relocations, including geocoding addresses, analyzing commute patterns, and generating graphical representations of the data. This class leverages external APIs, custom data handling, and graphical libraries to perform a comprehensive analysis tailored to the needs of strategic decision-making regarding office locations.

Key functionalities include:
- Geocoding addresses to latitude and longitude.
- Generating employee commute data and associated costs and emissions.
- Fuzzing GPS data to anonymize employee locations.
- Calculating commute costs and emissions based on commute data.
- Generating visual representations of analyzed data for easier interpretation.

This class is designed with modularity and reusability in mind, allowing for flexible adaptation and expansion to meet the evolving requirements of relocation impact analysis.
"""
import os
from relocation_impact_analyzer.project import Project
from relocation_impact_analyzer.g_api import GAPI
from relocation_impact_analyzer.graphing import Graphing

from datetime import datetime, timedelta
import re
from dotenv import load_dotenv, set_key
from time import sleep
import json
import pandas as pd
import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as mplt
from matplotlib.lines import Line2D                

class Analyzer:
    def __init__(self, proj=None, project_directory=None, env_file=""):
        """
        Initializes the Analyzer with specified project details and configuration.

        Args:
            proj (str, optional): The name of the project to load or create. Defaults to None.
            project_directory (str, optional): The directory where project files are stored. Defaults to None.
            env_file (str, optional): Path to a .env file for loading configuration variables. Defaults to an empty string.

        Raises:
            ValueError: If the specified project directory does not exist or no .env file is provided when expected.
        
        This constructor sets up the API rate limiting, loads the .env configuration, initializes the Google API client,
        and prepares the project directory and graphs subdirectory as needed.
        """

        # api rate limit is 3000 requests per minute, we see errors at 1000 requests per minute, so we limit to 300 per minute
        self.api_rate_limit = 300
        self.sleep_time = 60 / self.api_rate_limit
        # create a last call variable, set it to a time in the past
        self.last_call = datetime.now() - timedelta(seconds=self.sleep_time)
        self.gAPI = None
        self.gAPI_key = ""
        self.analysis_phase = 0
        self.env_file = env_file
        self.project_directory = None
        # load the .env file if it exists
        if self.env_file != "" and os.path.exists(env_file):
            load_dotenv(env_file,override=True)
        else:
            if os.path.exists(env_file):
                raise ValueError("No .env file provided.")
            # attempt to load the .env file from the CWD
            self.env_file = os.path.join(os.getcwd(), ".env")
            load_dotenv(override=True)
        # if the .env has keys, use them, otherwise use the defaults
        if os.getenv("GMAPS_API_KEY"):
            self.gAPI_key = os.getenv("GMAPS_API_KEY")
        if os.getenv("DEFAULT_PROJECT_DIRECTORY"):
            self.project_directory = os.getenv("DEFAULT_PROJECT_DIRECTORY")
        # if a project directory is provided, override .env and use it, otherwise use the default
        if project_directory:
            if os.path.exists(project_directory):
                self.project_directory = project_directory
            else:
                raise ValueError("Project directory does not exist.")
        elif self.project_directory is None:
            # use the CWD for now
            self.project_directory = os.path.join(os.path.dirname(__file__), "projects")
        self.project = None
        # if a project called for, load or create it        
        if proj:
            self.project = Project(proj, self.project_directory)
        else:
            self.project = Project( None, self.project_directory)
        # if a project is loaded, check for a subdirectory called "plots" in the project folder, 
            # create it if it doesn't exist, then list the plot .png filenames
        self.load_graphs()
        self.graphing = None
        # update the analysis phase
        self.update_analysis_phase()
        return None

    def load_graphs(self):
        """
        Loads the list of graph filenames from the project's 'plots' directory.

        This method checks if the 'plots' subdirectory exists within the current project directory. 
        If it doesn't exist, it creates the directory. It then updates the instance variable with a list of .png filenames 
        found in the 'plots' directory.

        Returns:
            bool: True if the project has a 'plots' directory, False otherwise.
        """
        if self.project.project_name !="":
            if not os.path.exists(os.path.join(self.project_directory, self.project.project_name, "plots")):
                os.mkdir(os.path.join(self.project_directory, self.project.project_name, "plots"))
            # load the list of .png filenames into a self.graphs attribute only if they are .png files
            self.graphs = [f for f in os.listdir(os.path.join(self.project_directory, self.project.project_name, "plots")) if f.endswith('.png')]
            return True
        else:
            self.graphs = []
            return False

    def sleepif(self):
        """
        Ensures adherence to the API rate limit by sleeping if the time since the last API call is less than the required wait time.

        This method calculates the time elapsed since the last API call and pauses execution for the remainder of the time needed to 
        comply with the set rate limit, ensuring that API requests do not exceed the prescribed rate.

        Returns:
            None
        """
        # if the delta between the current time and the last call is less than the sleep time, sleep for the difference
        if (datetime.now() - self.last_call).seconds < self.sleep_time:
            sleep(self.sleep_time - (datetime.now() - self.last_call).seconds)
        return None

    def log_error(self, message):
        """
        Logs an error message to the 'error_log.txt' file.

        Appends the provided message to a log file dedicated to errors, facilitating debugging and error tracking over time.

        Args:
            message (str): The error message to log.

        Returns:
            None
        """
        # append the message to the error.txt log
        with open("error_log.txt", "a") as f:
            f.write(message)
        return None

    def save_env(self, project_directory=None, gAPI_key=None, env_file=None):
        """
        Saves the specified environment variables to the .env file and updates the runtime environment.

        This method allows dynamic updating of critical environment variables, including the Google Maps API key and the default project directory. 
        If any arguments are provided, they override the corresponding instance variables before saving.

        Args:
            project_directory (str, optional): The directory where project files are stored. If specified, overrides the existing value.
            gAPI_key (str, optional): The Google Maps API key. If specified, overrides the existing value.
            env_file (str, optional): Path to the .env file. If specified, overrides the existing value.

        Raises:
            ValueError: If no .env file path is provided.

        Returns:
            None
        """
        # if variables specified, override self and then save to .env
        if project_directory:
            self.project_directory = project_directory
        if gAPI_key:
            self.gAPI_key = gAPI_key
        if env_file:
            self.env_file = env_file
        # save the .env file
        if self.env_file:
            set_key(self.env_file, "GMAPS_API_KEY", self.gAPI_key)
            set_key(self.env_file, "DEFAULT_PROJECT_DIRECTORY", self.project_directory)

        else:
            raise ValueError("No .env file provided.")

        # update the current runtime environment
        os.environ["GMAPS_API_KEY"] = self.gAPI_key
        os.environ["DEFAULT_PROJECT_DIRECTORY"] = self.project_directory

    def list_projects(self):
        """
        Lists all projects within the project directory.

        Retrieves the names of all subdirectories within the project directory, treating each as a separate project. 
        This method is useful for enumerating all available projects for selection or analysis.

        Returns:
            list: A list of project names (subdirectory names) within the project directory.
        """
        # list all projects in the project directory
        return os.listdir(self.project_directory)
    
    def create_project(self, project_name):
        """
        Creates a new project with the specified name.

        This method initializes a new `Project` instance and sets it as the current project. It updates the analysis phase 
        based on the new project's status.

        Args:
            project_name (str): The name of the new project to create.

        Returns:
            bool: True if the project is successfully created, False otherwise.
        """
        # create a new project
        self.project = Project(project_name, self.project_directory)
        # update the analysis phase
        self.update_analysis_phase()
        return True
    
    def load_project(self, project_name):
        """
        Loads an existing project by name.

        Sets the specified project as the current project, loads any associated graphs, and updates the analysis phase 
        based on the loaded project's status.

        Args:
            project_name (str): The name of the project to load.

        Returns:
            bool: True if the project is successfully loaded, False otherwise.
        """
     # load an existing project
        self.project = Project(project_name, self.project_directory)
        # load the graphs if any
        self.load_graphs()
        # update the analysis phase
        self.update_analysis_phase()
        return True

    def update_analysis_phase(self):
        """
        Updates the analysis phase based on the current state of the project data.

        This method determines the current phase of analysis by checking the availability of specific data files within the project. 
        The analysis phase is a critical component that guides the workflow and available actions within the current project context.

        Returns:
            int: The updated analysis phase.
        """

        # if project is none, phase is zero
        if self.project is None:
            self.analysis_phase = 0
            return 0
        # if there is a project and there is no employee_addresses.csv in the project, phase is 1
        if "employee_addresses.csv" not in self.project.list_data_files():
            self.analysis_phase = 1
            return 1
        # if there is a project and there is a employee_addresses.csv in the project, phase is 2
        if "employee_addresses.csv" in self.project.list_data_files() and "office_addresses.csv" in self.project.list_data_files():
            # if there is also a employee_gps.csv in the project, phase is 3
            if "employee_gps.csv" in self.project.list_data_files() and "office_gps.csv" in self.project.list_data_files():
                # if there is also a gps_fuzz.csv in the project, or if using GPS fuzz is set to fals, we are at phase is 4
                if "gps_fuzz.csv" in self.project.list_data_files() or self.project.use_gps_fuzzing==False or self.project.use_gps_fuzzing=="False":
                    # if there is also a commute_data.csv in the project, phase is 5
                    if "commute_data.csv" in self.project.list_data_files():
                        # if graphs.json is present in the plots dir, we've graphed, phase is 6
                        if "plots" in os.listdir(os.path.join(self.project_directory, self.project.project_name)) and "graphs.json" in os.listdir(os.path.join(self.project_directory, self.project.project_name, "plots")):
                            # if tables dir exists and tables.json is present, we've tabled, phase is 7
                            if "tables" in os.listdir(os.path.join(self.project_directory, self.project.project_name)) and "tables.json" in os.listdir(os.path.join(self.project_directory, self.project.project_name, "tables")):
                                #self.analysis_phase = 7
                                #return 7
                                # at the moment, we don't actually have a need for the tabluar data, so we'll skip it
                                self.analysis_phase = 6
                                return 6
                            self.analysis_phase = 6
                            return 6
                        self.analysis_phase = 5
                        return 5
                    else:
                        self.analysis_phase = 4
                        return 4
                else:
                    self.analysis_phase = 3
                    return 3
            else:
                self.analysis_phase = 2
                return 2
        
    def convert_addresses_to_gps(self, force=False,log_csv=None):
        """
        Converts addresses from specified CSV files to GPS coordinates using the Google Maps API.

        This method processes both employee and office address data, converting each address to latitude and longitude coordinates. 
        The results are saved to corresponding GPS data files. If logging is enabled, the process details are recorded in a specified log CSV file.

        Args:
            force (bool, optional): If True, forces re-conversion of addresses even if GPS data already exists. Defaults to False.
            log_csv (str, optional): Path to a log CSV file where operation details are recorded. Defaults to None.

        Returns:
            bool: True if the conversion process is completed successfully for all addresses; False otherwise.
        
        This method handles geocoding of addresses using the Google Maps API, respecting API rate limits
        and optionally logging the process. If `force` is True, existing GPS data is ignored, and addresses are re-geocoded.
            
        """

        # start logfile if logging
        if log_csv:
            log = open(log_csv, "a+")
            log.write("Beginning the geocoding of addresses\n")
            # dump the project data including the file system location of all data files to the log
            log.write("project data" + str(self.project) + "\n")
            log.write(self.project.project_directory + "\n")

            log.flush()
        # create a google API object if it doesn't exist
        # if the project has an API key, use it, otherwise use the default .env key
        if self.project.GMAPS_API_KEY:
            api_key = self.project.GMAPS_API_KEY
        else:
            api_key = self.gAPI_key
        if not self.gAPI:
            self.gAPI = GAPI(api_key)  
        # same action for both files
        out = {"employee_addresses.csv": "employee_gps.csv", "office_addresses.csv": "office_gps.csv"}
        for file in out.keys():
            # check to see if addresses are already in the project
            if file in self.project.list_data_files():
                # if the address data isn't already in the project, load it
                if self.project.data[file] is None or force:
                    # attempt to load the address data
                    if self.project.load_data_file(file):
                        pass # valid data loaded
                    else:
                        print("Errors loading address data from project.")
                        return False
                # if the address data is already in the project, use it
                # create the project data object to hold the gps data
                self.project.start_dataframe(out[file])
                # iterate through the address data and convert each address to gps lat long in the project data object
                for index, row in self.project.data[file].iterrows():
                    # get the geocoded address lat and long
                    try:
                        if log_csv: 
                            log.write("Geocoding address: "+row["address"]+"\n")
                            log.flush()
                            print("Geocoding address: "+row["address"]+"\n")
                        self.sleepif()
                        try:
                            latlong = self.gAPI.geocode(row["address"])
                        except Exception as e:
                            # if logging, write the exception event to the logfile
                            self.log_error("Exception calling geocode function: "+str(e)+"\n")
                            print("Exception calling geocode function: "+str(e)+"\n")
                            # if the excetion is a recoverable one, retry after a delay, else raise the exception
                            if self.handle_GAPI_exception(e):
                                print("recoverable exception, waiting to retry once")
                                sleep(10000)
                                try:
                                    latlong = self.gAPI.geocode(row["address"])
                                except Exception as e:
                                    print("Unrecoverable exception, tried twice skipping address"+str(e)+"\n")
                                    # if logging, write the exception event to the logfile
                                    self.log_error("Recoverable error calling geocode function, failed twice. Deemed unrecoverable. Exception: "+str(e)+"\n")
                                    e.add_note = "Recoverable error calling geocode function, failed twice. Deemed unrecoverable"
                                    raise e
                            else:
                                print("Recoverable exception calling geocode, skipping address. \n"+str(e)+"\n")
                                self.log_error("Unrecoverable error calling geocode, failed once. Exception: "+str(e)+"\n")
                                e.add_note = "Unrecoverable error calling geocode, failed once"
                                raise e
                            

                        # insert the lat and long into a new row in the project data object
                        self.project.data[out[file]].loc[index] = {"address": row["address"],"latitude": latlong['lat'], "longitude": latlong['lng']}
                    except Exception as e:
                        print("Error saving geocode address result: "+row["address"] + "\n Got exception: "+str(e))
                        if log_csv: log.write("Error saving geocode result address: "+row["address"]+"\n")
                        self.log_error("Error saving geocode result address: "+row["address"]+"\n" + "Got exception: "+str(e))
                        raise e
                                            
                # save the project data object to the csv file
                if file == "employee_addresses.csv":
                    self.project.save_data_file(out[file])
                elif file == "office_addresses.csv":
                    self.project.save_data_file(out[file])
                # update the analysis phase
                self.update_analysis_phase()
                if log_csv: log.write("Geocoding complete\n")
            else:
                print("Address data "+file+" missing from project.")
                return False   
        if log_csv: log.close()             
        return True
    
    def fuzz_employee_gps(self, force=False):
        """
        Applies a fuzzing process to employee GPS coordinates to anonymize locations.

        This method adds a small, random displacement to the latitude and longitude of employee addresses. 
        This process is intended to protect privacy by preventing the exact identification of employee home locations.

        Args:
            force (bool, optional): If True, forces re-fuzzing of GPS coordinates even if fuzzed data already exists. Defaults to False.

        Returns:
            bool: True if fuzzing is successfully applied to all employee GPS coordinates; False otherwise.
        """
        # if the google API object doesn't exist, create it
        if not self.gAPI:
            self.gAPI = GAPI()
        # add a small amount of fuzz to the employee gps coordinates
        # if the gps data isn't already in the project, load it
        if "employee_gps.csv" in self.project.list_data_files():
            if self.project.data["employee_gps.csv"] is None or force:
                # attempt to load the gps data
                if self.project.load_data_file("employee_gps.csv"):
                    pass
                else:
                    print("Errors loading gps data from project.")
                    return False
            # if the gps data is already in the project, use it
            # create the project data object to hold the fuzzed gps data
            self.project.start_dataframe("gps_fuzz.csv")
            # iterate through the gps data and fuzz each set of coordinates
            for index, row in self.project.data["employee_gps.csv"].iterrows():
                # fuzz the lat and long
                latlong = self.gAPI.fuzz_latlong({"lat": row["latitude"], "lng": row["longitude"]},self.project.gps_fuzz_factor)
                # insert the fuzzed lat and long into a new row in the project data object
                self.project.data["gps_fuzz.csv"].loc[index] = {"latitude": latlong['lat'], "longitude": latlong['lng']}
            # save the project data object to the csv file
            self.project.save_data_file("gps_fuzz.csv")
            # update the analysis phase
            self.update_analysis_phase()
        else:    
            print("GPS data missing from project.")
            return False
        
    def get_commute_data(self, force=False, log_csv=None):
        """
        Generates commute data for employees based on their GPS coordinates and the office locations.

        This method calculates commute times and distances from employees' locations to the office, accounting for specified commute times. 
        Optionally logs the operation details if a log CSV file path is provided.

        Args:
            force (bool, optional): If True, forces regeneration of commute data even if it already exists. Defaults to False.
            log_csv (str, optional): Path to a log CSV file where operation details are recorded. Defaults to None.

        Returns:
            bool: True if commute data is successfully generated; False otherwise.
        """

        # if the use fuzzed data flag is set, use the fuzzed data, otherwise use the original data
        if self.project.use_gps_fuzzing==True or self.project.use_gps_fuzzing=="True":
            # if the fuzzed gps data isn't already in the project, load it
            if "gps_fuzz.csv" in self.project.list_data_files():
                if self.project.data["gps_fuzz.csv"] is None or force:
                    # attempt to load the fuzzed gps data
                    if self.project.load_data_file("gps_fuzz.csv"):
                        print("Using fuzzed GPS data.")
                        pass
                    else:
                        print("Errors loading fuzzed gps data from project.")
                        return False
            else:
                print("Fuzzed GPS data missing from project.")
                return False
        else:
            # use the un fuzzed data
            # if the gps data isn't already in the project, load it
            if "employee_gps.csv" in self.project.list_data_files():
                if self.project.data["employee_gps.csv"] is None or force:
                    # attempt to load the gps data
                    if self.project.load_data_file("employee_gps.csv"):
                        pass
                    else:
                        print("Errors loading gps data from project.")
                        return False
                else:
                    pass
            else:
                print("GPS data missing from project.")
                return False
        # attempt to load the office gps data
        if "office_gps.csv" in self.project.list_data_files():
            if self.project.data["office_gps.csv"] is None or force:
                # attempt to load the office gps data
                if self.project.load_data_file("office_gps.csv"):
                    pass
                else:
                    print("Errors loading office gps data from project.")
                    return False
        else:
            print("Office GPS data missing from project.")
            return False
        
        # touch the logfile to lock
        if log_csv:
            log = open(log_csv, "a+")
            log.write("Beginning the generation of commute data\n")
            log.flush()
        # if the google API object doesn't exist, create it
        if not self.gAPI:
            self.gAPI = GAPI()
        # create a new dataframe to hold the commute data
        self.project.start_dataframe("commute_data.csv")
        # create preparatory helper variables
        # create datetime objects for the morning commute times
        morning_departure = datetime.strptime(self.project.morning_commute_start, "%H:%M")
        evening_departure = datetime.strptime(self.project.evening_commute_start, "%H:%M")
        days = ["m","t","w","h","f"]
        times = ["morning","evening"]
        values = ["duration_in_traffic"]
        # get today's data and calculate days until NEXT monday
        today = datetime.today()
        days_until_monday = (0-today.weekday()) % 7
        if days_until_monday == 0: # today is a monday, we want the next one
            # get the date of next monday
            days_until_monday = 7
        # get the calendar date seven days from today
        next_monday = today + timedelta(days=days_until_monday)
        #next_monday = today.replace(day=today.day+days_until_monday)
        # based off of next_monday, create morning and evening date time objects for commute departure times in project attributes
        commutes = {'m_morning':datetime.combine(next_monday, morning_departure.time()),
                    'm_evening':datetime.combine(next_monday, evening_departure.time()),
                    't_morning':datetime.combine(next_monday+timedelta(days=1), morning_departure.time()),
                    't_evening':datetime.combine(next_monday+timedelta(days=1), evening_departure.time()),
                    'w_morning':datetime.combine(next_monday+timedelta(days=2), morning_departure.time()),
                    'w_evening':datetime.combine(next_monday+timedelta(days=2), evening_departure.time()),
                    'h_morning':datetime.combine(next_monday+timedelta(days=3), morning_departure.time()),
                    'h_evening':datetime.combine(next_monday+timedelta(days=3), evening_departure.time()),
                    'f_morning':datetime.combine(next_monday+timedelta(days=4), morning_departure.time()),
                    'f_evening':datetime.combine(next_monday+timedelta(days=4), evening_departure.time())
                    }
        """
        "commute_data.csv": ["office_address","origin_lat", "origin_long", "destination_lat", "destination_long", 
                                 "miles", "duration", "emissions", "commute_cost",
                                 "m_morning_duration_in_traffic", 
                                 "m_morning_emissions", 
                                 "m_evening_duration_in_traffic", 
                                 "m_evening_emissions",
                                 "t_morning_duration_in_traffic", 
                                 "t_morning_emissions", 
                                 "t_evening_duration_in_traffic", 
                                 "t_evening_emissions",
                                 "w_morning_duration_in_traffic", 
                                 "w_morning_emissions", 
                                 "w_evening_duration_in_traffic", 
                                 "w_evening_emissions",
                                 "h_morning_duration_in_traffic", 
                                 "h_morning_emissions", 
                                 "h_evening_duration_in_traffic", 
                                 "h_evening_emissions",
                                 "f_morning_duration_in_traffic", 
                                 "f_morning_emissions", 
                                 "f_evening_duration_in_traffic", 
                                 "f_evening_emissions"]
        """       
        # for each office location
        data_key = "employee_gps.csv" if self.project.use_gps_fuzzing==False or self.project.use_gps_fuzzing==False else "gps_fuzz.csv"
        for index, row in self.project.data["office_gps.csv"].iterrows():
            # for each employee+
            for index2, row2 in self.project.data[data_key].iterrows():
                data_row = len(self.project.data["commute_data.csv"])
                # create a row in the dataframe for this employee to this office, add initial data, use -1 for all incomplete calculations
                val= [row["address"],row2["latitude"], row2["longitude"],row["latitude"],row["longitude"]] + [-1.0 for i in range(24)]
                self.project.data["commute_data.csv"].loc[data_row] = val
                # calculate the commute time for this employee to this office
                for day in days:
                    for time in times:
                        # log iff logging
                        # create source and destination placeholders
                        if "evening" in time:
                            source = (row2["latitude"],row2["longitude"])
                            destination = (row["latitude"],row["longitude"])
                        else:
                            source = (row["latitude"],row["longitude"])
                            destination = (row2["latitude"],row2["longitude"])
                        if log_csv: 
                            log.write("Calculating commute time for " +str(source[0])+","+str(source[1])+" to "+str(destination[0])+","+str(destination[1])+" at "+str(commutes[day+"_"+time])+"\n")
                            log.flush()
                        print("Calculating commute time for " +str(source[0])+","+str(source[1])+" to "+str(destination[0])+","+str(destination[1])+" at "+str(commutes[day+"_"+time])+"\n")
                        # sleep if necessary for rate limit
                        self.sleepif()
                        try:
                            # get the commute time
                            commute = self.gAPI.commute((source[0],source[1]),(destination[0],destination[1]),commutes[day+"_"+time])
                        except Exception as e:
                            # if logging, write the exception event to the logfile
                            if log_csv:
                                log.write("Exception calling commute function: "+str(e)+"\n")
                                log.flush()
                            self.log_error("Exception calling commute function: "+str(e)+"\n")
                            # if the excetion is a recoverable one, retry after a delay, else raise the exception
                            if self.handle_GAPI_exception(e):
                                print("recoverable exception, waiting to retry once")
                                sleep(10000)
                                try:
                                    commute = self.gAPI.commute((source[0],source[1]),(destination(0),destination[1]),commutes[day+"_"+time])
                                except Exception as e:
                                    print("Recoverable exception, tried twice skipping address, deemed unrecoverable. "+str(e)+"\n")
                                    # if logging, write the exception event to the logfile
                                    self.log_error("Recoverable error calling commute function, failed twice. Deemed unrecoverable. Exception: "+str(e)+"\n")
                                    e.add_note = "Recoverable error calling commute function, failed twice. Deemed unrecoverable"
                                    raise e
                            else:
                                # print the full stack trace and raise e
                                print("Unrecoverable unknown exception, tried once. "+str(e)+"\n")
                                # if logging, write the exception event to the logfile
                                self.log_error("Unrecoverable error calling commute function, failed once. Exception: "+str(e)+"\n")
                                e.add_note = "Unrecoverable error calling commute function, failed once"
                                raise e
                        try:
                            # Update the row in the dataframe with the commute time
                            self.project.data["commute_data.csv"].loc[data_row,day+"_"+time+"_duration_in_traffic"] = float(self.convert_stringtime_to_minutes(commute["duration_in_traffic"]))
                            # if this is the first time through, insert the distance and duration into the dataframe
                            if day == "m" and time == "morning":
                                self.project.data["commute_data.csv"].loc[data_row,"miles"] = float(self.convert_stringdistance_to_d(commute["distance"]))
                                self.project.data["commute_data.csv"].loc[data_row,"duration"] = float(self.convert_stringtime_to_minutes(commute["duration"]))
                        except Exception as e:
                            # if logging, write the exception event to the logfile
                            if log_csv:
                                log.write("Exception updating commute data: "+str(e)+"\n")
                                log.flush()
                            self.log_error("Exception updating commute data: "+str(e)+"\n")
                            e.add_note = "Exception updating commute data after calling commute function."
                            raise e
                        
        # save the project data object to the csv file
        self.project.save_data_file("commute_data.csv")


    def convert_stringtime_to_minutes(self, time_string):
        """
        Converts a string representing distance into miles.

        Parses a string for distance measurements expressed in various units (miles, kilometers, meters, etc.) and converts 
        the total distance into miles.

        Args:
            distance_string (str): The distance string to convert.

        Returns:
            float: The total distance in miles.
        """

        # Regular expression to find all occurrences of numbers followed by time units
        matches = re.findall(r'(\d+)\s*(hour|minute|second|min|sec|hrs|hours|minutes|mins|seconds)s?', time_string, re.IGNORECASE)
        
        # Initialize a dictionary to hold our time values
        time_values = {'hours': 0, 'minutes': 0, 'seconds': 0}
        
        # Loop through all matches and update the time_values dictionary accordingly
        for amount, unit in matches:
            if unit.startswith('hour') or unit == 'hrs':
                time_values['hours'] += int(amount)
            elif unit.startswith('min'):
                time_values['minutes'] += int(amount)
            elif unit.startswith('sec'):
                time_values['seconds'] += int(amount)
        
        # create an integer to hold the total minutes
        total_minutes = 0
        # sum the hours and minutes into total minutes
        total_minutes += time_values['hours']*60
        total_minutes += time_values['minutes']
        return total_minutes


    def convert_stringdistance_to_d(self, distance_string):
        """
        Converts a string representing distance into miles.

        Parses a string for distance measurements expressed in various units (miles, kilometers, meters, etc.) and converts 
        the total distance into miles.

        Args:
            distance_string (str): The distance string to convert.

        Returns:
            float: The total distance in miles.
        """

        # Regular expression to find all occurrences of numbers followed by distance units
        matches = re.findall(r'(\b\d+(?:\.\d+)?)\s*(mile|kilometer|meter|foot|yard|inch|mi|km|m|ft|yd|in)s?', distance_string, re.IGNORECASE)
        
        # Initialize a dictionary to hold our distance values
        distance_values = {'miles': 0, 'kilometers': 0, 'meters': 0, 'feet': 0, 'yards': 0, 'inches': 0}
        # Loop through all matches and update the distance_values dictionary accordingly
        for amount, unit in matches:
            if unit.startswith('mile') or unit == 'mi':
                distance_values['miles'] += float(amount)
            elif unit.startswith('kilometer') or unit == 'km':
                distance_values['kilometers'] += float(amount)
            elif unit.startswith('meter') or unit == 'm':
                distance_values['meters'] += float(amount)
            elif unit.startswith('foot') or unit == 'ft':
                distance_values['feet'] += float(amount)
            elif unit.startswith('yard') or unit == 'yd':
                distance_values['yards'] += float(amount)
            elif unit.startswith('inch') or unit == 'in':
                distance_values['inches'] += float(amount)
        
        # create an integer to hold the total miles
        total_miles = 0
        # sum the miles into total miles
        total_miles += distance_values['miles']
        return total_miles
    
    def get_commute_cost(self, force=False):
        """
        Updates the commute data with calculated commute costs based on distances.

        Commute costs are calculated using the project's specified mileage rate applied to the commute distances for each employee.

        Args:
            force (bool, optional): If True, forces recalculation of commute costs even if they are already calculated. Defaults to False.

        Returns:
            bool: True if commute costs are successfully calculated; False otherwise.
        """
        # update the commute data to calculate the commute cost
        if "commute_data.csv" in self.project.list_data_files():
            if self.project.data["commute_data.csv"] is None or force:
                # attempt to load the commute data
                if self.project.load_data_file("commute_data.csv"):
                    pass
                else:
                    print("Errors loading commute data from project.")
                    return False
            else:
                pass
        else:
            print("Commute data missing from project.")
            return False
        # calculate the commute cost for each employee
        for index, row in self.project.data["commute_data.csv"].iterrows():
            # calculate the commute cost
            self.project.data["commute_data.csv"].loc[index,"commute_cost"] = float(row["miles"]) * float(self.project.mileage_rate)
        # save the project data object to the csv file
        self.project.save_data_file("commute_data.csv")
    
    def get_commute_emissions(self, force=False):
        """
        Calculates and updates commute data with emissions estimates based on commute distances.

        Commute emissions are calculated using the project's specified CO2 emissions per mile, applied to the commute distances 
        for each employee. Optionally adjusts emissions based on traffic conditions.

        Args:
            force (bool, optional): If True, forces recalculation of commute emissions even if they are already calculated. Defaults to False.

        Returns:
            bool: True if commute emissions are successfully calculated; False otherwise.
        """

        # update the commute data to calculate the commute emissions
        if "commute_data.csv" in self.project.list_data_files():
            if self.project.data["commute_data.csv"] is None or force:
                # attempt to load the commute data
                if self.project.load_data_file("commute_data.csv"):
                    pass
                else:
                    print("Errors loading commute data from project.")
                    return False
            else:
                pass
        else:
            print("Commute data missing from project.")
            return False
        # calculate the commute emissions for each row in the commute data
        for index, row in self.project.data["commute_data.csv"].iterrows():
            # calculate the commute emissions
            self.project.data["commute_data.csv"].loc[index,"emissions"] = float(row["miles"]) * float(self.project.CO2_per_mile)
            # calcualte the emissions for each day and time
            for day in ["m","t","w","h","f"]:
                for time in ["morning","evening"]:
                    # get the traffic regime for this commute
                    emissions_factor = self.get_traffic_emissions_factor(self.get_traffic_regime(row["miles"], row[day+"_"+time+"_duration_in_traffic"]))
                    self.project.data["commute_data.csv"].loc[index,day+"_"+time+"_emissions"] = float(row["miles"]) * float(self.project.CO2_per_mile) * emissions_factor
                    
        # save the project data object to the csv file
        self.project.save_data_file("commute_data.csv")


    def get_traffic_regime(self, distance, duration_in_traffic):
        """
        Determines the traffic regime based on the commute distance and duration in traffic.

        The traffic regime is an estimation of traffic conditions affecting the commute, categorized into levels based on the 
        relationship between the expected duration and the actual duration in traffic.

        Args:
            distance (float): The distance of the commute.
            duration_in_traffic (int): The duration of the commute in traffic in minutes.

        Returns:
            int: The traffic regime level, indicating the severity of traffic conditions.
    
        """
        # get the average speed
        average_speed = distance / (duration_in_traffic/60)
        # if the average speed is less than the lower bound of regime 2, return regime 1
        if average_speed < self.project.traffic_regime_2:
            return 1
        # if the average speed is less than the lower bound of regime 3, return regime 2
        if average_speed < self.project.traffic_regime_3:
            return 2
        # if the average speed is greater than or equal to the lower bound of regime 3, return regime 3
        return 3
        
    def get_traffic_emissions_factor(self, regime):
        """
        Retrieves the emissions factor associated with a given traffic regime.

        This method returns a multiplier that adjusts the calculated emissions based on the traffic regime, 
        with different factors indicating varying levels of traffic congestion.

        Args:
            regime (int): The traffic regime level as determined by get_traffic_regime method.

        Returns:
            float: The emissions factor corresponding to the specified traffic regime.
        """

        # return the emissions factor for the traffic regime
        if regime == 1:
            return float(self.project.traffic_regime_1_coeff)
        if regime == 2:
            return float(self.project.traffic_regime_2_coeff)
        if regime == 3:
            return float(self.project.traffic_regime_3_coeff)
        return 1.0

    def handle_GAPI_exception(self, exception):
        """
        Determines the course of action for a given Google API exception.

        Based on the type of exception encountered during API calls, this method decides whether the exception is recoverable 
        (suggesting a retry might succeed) or if it's unrecoverable, necessitating alternate handling.

        Args:
            exception (Exception): The exception encountered during a Google API call.

        Returns:
            bool: True if the exception is considered recoverable, False otherwise.
        """

        # Extract the type of the exception as a string
        exception_type = exception.__class__.__name__
        
        # Check if the exception type is in our predefined dictionary
        if exception_type in self.gAPI.google_api_exceptions:
            action = self.gAPI.google_api_exceptions[exception_type]
            if action == 'recoverable':
                return True
            else:
                return False
        else:
            print("Encountered an undefined exception type (" + str(exception) + "). Raising the exception...")
            return False

    def generate_graphs(self, graph="_all"):
        """
        Generates and saves graphical representations of analyzed commute data.

        Based on the available commute data, this method generates graphs such as the geographical distribution 
        of analyzed locations and the local analysis of commute geography. It supports generating all graphs or 
        a specific one based on the `graph` parameter.

        Args:
            graph (str, optional): Specifies which graph to generate. Use "_all" to generate all graphs, or specify a 
            particular graph's key. Defaults to "_all".

        Returns:
            list: A list of dictionaries, each containing details about the generated graphs, including file paths and titles.
        """

        # define a color palette supporting up to 10 unique colors
        color_palette = ['#6e7c8a', '#90a08f', '#c3a3a9', '#b1c5c3', '#e1c08b', '#a592ba', '#a8b1d5', '#d4abad', '#c4c38a', '#ceb2ab']
                        # lighter pastel ['#7D8A97', '#A3B0A2', '#D3BCC0', '#C9D7D6', '#EAD2AC', '#B8A9C9', '#C5CBE3', '#E3C8C9', '#D1D0A3', '#DECBC6']

        # Create a new list of colors "i" long, recycling colors as needed
        def colors(i):
            return color_palette[i % len(color_palette)]

        # generate the graphs for the project
        # if the commute data isn't already in the project, load it
        if "commute_data.csv" in self.project.list_data_files():
            if self.project.data["commute_data.csv"] is None:
                # attempt to load the commute data
                if self.project.load_data_file("commute_data.csv"):
                    pass
                else:
                    print("Errors loading commute data from project.")
                    return False
            else:
                pass
        else:
            print("Commute data missing from project.")
            return False
        
        # create the graphing object
        self.graphing = Graphing()
        
        # create a list of dicts to map the graphs to return to UI, they will be plotted in the order they are listed
        self.graph_list = []
 
        ### generate the graphs  ###
        plots_dir = os.path.join(self.project_directory, self.project.project_name, "plots")
        # get the baseline data
        emp = self.project.get_emp_gps()
        
        offices = self.project.get_office_gps()
        commute_data = self.project.get_commute_data()
        
        # helper function to get a base cost dataframe
        def get_base_cost_df(emp, officeaddr):
            rows = []
            for index, row in emp.iterrows():
                cost = 0.0
                rows.append({'latitude':row['latitude'],'longitude':row['longitude'],'office':officeaddr,'cost':cost})
            #cost_df = pd.DataFrame(rows)
            return rows
            
        ################################################################################ 
        # GRAPH: 
        ## Geographical Distribution of Analyzed Locations
        title="Geographical Distribution of Analyzed Locations"
        key = "gdal"
        self.graph_list.append( {"GRAPH": key,
                                 "TITLE": title,
                                 "FILENAME": key+".png",
                                "PLOT-DESCRIPTION": "Employee addresses and potential office locations are visualized on a map, " + \
                                    "including those which may be outside of the commuting radius.  A total of "+str(len(emp))+" employee addresses " + \
                                    "and "+str(len(offices))+" office locations are included in the analysis."               
                                })
        if graph == "_all" or graph == key:
            plt, ax = self.graphing.get_map_view(emp, offices, title=title, font_mod=1.5,
                                                 commute_color=False, commute_data=commute_data, convex_hull=False, size_o=400, size_e=40)
            plt.tight_layout(pad=1.0)
            plt.savefig(plots_dir+"/gdal.png")
            plt.close()

        ################################################################################
        ### GRAPH SET: Local Analysis for Office X
        # iterate through offices, generate a graph for each office
        for index, row in offices.iterrows():
            ################################################################################ 
            # GRAPH: 
            ## Local Analysis for Office X
            key = 'lafo'+str(index)
            OfficeAddr = row["address"]
            title = "Employee Distribution for "+OfficeAddr
            short_title = "Employee Distribution for Office "+str(index+1)
            self.graph_list.append( {"GRAPH": key,
                                    "TITLE": short_title,
                                    "FILENAME": key+".png",
                                    "PLOT-DESCRIPTION": "This graph displays the commute cutoff distribution for employees relative to the office at "+OfficeAddr+". " + \
                                                        "The cutoff distance is "+str(self.project.commute_range_cut_off)+" miles. The circle represents the linear distance " + \
                                                        "but more importantly is the actual driving distance represented by the convex hull, the shape of which is a result of " + \
                                                        "roadway complexities.  The bounded region will vary widely between offices analyzed."
                                                        
                                    })
            if graph == "_all" or graph == key:
                #just get the first office row
                #offices = pd.DataFrame(offices.iloc[0],offices.columns).reset_index(drop=True)
                office = row.to_frame().T
                plt, ax = self.graphing.get_map_view(emp, office, title="Employee Distribution for \n"+OfficeAddr, 
                                                    cutoff_distance=self.project.commute_range_cut_off*2,
                                                    commute_radius=self.project.commute_range_cut_off, font_mod=1.5,
                                                    commute_color=True, commute_data=commute_data, convex_hull=True, legend_loc='lower right')
                plt.tight_layout(pad=1.0)
                plt.savefig(plots_dir+"/"+key+".png")
                plt.close()

                # get the employees within the cutoff distance by driving distance, then add the count to the plot description
                emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
                self.graph_list[-1]["PLOT-DESCRIPTION"] = self.graph_list[-1]["PLOT-DESCRIPTION"] + " There are " + str(len(emp_within)) + \
                                                                " of the total " + str(len(emp)) + " employees within the cutoff distance, a total of " + \
                                                                str(round(len(emp_within)/len(emp)*100,2)) + "% of the total employees."

        ################################################################################ 
        # GRAPH: 
        ## Local Analysis of Commute Geography
        key = 'lacg'
        #OfficeAddr = row["address"]
        title = "Local Analysis of Commute Geography"
        short_title = title
        self.graph_list.append( {"GRAPH": key,
                                "TITLE": short_title,
                                "FILENAME": key+".png",
                                "PLOT-DESCRIPTION": "The graph displays several key observations.  Firstly, the green points are employees whose remote work " + \
                                                    "status will be unaffected by the relocation. The red points within the green convex hull will have remote " + \
                                                    "work status affected by the relocation while those outside the green convex hull remain unaffected by all scenarios. " + \
                                                    "Black circles represent a bounding linear distance of " + str(self.project.commute_range_cut_off) +" miles from each office options for perspective."
                                })
        if graph == "_all" or graph == key:
            plt, ax = self.graphing.get_map_view(emp, offices, title=title, 
                                                 cutoff_radius=self.project.commute_range_cut_off*2,
                                                 commute_radius=self.project.commute_range_cut_off, legend_loc='lower left', font_mod=1.5,
                                                 commute_color=True, commute_data=commute_data, convex_hull=True,size_o=500)
            plt.tight_layout(pad=1.0)
            plt.savefig(plots_dir+"/"+key+".png")
            plt.close()


        ################################################################################ 
        # GRAPH: 
        ## Employees Impacted by Remote Work Policy & Relocation
        key = 'lacg2'
        title = "Employees Impacted by Remote Work Policy & Relocation"
        short_title = title
        self.graph_list.append( {"GRAPH": key,
                                "TITLE": short_title,
                                "FILENAME": key+".png",
                                "PLOT-DESCRIPTION": "deferred"                                
                                })
        
        if graph == "_all" or graph == key:
            plt, ax = self.graphing.get_map_view(emp, offices, title=title, font_mod=1.5,
                                                 cutoff_radius=self.project.commute_range_cut_off*1.2,
                                                 commute_radius=self.project.commute_range_cut_off, 
                                                 commute_color=False, commute_data=commute_data, convex_hull=False,size_o=500, manual_plot=True)
            
            emp_within, emp_outside, emp_overlap, emp_within_all, emp_outside_all = None, None, None, None, None
            
            emp_within = self.graphing.filter_drive_distance(emp,offices,self.project.commute_range_cut_off, commute_data=commute_data, inside=True)
            emp_outside = self.graphing.filter_drive_distance(emp,offices,self.project.commute_range_cut_off, commute_data=commute_data, inside=False)
            if not emp_within.empty and not emp_outside.empty:                
                emp_overlap = self.graphing.get_common_points(emp_within,emp_outside)
            if not emp_within.empty and not emp_outside.empty:
                emp_outside_all = self.graphing.get_unique_points(emp_outside,emp_overlap)
            if not emp_within.empty and not emp_outside.empty:
                emp_within_all = self.graphing.get_unique_points(emp_within,emp_overlap)
            emp_within_list = []
            hullvars = {"color":"red","linewidth":50,"alpha":0.07}
            for i, row in offices.iterrows():
                office = row.to_frame().T
                emp_within_list.append(self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data, inside=True))
                self.graphing.plot_convex_hull(ax, emp_within_list[i], **hullvars)

            # plot the points
            if emp_within_all is not None and not emp_within_all.empty:
                self.graphing.plot_addresses(ax, emp_within_all, color='green', label="Unaffected by \nRelocation Decision")
            #if emp_outside_all is not None and not emp_outside_all.empty:
                #self.graphing.plot_addresses(ax, emp_outside_all,color='gray',label="Outside Commute \nRadius for Offices")
            if emp_overlap is not None and not emp_overlap.empty:
                self.graphing.plot_addresses(ax, emp_overlap, color='red',s=50, label="Impacted by \nRelocation Decision")
            self.graphing.plot_offices(ax, offices, s=400, label="Potential Office Locations")
            if emp_within_all is not None and not emp_within_all.empty:
                self.graphing.plot_convex_hull(ax, emp_within_all, color='red')
            if emp_overlap is not None and not emp_overlap.empty:
                self.graphing.plot_convex_hull(ax, emp_overlap, color='gray')
            self.graphing.add_scalebar(ax,font_mod=1.5)
            # add legend
            handles, labels = plt.gca().get_legend_handles_labels()
            self.graphing.map_view_standard_legend(ax, handles, labels, fontsize=15)
            plt.title(title, fontsize=25)
            plt.tight_layout(pad=1.0)
            plt.savefig(plots_dir+"/"+key+".png")
            plt.close()
            

            # udpate the plot description
            self.graph_list[-1]["PLOT-DESCRIPTION"] = "This graph displays the " + str(0 if emp_overlap is None or emp_overlap.empty else len(emp_overlap)) + " employees that are impacted by the relocaiton.  " + \
                                "Specifically, the red indicates employees that either rotate into, or out of the remote work policy by cutoff-distance. This is " + \
                                str(0 if emp_overlap is None or emp_overlap.empty else round(len(emp_overlap)/len(emp)*100,2)) + "% of the total employees.  "
        

        ################################################################################ 
        # GRAPH: 
        ## Baseline Commute Cost Analysis
        key = 'bcca'
        title = "Baseline Commute Cost Analysis"
        short_title = title
        self.graph_list.append( {"GRAPH": key,
                                "TITLE": short_title,
                                "FILENAME": key+".png",
                                "PLOT-DESCRIPTION": "deferred"
                                })
        
        if graph == "_all" or graph == key:
            # get the value to plot
            value = ['commute_cost']
            # baseline will be first office, assumed to be the current office, or "as is use case"
            office = offices.iloc[0].to_frame().T
            # employees to analyze are within the cutoff distance for this office
            emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
            # get commute cost values 
            cost_values = self.graphing.get_commute_values(emp_within, office, commute_data, value)
            # calculate the bin list based upon a the max value of the data
            binmax = int(max(cost_values['commute_cost'])+1)
            step = 1
            # round the binmax up to the nearest step
            bins = range(0, int(binmax + step - (binmax % step)), step)
            plt, ax = self.graphing.get_histogram(emp_within, office, commute_data, value, suptitle="",
                                      x_label=str('\$ (USD) based on \$'+str(self.project.mileage_rate)+' per mile.'), y_label='# Employees',
                                      bins=bins, rows=1, cols=1, column_titles=["Baseline Commute Cost Analysis for "+office["address"].values[0] ], cumulative_line=False, font_mod=1, figsize=(10,6))
            
            # udpate the plot description
            median_cost = round(np.median(cost_values['commute_cost']),2)
            average_cost = round(np.mean(cost_values['commute_cost']),2)
            commutes = 2*self.project.commute_days_per_week*self.project.commute_weeks_per_year
            self.graph_list[-1]["PLOT-DESCRIPTION"] = "This graph displays the distribution of commute costs for employees within the " + \
                                                    "cutoff distance of the office at "+office["address"].values[0]+".  " + \
                                                    "The median cost per commute is $"+"{:.2f}".format(median_cost)+", and the average cost per commute is $"+"{:.2f}".format(average_cost)+", one way. " + \
                                                    "For 2 commutes per day, " + str(self.project.commute_days_per_week) + \
                                                    " days per week, and " + str(self.project.commute_weeks_per_year) + " weeks per year (" + str(commutes) + " commutes/yr), the " + \
                                                    "median and average annual cost per employee is $"+"{:.2f}".format(round(median_cost*commutes,2))+" and $"+"{:.2f}".format(round(average_cost*commutes,2))+" respectively not including tolls, etc. " + \
                                                    "Minimum and maximum annual costs within the designated commute range are: $" + "{:.2f}".format(round(min(cost_values['commute_cost']*commutes),2)) + " and $" + \
                                                    "{:.2f}".format(round(max(cost_values['commute_cost']*commutes),2)) + " respectively.  In total, the workforce within the cutoff distance " + \
                                                    "has a total annual commute cost of $"+"{:,.2f}".format(round(sum(cost_values['commute_cost'])*commutes,2))+". Values based on $"+str(self.project.mileage_rate)+" per mile."
            
            # add a text box with the stats, using two decimal places and adding commas at the thousands
            t = {'me' : 'Median: |${:,.2f}'.format(median_cost*commutes),
                'av' : 'Average: |${:,.2f}'.format(average_cost*commutes),
                'mi' : 'Min: |${:,.2f}'.format(round(min(cost_values['commute_cost']*commutes),2)),
                'ma' : 'Max: |${:,.2f}'.format(round(max(cost_values['commute_cost']*commutes),2)),
                'to' : 'Total: |${:,.2f}'.format(round(sum(cost_values['commute_cost'])*commutes,2))
                }
            # get the longest string value
            max_len = max(len(t['me']),len(t['av']),len(t['to']),len(t['mi']),len(t['ma']))
            # calculate how many narrow numbers/letters exist in the string, we need to add additional space for each
            for k in t:
                t[k] = t[k].replace("|"," "*(max_len-len(t[k])))


            # add spaces to make all the same length, replacing |
            textstr = "Annualized Costs: "
            for k in t:
                textstr += "\n" + t[k]
            
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.2)
                
            ax.text(.95, .5, textstr, fontsize=10, transform=ax.transAxes,
                        verticalalignment='center', bbox=props, fontdict={'family': 'monospace'}, horizontalalignment='right')


            plt.tight_layout(pad=1.0)
            plt.savefig(plots_dir+"/"+key+".png")
            plt.close()

            

        ################################################################################ 
        # GRAPH: 
        ## Commute Costs per Office
        key = 'ccpo'
        title = "Commute Costs per Office"
        short_title = title
        self.graph_list.append( {"GRAPH": key,
                                "TITLE": short_title,
                                "FILENAME": key+".png",
                                "PLOT-DESCRIPTION": "This graph displays the distribution of commute costs for employees within the " + \
                                                    "cutoff distance of the office options. Overall commute costs are shown for each office " + \
                                                    "option.  This analysis inlcudes only per mile costs, not including tolls, etc.  " + \
                                                    "Costs due to cash equivalent for time not included."
                                })
        
        if graph == "_all" or graph == key:
            # get the value to plot
            value = []
            # employees to analyze are within the cutoff distance for this office
            # for this analysis, we need to iterate through options
            emp_within = []
            office_addrs = []
            cost_values = []
            median_costs = []
            average_costs = []
            total_costs = []
            min_costs = []
            max_costs = []
            for index, row in offices.iterrows():
                office = row.to_frame().T
                emp_within.append(self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data))
                office_addrs.append(office["address"].values[0])
                value.append('commute_cost')
                cost_values.append(self.graphing.get_commute_values(emp_within[-1], office, commute_data, value[-1]))
                commutes = 2*self.project.commute_days_per_week*self.project.commute_weeks_per_year
                median_costs.append(round(np.median(cost_values[-1]['commute_cost'])*commutes,2))
                average_costs.append(round(np.mean(cost_values[-1]['commute_cost']*commutes),2))
                total_costs.append(round(sum(cost_values[-1]['commute_cost'])*commutes,2))
                min_costs.append(round(min(cost_values[-1]['commute_cost']*commutes),2))
                max_costs.append(round(max(cost_values[-1]['commute_cost']*commutes),2))


            # calculate the bin list based upon a the max value of the data
            #binmax = int(max(cost_values['commute_cost'])+1)
            binmax = 0
            for i in range(len(cost_values)):
                if max(cost_values[i]['commute_cost']) > binmax:
                    binmax = max(cost_values[i]['commute_cost'])
            step = 1
            # round the binmax up to the nearest step
            bins = range(0, int(binmax + step - (binmax % step)), step)
            plt, ax = self.graphing.get_histogram(emp, offices, commute_data, value, suptitle="", cutoff_radius=self.project.commute_range_cut_off,
                                      x_label=str('\$ (USD), one-way, based on \$'+str(self.project.mileage_rate)+' per mile.'), y_label='# Employees',
                                      bins=bins, rows=len(office_addrs), cols=1, column_titles=["Commute Cost Analysis for Options"], 
                                      cumulative_line=False, font_mod=1.5, manual_plot=True)
            
            # manually add histograms for each office option
            for i in range(len(emp_within)):
                ax[i].hist(cost_values[i]['commute_cost'], bins=bins, alpha=0.5, edgecolor='#555555', linewidth=1, zorder=2, align='mid', 
                           rwidth=0.8, label=office_addrs[i], color=colors(i))
                ax[i].tick_params(axis='both', which='major', labelsize=16)
                
                # add a legend to show the office options
                ax[i].legend(loc='upper right', fontsize=16)
                
                # add a text box with the stats, using two decimal places and adding commas at the thousands
                t = {'me' : 'Median: |${:,.2f}'.format(median_costs[i]),
                    'av' : 'Average: |${:,.2f}'.format(average_costs[i]),
                    'mi' : 'Min: |${:,.2f}'.format(min_costs[i]),
                    'ma' : 'Max: |${:,.2f}'.format(max_costs[i]),
                    'to' : 'Total: |${:,.2f}'.format(total_costs[i])
                    }             
                # get the longest string value
                max_len = max(len(t['me']),len(t['av']),len(t['to']),len(t['mi']),len(t['ma']))
                
                # calculate how many narrow numbers/letters exist in the string, we need to add additional space for each
                for k in t:
                    t[k] = t[k].replace("|"," "*(max_len-len(t[k])))


                # add spaces to make all the same length, replacing |
                textstr = "Annualized Costs: "
                for k in t:
                    textstr += "\n" + t[k]
                # these are matplotlib.patch.Patch properties
                props = dict(boxstyle='round', facecolor='wheat', alpha=0.2)
                # place a text box in upper right in axes coords, 
                ax[i].text(.95, .5, textstr, transform=ax[i].transAxes, fontsize=14,
                            verticalalignment='center', bbox=props, fontdict={'family': 'monospace'}, horizontalalignment='right')
                
            
            plt.tight_layout(pad=1.0)
            plt.savefig(plots_dir+"/"+key+".png")
            plt.close()

            
            
        
        ################################################################################ 
        # GRAPH: 
        ## Employee Commute Cost Differential Analysis
        key = 'eccda'
        title = "Employee Commute Cost Differential Analysis"
        short_title = title
        self.graph_list.append( {"GRAPH": key,
                                "TITLE": short_title,
                                "FILENAME": key+".png",
                                "PLOT-DESCRIPTION": "This graph displays the distribution of commute costs for employees within the " + \
                                                    "cutoff distance of the office options. Changes in per-employee commute costs are shown for each office " + \
                                                    "option relative to the existing office locaton.  This analysis inlcudes only per mile costs, not including tolls, etc.  " + \
                                                    "Costs due to cash equivalent for time not included."
                                })
        
        if graph == "_all" or graph == key:
            # get the value to plot
            value = []
            # employees to analyze are within the cutoff distance for this office
            # for this analysis, we need to iterate through options
            current_office = offices.iloc[0].to_frame().T
            other_offices = offices.drop(0)
            cost_values = []
            withins = []
            commutes = 2*self.project.commute_days_per_week*self.project.commute_weeks_per_year
            
            # for each employee, calculate the commute cost to the current office, place a new dataframe with lat, long, office, and cost
            # if the employee is within the cutoff distance, if outside the cutoff distance, the cost is 0
            # start by looping through ALL employees and adding a row with the current office, and cost = 0
                    

            base_costs = pd.DataFrame(get_base_cost_df(emp, current_office['address'].values[0]))
            # now get emp_within for the current office, and update the relevant rows of base_costs with actual costs for those employees 
            # using the commute_cost column in the commute_data dataframe where the employee lat long matches the commute_data lat long and office address
            
            base_emp_within = self.graphing.filter_drive_distance(emp,current_office,self.project.commute_range_cut_off, commute_data=commute_data)

            for index, row in base_emp_within.iterrows():
                # get the cost from the commute_data
                cost = commute_data[(commute_data['origin_lat'] == row['latitude']) & (commute_data['origin_long'] == row['longitude']) & (commute_data['office_address'] == current_office['address'].values[0])]['commute_cost'].values[0]
                base_costs.loc[(base_costs['latitude'] == row['latitude']) & (base_costs['longitude'] == row['longitude']),'cost'] = cost
            # now we have a dataframe with all employees, and the cost to the current office
        
            # now iterate through the other offices, get a base cost dataframe, and then update the relevant rows with actual costs, place in cost_values
            for index, row in other_offices.iterrows():
                office = row.to_frame().T
                tmp_costs = pd.DataFrame(get_base_cost_df(emp, office['address'].values[0]))
                emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
                # we will use this later to get the differential for each employee, without the employees that aren't overlapping
                withins.append(emp_within)
                for index, row in emp_within.iterrows():
                    # get the cost from the commute_data
                    cost = commute_data[(commute_data['origin_lat'] == row['latitude']) & (commute_data['origin_long'] == row['longitude']) & (commute_data['office_address'] == office['address'].values[0])]['commute_cost'].values[0]
                    tmp_costs.loc[(tmp_costs['latitude'] == row['latitude']) & (tmp_costs['longitude'] == row['longitude']),'cost'] = cost
                cost_values.append(tmp_costs)
            
            # now we have a full list of costs for each employee to each office, we can get the differentials
            # create a list to hold the differential dataframes
            diffs = []
            # for each cost dataframe, calculate the differential from the base_costs dataframe into a new dataframe
            for i in range(len(cost_values)):
                # get the differential
                diffs.append(cost_values[i]['cost'] - base_costs['cost'])
            # now we have a list of dataframes with the differentials, we eliminate all rows with 0 cost differential to prevent skewing the histogram
            # calculate the bin list based upon a the min (negative) and max (positive) values of the data     
            binmin = 0
            binmax = 0
            for i in range(len(diffs)):
                if min(diffs[i]) < binmin:
                    binmin = min(diffs[i])
                if max(diffs[i]) > binmax:
                    binmax = max(diffs[i])
            step = 1
            # round the binmin down to the nearest step, max up to the nearest step
            bins = range(int(binmin - (binmin % step)), int(binmax + step - (binmax % step)), step)

            plt, ax = self.graphing.get_histogram(emp, other_offices, commute_data, value, suptitle="Employee Commute Cost Differential Analysis", cutoff_radius=self.project.commute_range_cut_off,
                                      x_label=str('\$ (USD) based on \$'+str(self.project.mileage_rate)+' per mile.'), y_label='# Employees (log scale)',
                                      bins=bins, rows=len(other_offices), cols=1, column_titles=["Employee Commute Cost Differential Analysis"], 
                                      cumulative_line=False, font_mod=1.5, manual_plot=True)
            
            # manually add histograms for each office option
            for i in range(len(diffs)):
                ax[i].hist(diffs[i], bins=bins, alpha=0.5, edgecolor='#555555', linewidth=1, zorder=2, align='mid', 
                           rwidth=0.8, label=other_offices['address'].values[i], color=colors(i+1))
                ax[i].tick_params(axis='both', which='major', labelsize=16)
                
                # add a legend to show the office options
                ax[i].legend(loc='upper right', fontsize=16)
                
                # add a text box with the stats, using two decimal places and adding commas at the thousands
                t = {'me' : 'Median: |${:,.2f}'.format(np.median(diffs[i]*commutes)),
                    'av' : 'Average: |${:,.2f}'.format(np.mean(diffs[i]*commutes)),
                    'mi' : 'Min: |${:,.2f}'.format(min(diffs[i])*commutes),
                    'ma' : 'Max: |${:,.2f}'.format(max(diffs[i])*commutes),
                    'to' : 'Total: |${:,.2f}'.format(sum(diffs[i])*commutes)
                    }             
                # get the longest string value
                max_len = max(len(t['me']),len(t['av']),len(t['to']),len(t['mi']),len(t['ma']))
                
                # calculate additional space
                for k in t:
                    t[k] = t[k].replace("|"," "*(max_len-len(t[k])))


                # add spaces to make all the same length, replacing |
                textstr = "Annualized \nDifferentials: "
                for k in t:
                    textstr += "\n" + t[k]
                # these are matplotlib.patch.Patch properties
                props = dict(boxstyle='round', facecolor='wheat', alpha=0.2)
                # place a text box in upper left in axes coords, 
                ax[i].text(.05, .75, textstr, transform=ax[i].transAxes, fontsize=14,
                            verticalalignment='center', bbox=props, fontdict={'family': 'monospace'}, horizontalalignment='left')
                
                # now, take the base_cost and the cost_values[i] and get the differential for each employee omitting 
                # any employees that are zero cost in one, and not zero cost in the other
                # this will omit those employees who rotated to/from remote work status as a result of the move.
                mask = (cost_values[i]['cost'] != 0) & (base_costs['cost'] != 0)
                differences = (cost_values[i]['cost'] - base_costs['cost'])[mask]
                
                # Convert differences to a list and store in diffs
                diffs2 = differences.tolist()

                # get the differential
                # get the stats
                median = np.median(diffs2)*commutes
                average = np.mean(diffs2)*commutes
                minimum = min(diffs2)*commutes
                maximum = max(diffs2)*commutes
                total = sum(diffs2)*commutes
               
                # add a text box with the stats, using two decimal places and adding commas at the thousands
                t = {'me' : 'Median: |${:,.2f}'.format(median),
                    'av' : 'Average: |${:,.2f}'.format(average),
                    'mi' : 'Min: |${:,.2f}'.format(minimum),
                    'ma' : 'Max: |${:,.2f}'.format(maximum),
                    'to' : 'Total: |${:,.2f}'.format(total)
                    }
                
                # get the longest string value
                max_len = max(len(t['me']),len(t['av']),len(t['to']),len(t['mi']),len(t['ma']))
                # calculate how many narrow numbers/letters exist in the string, we need to add additional space for each
                for k in t:
                    t[k] = t[k].replace("|"," "*(max_len-len(t[k])))
                # add spaces to make all the same length, replacing |
                textstr = "Annualized Differentials omitting \n Employees Rotating to/from Remote Work: "
                for k in t:
                    textstr += "\n" + t[k]
                # place a text box in upper right in axes coords, 
                ax[i].text(.95, .75, textstr, transform=ax[i].transAxes, fontsize=14,
                            verticalalignment='center', bbox=props, fontdict={'family': 'monospace'}, horizontalalignment='right')
                

                ax[i].set_yscale('log')


            plt.tight_layout(pad=1.0)
            plt.savefig(plots_dir+"/"+key+".png")
            plt.close()
            
        

        ################################################################################
        ### GRAPH SET: Local Analysis for Office X
        # iterate through offices, generate a graph for each office
        for index, row in offices.iterrows():  
        ################################################################################ 
            # GRAPH: 
            ## Weekly Commute Duration Analysis
            key = 'wcda'+str(index)
            title = "Weekly Commute Duration Analysis "+str(row["address"])
            short_title = title
            self.graph_list.append( {"GRAPH": key,
                                    "TITLE": short_title,
                                    "FILENAME": key+".png",
                                    "PLOT-DESCRIPTION":  "This graph displays the the morning and evening commute durations for employees within the " + \
                                                        "cutoff distance of the current office.  The analysis is broken down by day of the week, " + \
                                                        "and the distribution of commute times is shown for each day.  The commute times are based on " + \
                                                        "the commute data derived based on traffic conditions, and are in minutes. The analysis is specific " + \
                                                        "to the office at "+row["address"]+"."
                                    })
            
            if graph == "_all" or graph == key:
                # only calculate for the first office, the current office
                #office = offices.iloc[0].to_frame().T
                office = row.to_frame().T
                values = ['m_morning_duration_in_traffic','m_evening_duration_in_traffic',
                        't_morning_duration_in_traffic','t_evening_duration_in_traffic',
                        'w_morning_duration_in_traffic','w_evening_duration_in_traffic',
                        'h_morning_duration_in_traffic','h_evening_duration_in_traffic',
                        'f_morning_duration_in_traffic','f_evening_duration_in_traffic']
                cumulative_markers = {50: {'color': 'purple', 'marker': 'x', 'label': '50%', 'linestyle': '--', 'linewidth': 1},
                                    75: {'color': 'blue', 'marker': 'x', 'label': '75%', 'linestyle': '--', 'linewidth': 1},}
                # calculate teh bins based on the max value of the data
                binmax = 0
                emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
                val_set = self.graphing.get_commute_values(emp_within, office, commute_data, values)
                # get max value of val_set
                # val_set is a DataFrame containing the extracted values for each employee location that matches the given office location. The DataFrame includes 'latitude' and 'longitude' of the employee locations and the specified `values`.
                for each in values:
                    if max(val_set[each]) > binmax:
                        binmax = max(val_set[each])            
                step = 5
                # round the binmax up to the nearest step
                bins = range(0, int(binmax + step - (binmax % step)), step)
                plt, ax = self.graphing.get_histogram(emp, office, commute_data, values, suptitle=str(row['address'])+" Commute Analysis", x_label='Minutes in Traffic', y_label='# Employees',  
                            commute_radius=self.project.commute_range_cut_off, bins=bins, rows=5, cols=2, column_titles=['Morning Commute','Evening Commute'], cumulative_line=True,
                            cumulative_color='black', cumulative_linestyle='--', cumulative_linewidth=1, cumulative_markers=cumulative_markers, font_mod=1.5)
                
                plt.legend(loc='center right')
                for each in plt.gcf().get_axes():
                    # Add monday through Friday labels on first column only
                    if each.get_subplotspec().colspan.start == 0:
                        # first row is monday, second is tuesday, etc
                        row = each.get_subplotspec().rowspan.start
                        if row == 0:
                            each.text(0.02, 0.85, 'Monday', fontsize=12, transform=each.transAxes, ha='left', va='top')
                        elif row == 1:
                            each.text(0.02, 0.85, 'Tuesday', fontsize=12, transform=each.transAxes, ha='left', va='top')
                        elif row == 2:
                            each.text(0.02, 0.85, 'Wednesday', fontsize=12, transform=each.transAxes, ha='left', va='top')
                        elif row == 3:
                            each.text(0.02, 0.85, 'Thursday', fontsize=12, transform=each.transAxes, ha='left', va='top')
                        elif row == 4:
                            each.text(0.02, 0.85, 'Friday', fontsize=12, transform=each.transAxes, ha='left', va='top')
                            
                plt.tight_layout(pad=1.0)
                plt.savefig(plots_dir+"/"+key+".png")
                plt.close()


        ################################################################################
        ### GRAPH SET: Local Analysis for Office X
        # iterate through offices, generate a graph for each office
        for index, row in offices.iterrows():            
            # GRAPH: 
            ## Normalized Weekly Commute Duration Analysis
            key = 'nwcda'+str(index)
            title = "Normalized Weekly Commute Duration Analysis "+str(row["address"])
            short_title = title
            self.graph_list.append( {"GRAPH": key,
                                    "TITLE": short_title,
                                    "FILENAME": key+".png",
                                    "PLOT-DESCRIPTION":  "This graph displays the the morning and evening commute durations for employees within the " + \
                                                        "cutoff distance of the current office, normalized to reflect the duration in traffic as a percentage " + \
                                                        " of the duration without traffic.  The analysis is broken down by day of the week, " + \
                                                        "and the distribution of commute times is shown for each day.  The commute times are based on " + \
                                                        "the commute data derived based on traffic conditions, and are in minutes. The analysis is specific " + \
                                                        "to the office at "+row["address"]+"."
                                    })
            
            if graph == "_all" or graph == key:
                # only calculate for the first office, the current office
                #office = offices.iloc[0].to_frame().T
                office = row.to_frame().T
                values = ['m_morning_duration_in_traffic','m_evening_duration_in_traffic',
                        't_morning_duration_in_traffic','t_evening_duration_in_traffic',
                        'w_morning_duration_in_traffic','w_evening_duration_in_traffic',
                        'h_morning_duration_in_traffic','h_evening_duration_in_traffic',
                        'f_morning_duration_in_traffic','f_evening_duration_in_traffic']
                cumulative_markers = {50: {'color': 'purple', 'marker': 'x', 'label': 'Median (min)', 'linestyle': '--', 'linewidth': 1}}
                
                emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
                val_set = self.graphing.get_commute_values(emp_within, office, commute_data, values)
                val_set_free = self.graphing.get_commute_values(emp_within, office, commute_data, "duration")
                # Normalize the values in val_set by dividing by the corresponding values in val_set_free, and multiplying by 100
                for each in values:
                    val_set[each] = val_set[each] / val_set_free['duration'] * 100
                
                # calculate teh bins based on the max value of the data
                binmax = 0
                binmin = 100
                for each in values:
                    if max(val_set[each]) > binmax:
                        binmax = max(val_set[each])
                    if min(val_set[each]) < binmin:
                        binmin = min(val_set[each])            
                step = 5
                # round the binmax up to the nearest step, and binmin down to the nearest step
                bins = range(int(binmin - (binmin % step)), int(binmax + step - (binmax % step)), step)
                
                plt, ax = self.graphing.get_histogram(emp, office, commute_data, values, suptitle="Normalized 'In Traffic' Commute Analysis, \n"+str(row['address']), 
                                                      x_label='Normalized (In-Traffic / Traffic-Free) \n Commute Duration (%)', y_label='# Employees',  
                            commute_radius=self.project.commute_range_cut_off, bins=bins, rows=5, cols=2, column_titles=['Morning Commute','Evening Commute'], cumulative_line=True,
                            cumulative_color='black', cumulative_linestyle='--', cumulative_linewidth=1, cumulative_markers=cumulative_markers, 
                            override_values=val_set, font_mod=1.5)
                
                
                plt.legend(loc='center right')
                for each in plt.gcf().get_axes():
                    # Add monday through Friday labels on first column only
                    if each.get_subplotspec().colspan.start == 0:
                        # first row is monday, second is tuesday, etc
                        row = each.get_subplotspec().rowspan.start
                        if row == 0:
                            each.text(0.02, 0.85, 'Monday', fontsize=12, transform=each.transAxes, ha='left', va='top')
                        elif row == 1:
                            each.text(0.02, 0.85, 'Tuesday', fontsize=12, transform=each.transAxes, ha='left', va='top')
                        elif row == 2:
                            each.text(0.02, 0.85, 'Wednesday', fontsize=12, transform=each.transAxes, ha='left', va='top')
                        elif row == 3:
                            each.text(0.02, 0.85, 'Thursday', fontsize=12, transform=each.transAxes, ha='left', va='top')
                        elif row == 4:
                            each.text(0.02, 0.85, 'Friday', fontsize=12, transform=each.transAxes, ha='left', va='top')
                            
                plt.tight_layout(pad=1.0)
                plt.savefig(plots_dir+"/"+key+".png")
                plt.close()



        ############################################################################################################
        # GRAPH:
        ## Normalized Commute Distribution Analysis
        key = 'ncda'
        title = "Normalized Commute Distribution Analysis"
        short_title = title
        self.graph_list.append( {"GRAPH": key,
                                "TITLE": short_title,
                                "FILENAME": key+".png",
                                "PLOT-DESCRIPTION":  "This graph plots the the normalized commute durations against the distance of the commute. " + \
                                                    "The objective is to affirm that the tails of the distribution are driven by shorter distance commutes " + \
                                                    "and therefore present minimal risk of skewing the analysis when an average across days/employees is taken."
                                })
        
        if graph == "_all" or graph == key:
            office = offices.iloc[0].to_frame().T
            values = ['m_morning_duration_in_traffic','m_evening_duration_in_traffic',
                    't_morning_duration_in_traffic','t_evening_duration_in_traffic',
                    'w_morning_duration_in_traffic','w_evening_duration_in_traffic',
                    'h_morning_duration_in_traffic','h_evening_duration_in_traffic',
                    'f_morning_duration_in_traffic','f_evening_duration_in_traffic']
            data_labels = ['Monday Morning','Monday Evening',
                    'Tuesday Morning','Tuesday Evening',
                    'Wednesday Morning','Wednesday Evening',
                    'Thursday Morning','Thursday Evening',
                    'Friday Morning','Friday Evening']
            emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
            val_set = self.graphing.get_commute_values(emp_within, office, commute_data, values)
            val_set_free = self.graphing.get_commute_values(emp_within, office, commute_data, "duration")
            val_set_miles = self.graphing.get_commute_values(emp_within, office, commute_data, "miles")
            # Normalize the values in val_set by dividing by the corresponding values in val_set_free, and multiplying by 100
            for each in values:
                val_set[each] = val_set[each] / val_set_free['duration'] * 100

            plt, ax = self.graphing.get_scatterplot(emp, office, commute_data, "miles", "duration", title=title, x_label='Normalized (In-Traffic / Traffic-Free) \n Commute Duration (%)', 
                                                    y_label='Commute Distance miles',
                                                    cutoff_radius=self.project.commute_range_cut_off, commute_radius=self.project.commute_range_cut_off, figsize=(15, 15), manual_plot=True, font_mod=1.5)
            # manually add scatter plots for each day
            for i in range(len(values)):
                ax.scatter(val_set[values[i]], val_set_miles['miles'],  alpha=0.5, edgecolor='#555555', linewidth=1, zorder=2, 
                           label=data_labels[i], color=colors(i))
                
                ax.tick_params(axis='both', which='major', labelsize=16)
              
                # add a legend to show the office options
                ax.legend(loc='upper right', fontsize=16)

            plt.tight_layout(pad=1.0)
            plt.savefig(plots_dir+"/"+key+".png")
            plt.close()


        ############################################################################################################
        # GRAPH:
        ## Normalized Commute Distribution Analysis Heat Map
        key = 'ncdahm'
        title = "Normalized Commute Distribution Analysis Heat Map"
        short_title = title
        self.graph_list.append( {"GRAPH": key,
                                "TITLE": short_title,
                                "FILENAME": key+".png",
                                "PLOT-DESCRIPTION":  "This graph plots the the normalized commute durations against the distance of the commute in a heat map. " + \
                                                    "The objective is to understand the geography driving any strong departures from average or standard deviation."
                                })
        
        if graph == "_all" or graph == key:
            office = offices.iloc[0].to_frame().T
            values = ['m_morning_duration_in_traffic','m_evening_duration_in_traffic',
                    't_morning_duration_in_traffic','t_evening_duration_in_traffic',
                    'w_morning_duration_in_traffic','w_evening_duration_in_traffic',
                    'h_morning_duration_in_traffic','h_evening_duration_in_traffic',
                    'f_morning_duration_in_traffic','f_evening_duration_in_traffic']
            data_labels = ['Monday Morning','Monday Evening',
                    'Tuesday Morning','Tuesday Evening',
                    'Wednesday Morning','Wednesday Evening',
                    'Thursday Morning','Thursday Evening',
                    'Friday Morning','Friday Evening']
            
            emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
            val_set = self.graphing.get_commute_values(emp_within, office, commute_data, commute_data.columns.to_list())
            # restore origin_lat and origin_long to the val_set
            val_set['origin_lat'] = val_set['latitude']
            val_set['origin_long'] = val_set['longitude']
            val_set_free = self.graphing.get_commute_values(emp_within, office, commute_data, "duration")
            # Normalize the values in val_set by dividing by the corresponding values in val_set_free, and multiplying by 100
            for each in values:
                val_set[each] = val_set[each] / val_set_free['duration'] * 100
            
            plt, ax = self.graphing.get_heatmap(emp_within, office, val_set, values[3], title=title, 
                                                value_label="Normalized Commute in Traffic (% vs. Free)", cutoff_distance=self.project.commute_range_cut_off, commute_radius=self.project.commute_range_cut_off,
                                                cmap='jet', alpha=0.3, levels=10, font_mod=1.5)

            plt.tight_layout(pad=1.0)
            plt.savefig(plots_dir+"/"+key+".png")
            plt.close()
            
        ################################################################################
        ### GRAPH SET: Local Analysis for Office X
        # iterate through offices, generate a graph for each office
        for index, row in offices.iterrows():    
        ############################################################################################################
            # GRAPH:
            ## Normalized Commute Standard Deviation Analysis
            key = 'ncsda'+str(index)
            title = "Normalized Commute Standard Deviation Analysis" + " for \n" + row["address"]
            short_title = title
            self.graph_list.append( {"GRAPH": key,
                                    "TITLE": short_title,
                                    "FILENAME": key+".png",
                                    "PLOT-DESCRIPTION":  "This graph shows the per-employee distribution of standard deviation to assess the " + \
                                    "validity of using the average commute time as a metric for comparison.  This analysis is specific to the " + \
                                    "office location at " + row["address"] + "."
                                    })
            
            if graph == "_all" or graph == key:
                office = row.to_frame().T
                values = ['m_morning_duration_in_traffic','m_evening_duration_in_traffic',
                        't_morning_duration_in_traffic','t_evening_duration_in_traffic',
                        'w_morning_duration_in_traffic','w_evening_duration_in_traffic',
                        'h_morning_duration_in_traffic','h_evening_duration_in_traffic',
                        'f_morning_duration_in_traffic','f_evening_duration_in_traffic']

                emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
                val_set = self.graphing.get_commute_values(emp_within, office, commute_data, values)
                val_set_free = self.graphing.get_commute_values(emp_within, office, commute_data, "duration")
                val_set_miles = self.graphing.get_commute_values(emp_within, office, commute_data, "miles")
                
                mean = val_set.loc[:,values].mean(axis=1)
                std = val_set.loc[:,values].std(axis=1)
                max_val = val_set.loc[:,values].max(axis=1)
                min_val = val_set.loc[:,values].min(axis=1)
                data_labels = ['Mean','Standard Deviation','Max','Min']
                x = [mean, std, max_val, min_val]
                # Normalize the values in val_set by dividing by the corresponding values in val_set_free, and multiplying by 100
                #for each in values:
                #   val_set[each] = val_set[each] / val_set_free['duration'] * 100

                plt, ax = self.graphing.get_scatterplot(emp, office, commute_data, "miles", "duration", title=title, x_label='Duration (min)', 
                                                        y_label='Commute Distance (miles)',
                                                        cutoff_radius=self.project.commute_range_cut_off, commute_radius=self.project.commute_range_cut_off, figsize=(15, 15), manual_plot=True, font_mod=1.5)
                
                # manually add scatter plots for each day
                #for i in range(len(data_labels)):
                i=1
                ax.scatter(x[i], val_set_miles['miles'],  alpha=0.5, edgecolor='#555555', linewidth=1, zorder=2,
                            label=data_labels[i])
                for i in range(len(val_set)):
                    # add end bars to the lines
                    ax.plot([min_val.iloc[i], max_val.iloc[i]], [val_set_miles['miles'].iloc[i], val_set_miles['miles'].iloc[i]], 'k-', marker='|', lw=1)   

                ax.tick_params(axis='both', which='major', labelsize=16)
                
                # add a legend to show the office options
                # add a legend entry for the label='Min/Max Spread'
                handles, labels = ax.get_legend_handles_labels()
                new_handle = Line2D([], [], color='black', label='Min/Max Spread', linestyle='-', linewidth=1, marker='|')
                new_label = 'In-Traffic Min/Max Spread for Week (miles)'
                handles.append(new_handle)
                labels.append(new_label)
            
                ax.legend(handles=handles, labels=labels, loc='lower right', fontsize=16)
                
                plt.tight_layout(pad=1.0)
                plt.savefig(plots_dir+"/"+key+".png")
                plt.close()
            

        ################################################################################
        ### GRAPH SET: Local Analysis for Office X
        # iterate through offices, generate a graph for each office
        for index, row in offices.iterrows():    
        ############################################################################################################
            # GRAPH:
            ## Time-Based Commute Cost Analysis
            key = 'tbcca'+str(index)
            title = "Time-Based Commute Cost Analysis" + " for \n" + row["address"]
            short_title = title
            self.graph_list.append( {"GRAPH": key,
                                    "TITLE": short_title,
                                    "FILENAME": key+".png",
                                    "PLOT-DESCRIPTION":  "This graph shows the average and high/conservative cost of employees commuting to " + \
                                    "the office location at " + row["address"] + ". The average cost is based upon the morning average and evening " + \
                                    "average commute times, while the high/conservative cost is based upon the highest morning maximum and evening values for " + \
                                    str(self.project.commute_days_per_week) + " days per week."
                                    })
            
            if graph == "_all" or graph == key:
                office = row.to_frame().T

                # get the needed commute values
                values = ['m_morning_duration_in_traffic','m_evening_duration_in_traffic',
                        't_morning_duration_in_traffic','t_evening_duration_in_traffic',
                        'w_morning_duration_in_traffic','w_evening_duration_in_traffic',
                        'h_morning_duration_in_traffic','h_evening_duration_in_traffic',
                        'f_morning_duration_in_traffic','f_evening_duration_in_traffic']
                
                mornings = ['m_morning_duration_in_traffic','t_morning_duration_in_traffic','w_morning_duration_in_traffic','h_morning_duration_in_traffic','f_morning_duration_in_traffic']
                evenings = ['m_evening_duration_in_traffic','t_evening_duration_in_traffic','w_evening_duration_in_traffic','h_evening_duration_in_traffic','f_evening_duration_in_traffic']
                cdpw = self.project.commute_days_per_week

                emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
                val_set = self.graphing.get_commute_values(emp_within, office, commute_data, values)
                
                

                # Calculate and insert the average morning and evening commute times directly into val_set
                val_set['Morning Average'] = val_set.loc[:, mornings].mean(axis=1)
                val_set['Evening Average'] = val_set.loc[:, evenings].mean(axis=1)

                # Calculate and insert the top 'cdpw' maximum morning and evening commute times
                # Note: Adjust the code below to calculate the averages of the top 'cdpw' as new columns directly
                val_set['Average Top CDPW Morning'] = val_set[mornings].apply(lambda row: row.nlargest(cdpw).mean(), axis=1)
                val_set['Average Top CDPW Evening'] = val_set[evenings].apply(lambda row: row.nlargest(cdpw).mean(), axis=1)

                # Calculate a per-minute cost based on "median_salary" and "hours_per_year"
                per_minute_cost = self.project.median_salary / (self.project.hours_per_year * 60)

                # Calculate and insert the average cost for the week directly into val_set
                val_set['Morning Average Cost'] = val_set['Morning Average'] * per_minute_cost
                val_set['Evening Average Cost'] = val_set['Evening Average'] * per_minute_cost

                # Calculate and insert the high/conservative cost for the week directly into val_set
                val_set['Morning High Cost'] = val_set['Average Top CDPW Morning'] * per_minute_cost
                val_set['Evening High Cost'] = val_set['Average Top CDPW Evening'] * per_minute_cost

                # create bins based on the max value of the data
                binmax = 0
                for each in ['Morning Average Cost','Evening Average Cost','Morning High Cost','Evening High Cost']:
                    if max(val_set[each]) > binmax:
                        binmax = max(val_set[each])
                step = 5
                # round the binmax up to the nearest step
                bins = range(0, int(binmax + step - (binmax % step)), step)
                
                font_mod = 1.5
                # create histograms for the morning and evening average costs
                plt, ax = self.graphing.get_histogram(emp, office, commute_data, ['m_morning_duration_in_traffic','m_evening_duration_in_traffic'], 
                                                      suptitle="Average and Maximum Time-in-Traffic Costs for \n"+str(row['address']), 
                                                      cutoff_radius=self.project.commute_range_cut_off,
                                      x_label=str('\$ (USD) based on median salary (converted to per minute)'), y_label='# Employees',
                                      bins=bins, rows=2, cols=2, column_titles=["Average","High/Conservative"], 
                                      cumulative_line=False, font_mod=font_mod, manual_plot=True, sharey=True, sharex=True)
                plot_vals = [['Morning Average Cost',"Morning High Cost"],["Evening Average Cost","Evening High Cost"]]
                # manually add histograms for each office option
                for r in range(2):
                    for c in range(2):
                        ax[r,c].hist(val_set[plot_vals[r][c]], bins=bins, alpha=0.5, edgecolor='#555555', linewidth=1, zorder=2, align='mid', 
                                rwidth=0.8, label=plot_vals, color=colors(r+1))
                        ax[r,c].tick_params(axis='both', which='major', labelsize=16)

                        # add a text box in the upper right corner with the stats
                        t = {'me' : 'Median: |${:,.2f}'.format(np.median(val_set[plot_vals[r][c]])),
                            'av' : 'Average: |${:,.2f}'.format(np.mean(val_set[plot_vals[r][c]])),
                            'mi' : 'Min: |${:,.2f}'.format(min(val_set[plot_vals[r][c]])),
                            'ma' : 'Max: |${:,.2f}'.format(max(val_set[plot_vals[r][c]])),
                            'to' : 'Total: |${:,.2f}'.format(sum(val_set[plot_vals[r][c]]))
                            }
                        # get the longest string value
                        max_len = max(len(t['me']),len(t['av']),len(t['to']),len(t['mi']),len(t['ma']))
                        # calculate additional space
                        for k in t:
                            t[k] = t[k].replace("|"," "*(max_len-len(t[k])))
                        # add spaces to make all the same length, replacing |
                        textstr = "Commute Time Cost: "
                        for k in t:
                            textstr += "\n" + t[k]
                        # these are matplotlib.patch.Patch properties
                        props = dict(boxstyle='round', facecolor='wheat', alpha=0.2)
                        # place a text box in upper right in axes coords,
                        ax[r,c].text(.95, .75, textstr, transform=ax[r,c].transAxes, fontsize=14,
                                    verticalalignment='center', bbox=props, fontdict={'family': 'monospace'}, horizontalalignment='right')
                        

                        # for the first column, add morning/evening text box the top left of the plot
                        if r==0 and c == 0:
                            ax[r,c].text(0.05, 0.85, 'Morning', fontsize=14*font_mod, transform=ax[r,c].transAxes, ha='left', va='top')
                        if r==1 and c == 0:
                            ax[r,c].text(0.05, 0.85, 'Evening', fontsize=14*font_mod, transform=ax[r,c].transAxes, ha='left', va='top')
                            # set a y axis label for the first column
                            ax[r,c].set_ylabel('# Employees', fontsize=14*font_mod)
                        if r==1:
                            ax[r,c].set_xlabel('Employee Time Cost ($ USD)', fontsize=14*font_mod)

                plt.tight_layout(pad=1.0)
                plt.savefig(plots_dir+"/"+key+".png")
                plt.close()  


        ############################################################################################################
        # GRAPH:
        ## Total Commute Cost Analysis
        key = 'tcca'
        title = "Total Commute Cost Analysis"
        short_title = title
        self.graph_list.append( {"GRAPH": key,
                                "TITLE": short_title,
                                "FILENAME": key+".png",
                                "PLOT-DESCRIPTION":  "This graph shows the total commute cost incurred by employees based upon mileage " + \
                                " and the average and high/conservative cost of employee time commuting to each office." + \
                                "The average cost is based upon the morning average and evening " + \
                                "average commute times, while the high/conservative cost is based upon the highest morning maximum and evening values for " + \
                                str(self.project.commute_days_per_week) + " days per week."
                                })
        if graph == "_all" or graph == key:
            employee_costs_to_office = {}

            for index, row in offices.iterrows():    
                office = row.to_frame().T
            
                # get the needed commute values
                values = commute_data.columns.to_list()
                
                mornings = ['m_morning_duration_in_traffic','t_morning_duration_in_traffic','w_morning_duration_in_traffic','h_morning_duration_in_traffic','f_morning_duration_in_traffic']
                evenings = ['m_evening_duration_in_traffic','t_evening_duration_in_traffic','w_evening_duration_in_traffic','h_evening_duration_in_traffic','f_evening_duration_in_traffic']
                
                cdpw = self.project.commute_days_per_week

                emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
                val_set = self.graphing.get_commute_values(emp_within, office, commute_data, values)
                
                

                # Calculate and insert the average morning and evening commute times directly into val_set
                val_set['Morning Average'] = val_set.loc[:, mornings].mean(axis=1)
                val_set['Evening Average'] = val_set.loc[:, evenings].mean(axis=1)

                # Calculate and insert the top 'cdpw' maximum morning and evening commute times
                # Note: Adjust the code below to calculate the averages of the top 'cdpw' as new columns directly
                val_set['Average Top CDPW Morning'] = val_set[mornings].apply(lambda row: row.nlargest(cdpw).mean(), axis=1)
                val_set['Average Top CDPW Evening'] = val_set[evenings].apply(lambda row: row.nlargest(cdpw).mean(), axis=1)

                # Calculate a per-minute cost based on "median_salary" and "hours_per_year"
                per_minute_cost = self.project.median_salary / (self.project.hours_per_year * 60)

                # Calculate and insert the average cost for the week directly into val_set
                val_set['Morning Average Cost'] = val_set['Morning Average'] * per_minute_cost
                val_set['Evening Average Cost'] = val_set['Evening Average'] * per_minute_cost

                # Calculate and insert the high/conservative cost for the week directly into val_set
                val_set['Morning High Cost'] = val_set['Average Top CDPW Morning'] * per_minute_cost
                val_set['Evening High Cost'] = val_set['Average Top CDPW Evening'] * per_minute_cost

                # Calculate a Total Average Time and Total High Time cost
                val_set['Total Average Time Cost'] = val_set['Morning Average Cost'] + val_set['Evening Average Cost']
                val_set['Total High Time Cost'] = val_set['Morning High Cost'] + val_set['Evening High Cost']

                # Calculate a Total Average Cost and Total High Cost
                val_set['Total Average Cost'] = val_set['Total Average Time Cost'] + val_set['commute_cost']
                val_set['Total High Cost'] = val_set['Total High Time Cost'] + val_set['commute_cost']
                
                # add the current val_set to the employee_costs_to_office dictionary
                employee_costs_to_office[row['address']] = val_set

            dvalues = ['Total Average Cost','Total High Cost']
            bins = []

            # now iterate through again to get bins
            for index, row in offices.iterrows():
                # create bins based on the max value of the Total Average Cost and Total High Cost data for each office, get the max value for bins
                binmax = 0
                for each in dvalues:
                    if max(employee_costs_to_office[row['address']][each]) > binmax:
                        binmax = max(employee_costs_to_office[row['address']][each])
                step = 5

            # round the binmax up to the nearest step
            bins = range(0, int(binmax + step - (binmax % step)), step)
            
            font_mod = 1.5
            
            # create histograms for the morning and evening average costs
            plt, ax = self.graphing.get_histogram(emp, office, commute_data, dvalues, 
                                                    suptitle="Total Employee Commute Costs per Day",cutoff_radius=self.project.commute_range_cut_off,
                                    x_label=str('\$ (USD)'), y_label='# Employees', bins=bins, rows=len(employee_costs_to_office.keys()), cols=2, 
                                    column_titles=["Average","High/Conservative"], cumulative_line=False, font_mod=font_mod, manual_plot=True, 
                                    sharey=True, sharex=True, override_values=employee_costs_to_office)
            
            # manually add histograms for each office option
            keys = list(employee_costs_to_office.keys())
            for r in range(len(keys)):
                for c in range(len(dvalues)):
                    ax[r,c].hist(employee_costs_to_office[keys[r]][dvalues[c]], bins=bins, alpha=0.5, edgecolor='#555555', linewidth=1, 
                                 zorder=2, align='mid', rwidth=0.8, label=dvalues, color=colors(r+1))
                    ax[r,c].tick_params(axis='both', which='major', labelsize=16)

                    # add a text box in the upper right corner with the stats
                    t = {'me' : 'Median: |${:,.2f}'.format(np.median(employee_costs_to_office[keys[r]][dvalues[c]])),
                        'av' : 'Average: |${:,.2f}'.format(np.mean(employee_costs_to_office[keys[r]][dvalues[c]])),
                        'mi' : 'Min: |${:,.2f}'.format(min(employee_costs_to_office[keys[r]][dvalues[c]])),
                        'ma' : 'Max: |${:,.2f}'.format(max(employee_costs_to_office[keys[r]][dvalues[c]])),
                        'to' : 'Total: |${:,.2f}'.format(sum(employee_costs_to_office[keys[r]][dvalues[c]])),
                        'co' : 'Count: |{}'.format(len(employee_costs_to_office[keys[r]][dvalues[c]]))
                        }
                    # get the longest string value
                    max_len = max(len(t['me']),len(t['av']),len(t['to']),len(t['mi']),len(t['ma']),len(t['co']))
                    # calculate additional space
                    for k in t:
                        t[k] = t[k].replace("|"," "*(max_len-len(t[k])))
                    # add spaces to make all the same length, replacing |
                    textstr = "Employee Commute \n Cost per Day: "
                    for k in t:
                        textstr += "\n" + t[k]
                    # these are matplotlib.patch.Patch properties
                    props = dict(boxstyle='round', facecolor='wheat', alpha=0.2)
                    # place a text box in upper right in axes coords,
                    ax[r,c].text(.95, .7, textstr, transform=ax[r,c].transAxes, fontsize=14,
                                verticalalignment='center', bbox=props, fontdict={'family': 'monospace'}, horizontalalignment='right')
                    
                    # add the address to the top left of the plot
                    if c==0:
                        ax[r,c].text(0.02, 0.98, keys[r], fontsize=10*font_mod, transform=ax[r,c].transAxes, ha='left', va='top')

                    # for the first column, add morning/evening text box the top left of the plot
                    if r==len(employee_costs_to_office.keys())-1:
                        ax[r,c].set_xlabel('Employee Total Cost ($ USD / Day)', fontsize=14*font_mod)                        
             
            plt.tight_layout(pad=1.0)
            plt.savefig(plots_dir+"/"+key+".png")
            plt.close() 

        ################################################################################ 
        # GRAPH: 
        ## Total Employee Commute Cost Differential Analysis
        key = 'teccda'
        title = "Total Employee Commute Cost Differential Analysis"
        short_title = title
        self.graph_list.append( {"GRAPH": key,
                                "TITLE": short_title,
                                "FILENAME": key+".png",
                                "PLOT-DESCRIPTION": "This graph displays the distribution of commute costs for employees within the " + \
                                                    "cutoff distance of the office options. Changes in per-employee commute costs are shown for each office " + \
                                                    "option relative to the existing office locaton.  This analysis inlcudes per mile costs (not including tolls, etc.) as well as  " + \
                                                    "average and conservative costs due to cash equivalent for time."
                                })
        
        if graph == "_all" or graph == key:
            # gather the data for the analysis
            base_costs, cost_values, average_diffs, conservative_diffs, withins, employee_costs_to_office, current_office, other_offices = \
                self.get_attrition_analysis(emp, offices, commute_data)


            # now we have a list of dataframes with the differentials, we eliminate all rows with 0 cost differential to prevent skewing the histogram
            # calculate the bin list based upon a the min (negative) and max (positive) values of the data     
            binmin = 0
            binmax = 0
            diffs = [average_diffs, conservative_diffs]
            for diff in diffs:
                for each in diff:
                    if min(each) < binmin:
                        binmin = min(each)
                    if max(each) > binmax:
                        binmax = max(each)
            step = 10 
            # round the binmin down to the nearest step, max up to the nearest step
            bins = range(int(binmin - (binmin % step)), int(binmax + step - (binmax % step)), step)
            dvalues = ['Total Average Cost','Total High Cost']
            
            plt, ax = self.graphing.get_histogram(emp, other_offices, cost_values, values=dvalues, suptitle="Total Employee Commute Cost Differential Analysis", cutoff_radius=self.project.commute_range_cut_off,
                                      x_label='\$ (USD) based on time and mileage', y_label='# Employees (log scale)',
                                      bins=bins, rows=len(other_offices), cols=2, column_titles=dvalues, 
                                      cumulative_line=False, font_mod=1.5, manual_plot=True,override_values=cost_values)
            
            # calculate the $ value for turnover due to cost
            median_salary = self.project.median_salary
            threshold = self.project.turnover_threshold_due_to_cost*median_salary
            daily_threshold = threshold/(self.project.commute_days_per_week*self.project.commute_weeks_per_year)
                   
            # manually add histograms for each office option
            for r in range(len(other_offices)):
                for c in range(2):
                    ax[r,c].hist(average_diffs[r], bins=bins, alpha=0.5, edgecolor='#555555', linewidth=1, zorder=2, align='mid', 
                            rwidth=0.8, label=other_offices['address'].values[r], color=colors(r+2), log=True)
                    ax[r,c].tick_params(axis='both', which='major', labelsize=16)
                    if c == 0:
                        ax[r,c].set_ylabel('# Employees (log scale)', fontsize=16)
                        # put office address top left of the plot
                        ax[r,c].text(0.03, 0.99, other_offices['address'].values[r], fontsize=16, transform=ax[r,c].transAxes, ha='left', va='top')
                    
                    if r == len(other_offices)-1:
                        ax[r,c].set_xlabel('Employee Total Cost Differential ($ USD)', fontsize=16)
                    ax[r,c].tick_params(axis='both', which='major', labelsize=16)
                    # draw a red box with alpha 0.1 over the plot from x=daily_threshold to x=binmax, and y=0 to y max
                    ax[r,c].fill_between([daily_threshold,binmax], 0, 10**3, color='red', alpha=0.1)
                    ax[r,c].fill_between([daily_threshold,binmax], 0, 10**3, color='red', alpha=0.1)
                    
                    above_threshold = 0
                    cost_impact = 0
                    # cycle through the average diffs and get a count of costs above the threshold
                    if c == 0:
                        for each in average_diffs[r]:
                            if each > daily_threshold:
                                above_threshold += 1                        
                    else:
                        for each in conservative_diffs[r]:
                            if each > daily_threshold:
                                above_threshold += 1

                    # cost impact is the # above threshold * employee replacement cost * probability of turnover
                    cost_impact = above_threshold * self.project.turnover_probability_time_cost * self.project.employee_replacement_cost
                    # add a text box with the count
                    t = {'dt' : 'Cost Threshold (\$/day): |${:,.2f}'.format(daily_threshold),
                         'co' : '# > Threshold (#): |{}'.format(above_threshold),
                         'ci' : 'Expected Cost (\$): |${:,.2f}'.format(cost_impact)                         
                        }
                    # get the longest string value
                    max_len = max(len(t['co']),len(t['ci']),len(t['dt']))
                    # calculate additional space
                    for k in t:
                        t[k] = t[k].replace("|"," "*(max_len-len(t[k])))
                        t[k] = t[k].replace("# > Threshold (#): ","# > Threshold (#):"*(max_len-len(t[k])))
                    # add spaces to make all the same length, replacing |
                    textstr = ""#Employees above \n Threshold: "
                    for k in t:
                        textstr += "\n" + t[k]
                    # these are matplotlib.patch.Patch properties
                    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
                    # place a text box in upper right in axes coords,
                    ax[r,c].text(.03, .85, textstr, transform=ax[r,c].transAxes, fontsize=14,
                                verticalalignment='center', bbox=props, fontdict={'family': 'monospace'}, horizontalalignment='left')
            
            plt.tight_layout(pad=1.0)
            plt.savefig(plots_dir+"/"+key+".png")
            plt.close()


        ################################################################################
        ### GRAPH SET: Local Analysis for Office X
        # iterate through offices, generate a graph for each office
        for index, row in offices.iterrows():    
            ################################################################################ 
            # GRAPH: 
            ## Traffic Regime Analysis
            key = 'tra'+str(index)
            title = "Traffic Regime Analysis for "+str(row['address'])
            short_title = title
            self.graph_list.append( {"GRAPH": key,
                                    "TITLE": short_title,
                                    "FILENAME": key+".png",
                                    "PLOT-DESCRIPTION": "This pie chart outlines the percentage of employees that are in each traffic regime for commute to " + \
                                    str(row['address']) + " for each day of the week."
                                    })
            
            if graph == "_all" or graph == key:
                
                office = row.to_frame().T
                
                # get the needed commute values
                values = commute_data.columns.to_list()
                # filter teh employees to only those within the cutoff distance
                emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
                val_set = self.graphing.get_commute_values(emp_within, office, commute_data, values)
                # restore val_set columns latitutde and longitude to origin_lat and origin_long
                val_set['origin_lat'] = val_set['latitude']
                val_set['origin_long'] = val_set['longitude']

                # for each employee, for each day's morning and evening commute, get the traffic regime
                # add the traffic regime to the val_set dataframe
                
                # lambda to call get_traffic_regime(distance, duration_in_traffic) using distance and duration_in_traffic columns
                val_set['m_morning_traffic_regime'] = val_set.apply(lambda row: self.get_traffic_regime(row['miles'], row['m_morning_duration_in_traffic']), axis=1)
                val_set['m_evening_traffic_regime'] = val_set.apply(lambda row: self.get_traffic_regime(row['miles'], row['m_evening_duration_in_traffic']), axis=1)
                val_set['t_morning_traffic_regime'] = val_set.apply(lambda row: self.get_traffic_regime(row['miles'], row['t_morning_duration_in_traffic']), axis=1)
                val_set['t_evening_traffic_regime'] = val_set.apply(lambda row: self.get_traffic_regime(row['miles'], row['t_evening_duration_in_traffic']), axis=1)
                val_set['w_morning_traffic_regime'] = val_set.apply(lambda row: self.get_traffic_regime(row['miles'], row['w_morning_duration_in_traffic']), axis=1)
                val_set['w_evening_traffic_regime'] = val_set.apply(lambda row: self.get_traffic_regime(row['miles'], row['w_evening_duration_in_traffic']), axis=1)
                val_set['h_morning_traffic_regime'] = val_set.apply(lambda row: self.get_traffic_regime(row['miles'], row['h_morning_duration_in_traffic']), axis=1)
                val_set['h_evening_traffic_regime'] = val_set.apply(lambda row: self.get_traffic_regime(row['miles'], row['h_evening_duration_in_traffic']), axis=1)
                val_set['f_morning_traffic_regime'] = val_set.apply(lambda row: self.get_traffic_regime(row['miles'], row['f_morning_duration_in_traffic']), axis=1)
                val_set['f_evening_traffic_regime'] = val_set.apply(lambda row: self.get_traffic_regime(row['miles'], row['f_evening_duration_in_traffic']), axis=1)

                # save val_set to file for debugging
            
                # get the counts of each traffic regime for each office
                traffic_graph_keys = ['m_morning_traffic_regime',
                                        't_morning_traffic_regime',
                                        'w_morning_traffic_regime',
                                        'h_morning_traffic_regime',
                                        'f_morning_traffic_regime',
                                        'm_evening_traffic_regime',
                                        't_evening_traffic_regime',
                                        'w_evening_traffic_regime',
                                        'h_evening_traffic_regime',
                                        'f_evening_traffic_regime']
                
                traffic_graphs_nice_names = {"m_morning_traffic_regime":"Monday Morning",
                                             "t_morning_traffic_regime":"Tuesday Morning",
                                             "w_morning_traffic_regime":"Wednesday Morning",
                                             "h_morning_traffic_regime":"Thursday Morning",
                                             "f_morning_traffic_regime":"Friday Morning",
                                             "m_evening_traffic_regime":"Monday Evening",
                                             "t_evening_traffic_regime":"Tuesday Evening",
                                             "w_evening_traffic_regime":"Wednesday Evening",
                                             "h_evening_traffic_regime":"Thursday Evening",
                                             "f_evening_traffic_regime":"Friday Evening"}
                
                traffic_regimes = {1:"Congested",2:"Bounded",3:"Free Flow"}

                # create a dictionary to hold the traffic regime counts for each day and morning/evening
                traffic_regime_counts = {}
                for k in traffic_graph_keys:
                    traffic_regime_counts[k] = val_set[k].value_counts().to_dict()
                    # sort the dictionary by key
                    traffic_regime_counts[k] = dict(sorted(traffic_regime_counts[k].items()))

                # traffic_regime_counts now holds: 
                # {'m_morning_traffic_regime': {1: 1539, 2: 424}, 't_morning_traffic_regime': {1: 1863, 2: 100}, 'w_morning_traffic_regime': {1: 1874, 2: 89}, 'h_morning_traffic_regime': {1: 1824, 2: 139}, 'f_morning_traffic_regime': {1: 1348, 2: 615}, 'm_evening_traffic_regime': {1: 1711, 2: 252}, 't_evening_traffic_regime': {1: 1826, 2: 137}, 'w_evening_traffic_regime': {1: 1888, 2: 75}, 'h_evening_traffic_regime': {1: 1878, 2: 85}, 'f_evening_traffic_regime': {1: 1704, 2: 259}}
                
                # create a values variable holding a list of the traffic regime counts for each day and morning/evening
                values = []
                for k in traffic_graph_keys:
                    values.append(list(traffic_regime_counts[k].values()))

                # iterate through traffic regime counts and create a list of labels for each day and morning/evening for regimes where counts are present
                labels = []
                for k in traffic_graph_keys:
                    label = []
                    for k in traffic_regime_counts[k].keys():
                        label.append(traffic_regimes[k])
                    labels.append(label)
                
                # iterate through the labels and get the colors for each traffic regime colors(i+1) will return a color for each regime
                colors_list = []
                for i in range(len(labels)):
                    color_list = []
                    for j in range(len(labels[i])):
                        color_list.append(colors(j+7))
                    colors_list.append(color_list)
                
                # create a titles variable holding a list of the traffic graph nice names
                titles = [traffic_graphs_nice_names[key] for key in traffic_graph_keys]
                rows = 2
                cols = 5
                # create a composite pie chart, five wide, with rows for morning and evening.  Each pie chart will display three values, Congested, Bounded, Free Flow
                plt, ax = self.graphing.get_piechart(values, titles=titles, suptitle=title, value_labels=labels, 
                                                    figsize=(21,7), manual_plot=False, font_mod=1, rows=rows, cols=cols, startangle=70, colors=colors_list)
                plt.tight_layout(pad=6, w_pad=8, h_pad=1)
                plt.subplots_adjust(top=0.85)
                # mauanlly adjust the font size of suptitle and plot titles
                plt.suptitle(title, fontsize=25, fontweight='bold')
                for i in range(rows):
                    for j in range(cols):
                        ax[i,j].title.set_fontsize(20)
                        # set bold
                        ax[i,j].title.set_fontweight('bold')
                
                plt.savefig(plots_dir+"/"+key+".png")
                plt.close()
                

        ################################################################################
        ### GRAPH SET: Local Analysis for Office X
        # iterate through offices, generate a graph for each office
        for index, row in offices.iterrows():    
            ################################################################################ 
            # GRAPH: 
            ## Worst Case Emissions Rate Heat Map Analysis
            key = 'wcerhma'+str(index)
            title = "Worst Case Emissions Rate Heat Map Analysis for "+str(row['address'])
            short_title = title
            self.graph_list.append( {"GRAPH": key,
                                    "TITLE": short_title,
                                    "FILENAME": key+".png",
                                    "PLOT-DESCRIPTION": "This heat map displays the representative worst case emissions rates for each office option. "
                                    })
            
            if graph == "_all" or graph == key:
                office = row.to_frame().T
                # get the needed commute values
                values = commute_data.columns.to_list()
                # filter teh employees to only those within the cutoff distance
                emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
                val_set = self.graphing.get_commute_values(emp_within, office, commute_data, values)
                # restore val_set columns latitutde and longitude to origin_lat and origin_long
                val_set['origin_lat'] = val_set['latitude']
                val_set['origin_long'] = val_set['longitude']

                traffic_graph_keys = ['m_morning_emissions',
                                        't_morning_emissions',
                                        'w_morning_emissions',
                                        'h_morning_emissions',
                                        'f_morning_emissions',
                                        'm_evening_emissions',
                                        't_evening_emissions',
                                        'w_evening_emissions',
                                        'h_evening_emissions',
                                        'f_evening_emissions']
                
                traffic_graphs_nice_names = {"m_morning_emissions":"Monday Morning",
                                             "t_morning_emissions":"Tuesday Morning",
                                             "w_morning_emissions":"Wednesday Morning",
                                             "h_morning_emissions":"Thursday Morning",
                                             "f_morning_emissions":"Friday Morning",
                                             "m_evening_emissions":"Monday Evening",
                                             "t_evening_emissions":"Tuesday Evening",
                                             "w_evening_emissions":"Wednesday Evening",
                                             "h_evening_emissions":"Thursday Evening",
                                             "f_evening_emissions":"Friday Evening"}
                
                # get the sum total emissions for each day and morning/evening
                emissions = []
                for k in traffic_graph_keys:
                    emissions.append(val_set[k].sum())

                # create a dictionary to hold the emissions for each day and morning/evening
                emissions_dict = {}
                for i in range(len(traffic_graph_keys)):
                    emissions_dict[traffic_graph_keys[i]] = emissions[i]
                

                plt, ax = self.graphing.get_heatmap(emp_within, office, val_set, "w_evening_emissions", title="Worst Case Emissions Rate (Wed. Evening)) \nfor "+str(row['address']), 
                                                value_label="CO2 Emissions in Traffic (kg/commute)", cutoff_distance=self.project.commute_range_cut_off, 
                                                commute_radius=self.project.commute_range_cut_off, alpha=0.4, levels=20, font_mod=1.5, 
                                                convex_hull=True, plot_points=True, imagery="Google", cmap='gist_heat_r')
                # add a text label to the bottom right of the plot with the total emissions for the plotted value
                t = {'em' : 'Total Emissions / Commute: {:.2f} kg'.format(emissions_dict['w_evening_emissions'])}    
                # add to plot
                textstr = t['em']                              
                # these are matplotlib.patch.Patch properties
                props = dict(boxstyle='round', facecolor='white', alpha=1)
                # place a text box in lower right in axes coords,
                ax.text(.985, .015, textstr, transform=ax.transAxes, fontsize=14,
                            verticalalignment='bottom', bbox=props, fontdict={'family': 'monospace'}, horizontalalignment='right')
                plt.savefig(plots_dir+"/"+key+".png")
                plt.close()
                
        #TODO : GRAPH THE EMISSIONS FOR EACH OFFICE


        ################################################################################ 
        # GRAPH: 
        ## Total Emissions Cost Differential Analysis
        key = 'tecdca'
        title = "Total Emissions Cost Differential Analysis"
        short_title = title
        self.graph_list.append( {"GRAPH": key,
                                "TITLE": short_title,
                                "FILENAME": key+".png",
                                "PLOT-DESCRIPTION": "This graph displays the differential cost associated with emissions based on the office options."
                                })
        
        if graph == "_all" or graph == key:
            # gather the data for the analysis
            base_costs, cost_values, average_diffs, conservative_diffs, withins, employee_costs_to_office, current_office, other_offices = \
                self.get_emissions_analysis(emp, offices, commute_data)

        
            # now we have a list of dataframes with the differentials, we eliminate all rows with 0 cost differential to prevent skewing the histogram
            # calculate the bin list based upon a the min (negative) and max (positive) values of the data     
            binmin = 0
            binmax = 0
            diffs = [average_diffs, conservative_diffs]
            for diff in diffs:
                for each in diff:
                    if min(each) < binmin:
                        binmin = min(each)
                    if max(each) > binmax:
                        binmax = max(each)
            step = 0.001
            # round the binmin down to the nearest step, max up to the nearest step
            bins = np.arange(binmin - (binmin % step), binmax + step - (binmax % step), step)

            dvalues = ['Total Average Cost','Total High Cost']
            
            plt, ax = self.graphing.get_histogram(emp, other_offices, cost_values, values=dvalues, suptitle=title, cutoff_radius=self.project.commute_range_cut_off,
                                      x_label='\$ (USD) per commute', y_label='# Employees (log scale)',
                                      bins=bins, rows=len(other_offices), cols=2, column_titles=dvalues, 
                                      cumulative_line=False, font_mod=1.5, manual_plot=True,override_values=cost_values)
            
                  
            # manually add histograms for each office option
            for r in range(len(other_offices)):
                for c in range(2):
                    ax[r,c].hist(average_diffs[r], bins=bins, alpha=0.5, edgecolor='#555555', linewidth=1, zorder=2, align='mid', 
                            rwidth=0.8, label=other_offices['address'].values[r], color=colors(r+2), log=True)
                    ax[r,c].tick_params(axis='both', which='major', labelsize=16)
                    if c == 0:
                        ax[r,c].set_ylabel('# Employees (log scale)', fontsize=16)
                        # put office address top left of the plot
                        ax[r,c].text(0.03, 0.99, other_offices['address'].values[r], fontsize=16, transform=ax[r,c].transAxes, ha='left', va='top')
                    
                    if r == len(other_offices)-1:
                        ax[r,c].set_xlabel('Cost of C02 Emissions (\$USD/commuting day)', fontsize=16)
                    ax[r,c].tick_params(axis='both', which='major', labelsize=16)
                    
                    # cost impact is the summation of the cost of emissions for all employees
                    cost_impact_avg = sum(average_diffs[r])
                    cost_impact_con = sum(conservative_diffs[r])
                    
                    # add a text box with the count
                    t = {'co' : 'Total Avg Emissions Cost Difference\n (\$/commuting day): ${:,.2f}'.format(cost_impact_avg),
                            'ci' : 'Total Conservative Cost Difference\n (\$/commuting day): ${:,.2f}'.format(cost_impact_con)                         
                            }
                    
                    textstr = t['co'] if c == 0 else t['ci']
                    # these are matplotlib.patch.Patch properties
                    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
                    # place a text box in upper right in axes coords,
                    ax[r,c].text(.03, .85, textstr, transform=ax[r,c].transAxes, fontsize=14,
                                verticalalignment='center', bbox=props, fontdict={'family': 'monospace'}, horizontalalignment='left')
                    
            plt.tight_layout(pad=1.0)
            plt.savefig(plots_dir+"/"+key+".png")
            plt.close()




        # write the graphs to graphs.json in the project plots directory
        # convert self.graphs_list to json
        with open(os.path.join(plots_dir, "graphs.json"), "w") as f:
            json.dump(self.graph_list, f)

        # update the analysis phase
        self.update_analysis_phase()
        return self.graph_list
    




    def generate_tables(self, table="_all"):
        """
        Generates and saves tabular representations of analyzed commute data.

        Based on the available commute data, this method generates tables such as the overall cost comparison analytics.

        Args:
            graph (str, optional): Specifies which table to generate. Use "_all" to generate all tables, or specify a 
            particular table's key. Defaults to "_all".

        Returns:
            list: A list of dictionaries, each containing details about the generated tables, including file paths and titles.
        """

        # generate the tables for the project
        # if the commute data isn't already in the project, load it
        if "commute_data.csv" in self.project.list_data_files():
            if self.project.data["commute_data.csv"] is None:
                # attempt to load the commute data
                if self.project.load_data_file("commute_data.csv"):
                    pass
                else:
                    print("Errors loading commute data from project.")
                    return False
            else:
                pass
        else:
            print("Commute data missing from project.")
            return False
        
        # create a list of dicts to map the tables to return to UI, they will be plotted in the order they are listed
        self.table_list = []
 
        ### generate the tables  ###
        tables_dir = os.path.join(self.project_directory, self.project.project_name, "tables")
        # if it doesn't exist, create it
        if not os.path.exists(tables_dir):
            os.makedirs(tables_dir)

        # get the baseline data
        emp = self.project.get_emp_gps()
        offices = self.project.get_office_gps()
        commute_data = self.project.get_commute_data()
        
        # helper function to save the table
        def save_table(t, key, tables_dir=tables_dir):
            # write the table to a file
            with open(os.path.join(tables_dir, key+".html"), "w") as f:
                f.write(t)

        ################################################################################
        ### TABLE SET: Office Addresses and Lat/Longs
        # iterate through offices and generate a table for each office
        for index, row in offices.iterrows():    
            ################################################################################ 
            # TABLE: 
            ## Location Information
            key = 'li'+str(index)
            title = "Location Information "+str(row['address'])
            short_title = title
            self.table_list.append( {"TABLE": key,
                                    "TITLE": short_title,
                                    "FILENAME": key+".html",
                                    "TABLE-DESCRIPTION": "This table displays the location information for office option " + \
                                    str(row['address']) + "."
                                    })
            
            if table == "_all" or table == key:
                office = row.to_frame().T
                # get the needed commute values

                # create a dataframe with the office address and lat/long
                location_data = pd.DataFrame()
                location_data['Office Address'] = [row['address']]
                location_data['Latitude'] = [row['latitude']]
                location_data['Longitude'] = [row['longitude']]
                # create a table
                t = location_data.to_html(index=False)
                # write the table to a file
                save_table(t, key)


        ################################################################################ 
        # TABLE: 
        ## Overal Cost Comparison Table
        key = 'occt'
        title = "Overall Cost Comparison Table"
        short_title = title
        self.table_list.append( {"TABLE": key,
                                "TITLE": short_title,
                                "FILENAME": key+".html",
                                "TABLE-DESCRIPTION": "This table displays the overall cost comparison for each office option."
                                })
        
        if table == "_all" or table == key:
            print("Generating table for: ", key, table)
            office = row.to_frame().T
            # gather the data for the analysis
            val_set, base_costs, cost_values, average_diffs, conservative_diffs, withins, employee_costs_to_office, current_office, other_offices = \
                self.get_attrition_analysis(emp, offices, commute_data)

            # commute related costs
                # pass
            
            # ####### employee attrition related costs
            # turnover threshold due to cost
            median_salary = self.project.median_salary
            threshold = self.project.turnover_threshold_due_to_cost*median_salary
            daily_threshold = threshold/(self.project.commute_days_per_week*self.project.commute_weeks_per_year)
            # turnover probability due to time cost
            turnover_probability_time_cost = self.project.turnover_probability_time_cost
            # employee replacement cost
            employee_replacement_cost = self.project.employee_replacement_cost




            # ######## emissions related costs

            # discount rate




            # create a dataframe with the office address and lat/long
            location_data = pd.DataFrame()
            location_data['Office Address'] = [row['address']]
            location_data['Latitude'] = [row['latitude']]
            location_data['Longitude'] = [row['longitude']]
            # create a table
            t = location_data.to_html(index=False)
            # write the table to a file
            save_table(t, key)











        # write the graphs to tables.json in the project tables directory
        # convert self.tables_list to json
        print(self.table_list)
        with open(os.path.join(tables_dir, "tables.json"), "w") as f:
            json.dump(self.table_list, f)
        
        # update the analysis phase
        self.update_analysis_phase()
        return self.table_list
        ################################################################################
    
    """
        # Constants
    annual_savings = 0.25  # in millions
    attrition_costs_year_1 = 0.05  # in millions
    annual_emissions_costs = 0.01  # in millions
    discount_rate = 0.05
    years = 5

    # Calculating NPV
    npv = 0

    # Year 1 cash flow (including attrition cost)
    year_1_net_savings = annual_savings - attrition_costs_year_1
    npv += year_1_net_savings / (1 + discount_rate)**1

    # Years 2-5 cash flows (including emissions costs)
    for year in range(2, years + 1):
        annual_net_savings = annual_savings - annual_emissions_costs
        npv += annual_net_savings / (1 + discount_rate)**year

    npv

    """
    def get_attrition_analysis(self, emp, offices, commute_data):
        # helper function to get a base cost dataframe
        def get_base_cost_df(emp, officeaddr):
            rows = []
            for index, row in emp.iterrows():
                cost = 0.0
                rows.append({'latitude':row['latitude'],'longitude':row['longitude'],'office':officeaddr,'cost':cost})
            #cost_df = pd.DataFrame(rows)
            return rows
        
        employee_costs_to_office = {}
        for index, row in offices.iterrows():    
            office = row.to_frame().T
            
            # get the needed commute values
            values = commute_data.columns.to_list()
            
            mornings = ['m_morning_duration_in_traffic','t_morning_duration_in_traffic','w_morning_duration_in_traffic','h_morning_duration_in_traffic','f_morning_duration_in_traffic']
            evenings = ['m_evening_duration_in_traffic','t_evening_duration_in_traffic','w_evening_duration_in_traffic','h_evening_duration_in_traffic','f_evening_duration_in_traffic']
            
            cdpw = self.project.commute_days_per_week

            emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
            val_set = self.graphing.get_commute_values(emp_within, office, commute_data, values)
            
            # restore val_set columns latitutde and longitude to origin_lat and origin_long
            val_set['origin_lat'] = val_set['latitude']
            val_set['origin_long'] = val_set['longitude']

            

            # Calculate and insert the average morning and evening commute times directly into val_set
            val_set['Morning Average'] = val_set.loc[:, mornings].mean(axis=1)
            val_set['Evening Average'] = val_set.loc[:, evenings].mean(axis=1)

            # Calculate and insert the top 'cdpw' maximum morning and evening commute times
            # Note: Adjust the code below to calculate the averages of the top 'cdpw' as new columns directly
            val_set['Average Top CDPW Morning'] = val_set[mornings].apply(lambda row: row.nlargest(cdpw).mean(), axis=1)
            val_set['Average Top CDPW Evening'] = val_set[evenings].apply(lambda row: row.nlargest(cdpw).mean(), axis=1)

            # Calculate a per-minute cost based on "median_salary" and "hours_per_year"
            per_minute_cost = self.project.median_salary / (self.project.hours_per_year * 60)

            # Calculate and insert the average cost for the week directly into val_set
            val_set['Morning Average Cost'] = val_set['Morning Average'] * per_minute_cost
            val_set['Evening Average Cost'] = val_set['Evening Average'] * per_minute_cost

            # Calculate and insert the high/conservative cost for the week directly into val_set
            val_set['Morning High Cost'] = val_set['Average Top CDPW Morning'] * per_minute_cost
            val_set['Evening High Cost'] = val_set['Average Top CDPW Evening'] * per_minute_cost

            # Calculate a Total Average Time and Total High Time cost
            val_set['Total Average Time Cost'] = val_set['Morning Average Cost'] + val_set['Evening Average Cost']
            val_set['Total High Time Cost'] = val_set['Morning High Cost'] + val_set['Evening High Cost']

            # Calculate a Total Average Cost and Total High Cost
            val_set['Total Average Cost'] = val_set['Total Average Time Cost'] + val_set['commute_cost']
            val_set['Total High Cost'] = val_set['Total High Time Cost'] + val_set['commute_cost']
            
            # add the current val_set to the employee_costs_to_office dictionary
            employee_costs_to_office[row['address']] = val_set
        
        # employees to analyze are within the cutoff distance for this office
        # for this analysis, we need to iterate through options
        current_office = offices.iloc[0].to_frame().T
        other_offices = offices.drop(0)
        cost_values = []
        withins = []
        commutes = 2*self.project.commute_days_per_week*self.project.commute_weeks_per_year
        
        # for each employee, calculate the commute cost to the current office, place a new dataframe with lat, long, office, and cost
        # if the employee is within the cutoff distance, if outside the cutoff distance, the cost is 0
        # start by looping through ALL employees and adding a row with the current office, and cost = 0
                

        base_costs = pd.DataFrame(get_base_cost_df(emp, current_office['address'].values[0]))
        # add columns for total average cost and total high cost
        base_costs['Total Average Cost'] = 0.0
        base_costs['Total High Cost'] = 0.0
        # now get emp_within for the current office, and update the relevant rows of base_costs with actual costs for those employees 
        # using the commute_cost column in the commute_data dataframe where the employee lat long matches the commute_data lat long and office address
        
        base_emp_within = self.graphing.filter_drive_distance(emp,current_office,self.project.commute_range_cut_off, commute_data=commute_data)

        for index, row in base_emp_within.iterrows():
            # set val_set from the employee_costs_to_office = {} dictionary
            val_set = employee_costs_to_office[current_office['address'].values[0]]
            # get the cost from the commute_data
            avg_cost = val_set[(val_set['origin_lat'] == row['latitude']) & (val_set['origin_long'] == row['longitude']) & (val_set['office_address'] == current_office['address'].values[0])]['Total Average Cost'].values[0]
            conservative_cost = val_set[(val_set['origin_lat'] == row['latitude']) & (val_set['origin_long'] == row['longitude']) & (val_set['office_address'] == current_office['address'].values[0])]['Total High Cost'].values[0]
            base_costs.loc[(base_costs['latitude'] == row['latitude']) & (base_costs['longitude'] == row['longitude']),'Total Average Cost'] = avg_cost
            base_costs.loc[(base_costs['latitude'] == row['latitude']) & (base_costs['longitude'] == row['longitude']),'Total High Cost'] = conservative_cost

        # now we have a dataframe with all employees, and the cost to the current office
    
        # now iterate through the other offices, get a base cost dataframe, and then update the relevant rows with actual costs, place in cost_values
        for index, row in other_offices.iterrows():
            office = row.to_frame().T
            tmp_costs = pd.DataFrame(get_base_cost_df(emp, office['address'].values[0]))
            # add columns for total average cost and total high cost
            tmp_costs['Total Average Cost'] = 0.0
            tmp_costs['Total High Cost'] = 0.0
            emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
            # we will use this later to get the differential for each employee, without the employees that aren't overlapping
            withins.append(emp_within)

            for index, row in emp_within.iterrows():
                # set val_set from the employee_costs_to_office = {} dictionary
                val_set = employee_costs_to_office[office['address'].values[0]]
                # get the cost from the commute_data
                avg_cost = val_set[(val_set['origin_lat'] == row['latitude']) & (val_set['origin_long'] == row['longitude']) & (val_set['office_address'] == office['address'].values[0])]['Total Average Cost'].values[0]
                conservative_cost = val_set[(val_set['origin_lat'] == row['latitude']) & (val_set['origin_long'] == row['longitude']) & (val_set['office_address'] == office['address'].values[0])]['Total High Cost'].values[0]
                tmp_costs.loc[(tmp_costs['latitude'] == row['latitude']) & (tmp_costs['longitude'] == row['longitude']),'Total Average Cost'] = avg_cost
                tmp_costs.loc[(tmp_costs['latitude'] == row['latitude']) & (tmp_costs['longitude'] == row['longitude']),'Total High Cost'] = conservative_cost
            
            cost_values.append(tmp_costs)
            
        # now we have a full list of costs for each employee to each office, we can get the differentials
        # create a list to hold the differential dataframes
        average_diffs = []
        conservative_diffs = []
        # for each cost dataframe, calculate the differential from the base_costs dataframe into a new dataframe
        for i in range(len(cost_values)):
            # get the differential
            average_diffs.append(cost_values[i]['Total Average Cost'] - base_costs['Total Average Cost'])
            conservative_diffs.append(cost_values[i]['Total High Cost'] - base_costs['Total High Cost'])

        return base_costs, cost_values, average_diffs, conservative_diffs, withins, employee_costs_to_office, current_office, other_offices
    




    def get_emissions_analysis(self, emp, offices, commute_data):
        # helper function to get a base cost dataframe
        def get_base_cost_df(emp, officeaddr):
            rows = []
            for index, row in emp.iterrows():
                cost = 0.0
                rows.append({'latitude':row['latitude'],'longitude':row['longitude'],'office':officeaddr,'cost':cost})
            #cost_df = pd.DataFrame(rows)
            return rows
        
        employee_costs_to_office = {}
        for index, row in offices.iterrows():    
            office = row.to_frame().T
            
            # get the needed commute values
            values = commute_data.columns.to_list()
            
            mornings = ['m_morning_emissions','t_morning_emissions','w_morning_emissions','h_morning_emissions','f_morning_emissions']
            evenings = ['m_evening_emissions','t_evening_emissions','w_evening_emissions','h_evening_emissions','f_evening_emissions']
            
            cdpw = self.project.commute_days_per_week

            emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
            val_set = self.graphing.get_commute_values(emp_within, office, commute_data, values)
            
            # restore val_set columns latitutde and longitude to origin_lat and origin_long
            val_set['origin_lat'] = val_set['latitude']
            val_set['origin_long'] = val_set['longitude']

            # Calculate and insert the average morning and evening commute times directly into val_set
            val_set['Morning Average'] = val_set.loc[:, mornings].mean(axis=1)
            val_set['Evening Average'] = val_set.loc[:, evenings].mean(axis=1)
            
            # Calculate and insert the top 'cdpw' maximum morning and evening commute times
            # Note: Adjust the code below to calculate the averages of the top 'cdpw' as new columns directly
            val_set['Average Top CDPW Morning'] = val_set[mornings].apply(lambda row: row.nlargest(cdpw).mean(), axis=1)
            val_set['Average Top CDPW Evening'] = val_set[evenings].apply(lambda row: row.nlargest(cdpw).mean(), axis=1)
            
            # emissions figure are in kg/commute. To get cost we need the CO2_credit_cost, which is $/metric ton
            per_kg_CO2_cost = self.project.CO2_credit_cost / 1000

            # Calculate and insert the average cost for the week directly into val_set
            val_set['Morning Average Cost'] = val_set['Morning Average'] * per_kg_CO2_cost
            val_set['Evening Average Cost'] = val_set['Evening Average'] * per_kg_CO2_cost
            
            # Calculate and insert the high/conservative cost for the week directly into val_set
            val_set['Morning High Cost'] = val_set['Average Top CDPW Morning'] * per_kg_CO2_cost
            val_set['Evening High Cost'] = val_set['Average Top CDPW Evening'] * per_kg_CO2_cost

            # Calculate a Total Average Time and Total High Time cost
            val_set['Total Average Cost'] = val_set['Morning Average Cost'] + val_set['Evening Average Cost']
            val_set['Total High Cost'] = val_set['Morning High Cost'] + val_set['Evening High Cost']
            
            # add the current val_set to the employee_costs_to_office dictionary
            employee_costs_to_office[row['address']] = val_set
        
        # employees to analyze are within the cutoff distance for this office
        # for this analysis, we need to iterate through options
        current_office = offices.iloc[0].to_frame().T
        other_offices = offices.drop(0)
        cost_values = []
        withins = []
        commutes = 2*self.project.commute_days_per_week*self.project.commute_weeks_per_year
        
        # for each employee, calculate the commute cost to the current office, place a new dataframe with lat, long, office, and cost
        # if the employee is within the cutoff distance, if outside the cutoff distance, the cost is 0
        # start by looping through ALL employees and adding a row with the current office, and cost = 0
                

        base_costs = pd.DataFrame(get_base_cost_df(emp, current_office['address'].values[0]))
        # add columns for total average cost and total high cost
        base_costs['Total Average Cost'] = 0.0
        base_costs['Total High Cost'] = 0.0
        # now get emp_within for the current office, and update the relevant rows of base_costs with actual costs for those employees 
        # using the commute_cost column in the commute_data dataframe where the employee lat long matches the commute_data lat long and office address
        
        base_emp_within = self.graphing.filter_drive_distance(emp,current_office,self.project.commute_range_cut_off, commute_data=commute_data)

        for index, row in base_emp_within.iterrows():
            # set val_set from the employee_costs_to_office = {} dictionary
            val_set = employee_costs_to_office[current_office['address'].values[0]]
            # get the cost from the commute_data
            avg_cost = val_set[(val_set['origin_lat'] == row['latitude']) & (val_set['origin_long'] == row['longitude']) & (val_set['office_address'] == current_office['address'].values[0])]['Total Average Cost'].values[0]
            conservative_cost = val_set[(val_set['origin_lat'] == row['latitude']) & (val_set['origin_long'] == row['longitude']) & (val_set['office_address'] == current_office['address'].values[0])]['Total High Cost'].values[0]
            base_costs.loc[(base_costs['latitude'] == row['latitude']) & (base_costs['longitude'] == row['longitude']),'Total Average Cost'] = avg_cost
            base_costs.loc[(base_costs['latitude'] == row['latitude']) & (base_costs['longitude'] == row['longitude']),'Total High Cost'] = conservative_cost

        # now we have a dataframe with all employees, and the cost to the current office
    
        # now iterate through the other offices, get a base cost dataframe, and then update the relevant rows with actual costs, place in cost_values
        for index, row in other_offices.iterrows():
            office = row.to_frame().T
            tmp_costs = pd.DataFrame(get_base_cost_df(emp, office['address'].values[0]))
            # add columns for total average cost and total high cost
            tmp_costs['Total Average Cost'] = 0.0
            tmp_costs['Total High Cost'] = 0.0
            emp_within = self.graphing.filter_drive_distance(emp,office,self.project.commute_range_cut_off, commute_data=commute_data)
            # we will use this later to get the differential for each employee, without the employees that aren't overlapping
            withins.append(emp_within)

            for index, row in emp_within.iterrows():
                # set val_set from the employee_costs_to_office = {} dictionary
                val_set = employee_costs_to_office[office['address'].values[0]]
                # get the cost from the commute_data
                avg_cost = val_set[(val_set['origin_lat'] == row['latitude']) & (val_set['origin_long'] == row['longitude']) & (val_set['office_address'] == office['address'].values[0])]['Total Average Cost'].values[0]
                conservative_cost = val_set[(val_set['origin_lat'] == row['latitude']) & (val_set['origin_long'] == row['longitude']) & (val_set['office_address'] == office['address'].values[0])]['Total High Cost'].values[0]
                tmp_costs.loc[(tmp_costs['latitude'] == row['latitude']) & (tmp_costs['longitude'] == row['longitude']),'Total Average Cost'] = avg_cost
                tmp_costs.loc[(tmp_costs['latitude'] == row['latitude']) & (tmp_costs['longitude'] == row['longitude']),'Total High Cost'] = conservative_cost
            
            cost_values.append(tmp_costs)
            
        # now we have a full list of costs for each employee to each office, we can get the differentials
        # create a list to hold the differential dataframes
        average_diffs = []
        conservative_diffs = []
        # for each cost dataframe, calculate the differential from the base_costs dataframe into a new dataframe
        for i in range(len(cost_values)):
            # get the differential
            average_diffs.append(cost_values[i]['Total Average Cost'] - base_costs['Total Average Cost'])
            conservative_diffs.append(cost_values[i]['Total High Cost'] - base_costs['Total High Cost'])

        return base_costs, cost_values, average_diffs, conservative_diffs, withins, employee_costs_to_office, current_office, other_offices