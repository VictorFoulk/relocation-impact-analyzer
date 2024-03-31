"""
Project class for the Relocation Impact Analysis Tool

The Project class is responsible for managing all aspects of a project within the relocation impact analysis tool. 
It encapsulates functionalities related to project setup, data management, and configuration handling. This includes 
creating new projects, loading and saving project configurations, managing data files (CSV format) for various aspects 
of the project (e.g., employee and office addresses, GPS coordinates), and ensuring the data integrity and structure 
conforms to expected formats. The class also provides utilities for accessing and manipulating project-specific data, 
supporting the broader analysis tasks by maintaining a central repository of the project's data and state.

Author: Victor Foulk
License: MIT License
Date: 2024-03-15
Version: 0.0.1 Pre-Alpha
"""

import os
import json
import pandas as pd

 

class Project:
    # Class representing an analysis project.
    def __init__(self, proj=None, project_directory=None, default_configuration=True):
        """
        Initializes a new Project instance with optional project name, directory, and configuration settings.

        Args:
            proj (str, optional): The name of the project to initialize or load. If None, a project is not immediately loaded or created.
            project_directory (str, optional): The filesystem path to the directory where project files are stored. If None, defaults to a 'projects' directory within the current working directory.
            default_configuration (bool, optional): Indicates whether the project should be initialized with default configuration settings. Defaults to True.

        This constructor sets up the initial environment for managing a project, including setting default data file definitions and project attributes. 
        If a project name is provided, it attempts to load the project from the specified directory.
        """

        # set the default configuration flag
        self.default_configuration = default_configuration
        # set the data file definitions
        self.data_file_definitions = {
            "employee_addresses.csv": ["address"],
            "employee_gps.csv": ["address","latitude", "longitude"],
            "gps_fuzz.csv": ["latitude", "longitude"],
            "office_addresses.csv": ["address"],
            "office_gps.csv": ["address","latitude", "longitude"],
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
        }
        
        self.project_file_attributes = {
                        "project_name": "",
                        "sources": "",
                        "destinations": "",
                        "use_gps_fuzzing": True,
                        "gps_fuzz_factor": 0.1,
                        "project_directory": os.path.join(os.getcwd(), "projects"), #current working director / projects
                        "commute_range_cut_off": 50,
                        "commute_range_cut_off_unit": "miles",
                        "commute_days_per_week": 2,
                        "commute_weeks_per_year": 50,
                        "CO2_per_mile": 0.404,
                        "traffic_regime_1": 0.0,
                        "traffic_regime_2": 33.554,
                        "traffic_regime_3": 55.923,
                        "traffic_regime_1_coeff": 0.7,
                        "traffic_regime_2_coeff": 0.53,
                        "traffic_regime_3_coeff": 1.25,
                        "CO2_credit_cost": round((0.92+0.68+0.6)/3,2),
                        "mileage_rate": 0.67,
                        "turnover_threshold_due_to_cost": 0.03,
                        "turnover_probability_time_cost": 0.25,
                        "employee_replacement_cost": 60000,
                        "median_salary": 114068,
                        "hours_per_year": 2080,
                        "morning_commute_start": "08:00",
                        "evening_commute_start": "17:00",
                        "GMAPS_API_KEY": ""
        }
        
        # initialize a default starting point for project directories
        self.default_project_directory = os.path.join(os.path.dirname(__file__), "projects")

        # set all project variables to None for initialization
        self.flush_project()

        # if a project directory is provided, use it. Otherwise, use the default project directory
        if project_directory:
            self.project_directory = project_directory
            # remember the provided project directory as the default
            self.default_project_directory = project_directory
        else:
            self.project_directory = self.default_project_directory

        # if the project directory does not exist, create it
        if not os.path.exists(self.project_directory):
            os.mkdir(self.project_directory)

        # if a project name is provided, attempt to load the project configuration json from the project directory
        if proj:
            self.load_project(proj)
        else:
            return None

    def flush_project(self):
        """
        Resets the project's attributes and data containers to their initial state.

        This method is used to reinitialize the project's attributes, effectively clearing any existing project data in memory. 
        It is useful when starting a new project or clearing the current project's state without loading another project.
        """

        # set all project variables except name to None (useful for reinitializing the project object)
        # if the project default flag is set, set the attributes to the default values, else, None
        for attr in self.project_file_attributes:
            setattr(self, attr, None if not self.default_configuration else self.project_file_attributes[attr])
        # (re)create the data container
        self.data = {}
        # self.data contains dictionaries, keys are the type of data, and the values are the dataframes
        for file in self.data_file_definitions:
            self.data[file] = None
        # restore the project directory to the default
        self.project_directory = self.default_project_directory

    def load_project(self, proj):
        """
        Attempts to load an existing project by name from the project directory.

        Args:
            proj (str): The name of the project to load.

        If the specified project exists, this method loads the project's configuration and data from the corresponding 'project.json' 
        file within the project's directory. If the project or configuration file does not exist, it prompts to create a new project template.
        """

        self.project_name = proj
        # check to see if a folder with the project name exists
        if os.path.exists(os.path.join(self.project_directory, proj)):
            self.project_file = os.path.join(self.project_directory, proj, "project.json")
            # check to see if a project file exists
            if os.path.exists(self.project_file):
                self.load_project_file()
            else:
                # project folder exists, but no project file. Create a new project file to correct error
                print("Project "+ proj + " configuration file not found. Creating a blank project template.")
                self.save_project()
                return None
        else:
            print("Project "+ proj + " not found. Creating new project.")
            self.new_project(proj)
            return None
    
    def load_project_file(self):
        """
        Loads the project's configuration from its 'project.json' file into the project attributes.

        This method reads the project configuration file and updates the project's attributes according to the file's contents. 
        It is called internally when a project is loaded.
        """
        # load the project file json into the project object
        try:
            with open(self.project_file, "r") as f:
                self.project = json.load(f)
            # for all attributes in the json, set project attributes to the value in the json
            for attr in self.project:
                setattr(self, attr, self.project[attr])

        except:
            print("Error loading project file.")
            return None
    
    def new_project(self, proj):
        """
        Creates a new project directory and initializes a blank project configuration.

        Args:
            proj (str): The name of the new project to create.

        This method sets up a new project by creating the necessary directory structure and initializing a blank project 
        configuration file if the specified project does not already exist.
        """
        # clear the current project
        self.flush_project()
        # create a new project with the provided name
        if not os.path.exists(os.path.join(self.project_directory, proj)):
            os.mkdir(os.path.join(self.project_directory, proj))
            # also create a subdirectory for the project plots called plots
            #os.mkdir(os.path.join(self.project_directory, proj, "plots"))
            self.project_name = proj
            self.project_file = os.path.join(self.project_directory, proj, "project.json")
            self.save_project()
        else:
            print("Project "+ proj + " already exists.")
            return None 
        
    def save_project(self):
        """
        Saves the current project's configuration and data files to disk.

        This method serializes the project's attributes to a 'project.json' configuration file and saves any loaded 
        data frames to their respective CSV files within the project's directory. It ensures that the project's current 
        state is persisted to disk.
        """
        # make sure there's a project here, must have a name at a minimum... if project name is None, return None
        if not self.project_name:
            return None
        # make sure the project directory exists
        if not os.path.exists(os.path.join(self.project_directory, self.project_name)):
            os.mkdir(os.path.join(self.project_directory, self.project_name)) 
        # project file 
        self.project_file = os.path.join(self.project_directory, self.project_name, "project.json")
       
        # save the attributes of the project class to the project file JSON
        self.project = {}
        for attr in self.project_file_attributes:
            self.project[attr] = getattr(self, attr)
        with open(self.project_file, "w") as f:
            json.dump(self.project, f, indent=4)
        # save all project data files that exist in the data dictionary
        for file in self.data:
            if self.data[file] is not None:
                self.save_data_file(file)
        return self.project_name
    
    def delete_project(self):
        """
        Saves the current project's configuration and data files to disk.

        This method serializes the project's attributes to a 'project.json' configuration file and saves any loaded 
        data frames to their respective CSV files within the project's directory. It ensures that the project's current 
        state is persisted to disk.
        """

        proj=self.project_name
        if not proj:
            print("No project to delete.")
            return None
        # delete the project directory and all files within it
        if os.path.exists(os.path.join(self.project_directory, proj)):
            # remove the contents of the project directory, recursively, to include any directories and their content
            for root, dirs, files in os.walk(os.path.join(self.project_directory, proj), topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            #for file in os.listdir(os.path.join(self.project_directory, proj)):
            #    os.remove(os.path.join(self.project_directory, proj, file))
            # remove the project directory
            os.rmdir(os.path.join(self.project_directory, proj))
            self.flush_project()
        else:
            print("Project "+ proj + " not found.")
            return None
    
    def list_data_files(self):
        """
        Lists all data files present in the current project's directory.

        Scans the project directory for CSV files, which are considered data files associated with the project, and returns a list of these filenames.

        Returns:
            list: A list of filenames (str) of data files found in the project directory.
        """

        # get all data files in the project directory with .csv extension
        data_files = []
        for file in os.listdir(os.path.join(self.project_directory, self.project_name)):
            if file.endswith(".csv"):
                data_files.append(file)
        return data_files
     
    def save_data_file(self, file_name):
        """
        Saves the specified data frame to a CSV file within the project directory.

        Args:
            file_name (str): The name of the data file to save.

        Validates the format of the data frame against expected column definitions and writes the data frame to a CSV file. 
        If validation fails, the method returns False.

        Returns:
            bool or str: The filename if the data file is successfully saved; otherwise, False if the validation fails.
        """

        # save a new or update existing data file in the project directory from a pandas dataframe, return file name if successful
        # check data format of the dataframe to ensure the columns contain the correct data
        if self.validate_dataframe(file_name):
            self.data[file_name].to_csv(os.path.join(self.project_directory, self.project_name, file_name), index=False, sep=";")
            return file_name
        else:
            return False
        
    
    def delete_data_file(self, file_name):
        """
        Deletes a specified data file from the project directory.

        Args:
            file_name (str): The name of the data file to delete.

        Checks if the file exists within the list of project data files and deletes it if found. Also clears the 
        corresponding data frame from the project's data container.

        Returns:
            bool: True if the file was successfully deleted; False otherwise.
        """

        # delete a data file in the project directory
        if file_name in self.list_data_files():
            os.remove(os.path.join(self.project_directory, self.project_name, file_name))
            try:
                if self.data[file_name]:
                    self.data[file_name]=None
            except:
                pass
            return True
        else:
            return False
        
    def load_data_file(self, file_name):
        """
        Loads data from a specified CSV file into a pandas DataFrame and stores it in the project's data container.

        Args:
            file_name (str): The name of the data file to load.

        Validates the presence of the data file in the project directory and attempts to load its contents into a DataFrame, which is then stored within the project's data container under the same filename.

        Returns:
            bool: True if the data file is successfully loaded; False otherwise.
        """

        # load a data file from the project directory into a pandas dataframe
        if file_name in self.list_data_files():
            data = pd.read_csv(os.path.join(self.project_directory, self.project_name, file_name), sep=";")
            # validate that the data file
            if self.validate_data_file(file_name, data):
                self.data[file_name] = data
                return True
        else:
            return False
        
    def validate_data_file(self, file_name, data):
        """
        Validates the structure of a DataFrame against expected column definitions for a specific data file.

        Args:
            file_name (str): The name of the data file for which the DataFrame is being validated.

        Ensures that the DataFrame associated with the file name contains all required columns.

        Returns:
            bool: True if the DataFrame's columns match the expected definitions; False otherwise.
        """

        # validate a data file in the project directory
        if file_name in self.list_data_files():
            # vefify that the data file has the correct columns, though it may have extra
            if set(data.columns).issuperset(self.data_file_definitions[file_name]):
                return True
            else:
                return False
        else:
            return False
    
    def validate_dataframe(self, file_name):
        """
        Validates the structure of a DataFrame against expected column definitions for a specific data file.

        Args:
            file_name (str): The name of the data file for which the DataFrame is being validated.

        Ensures that the DataFrame associated with the file name contains all required columns.

        Returns:
            bool: True if the DataFrame's columns match the expected definitions; False otherwise.
        """

        # validate a dataframe to ensure it has the correct columns
        if set(self.data[file_name].columns).issuperset(self.data_file_definitions[file_name]):
            return True
        else:
            return False
    
    def start_dataframe(self, file_name):
        """
        Initializes a new DataFrame with the correct columns for a specified data file type.

        Args:
            file_name (str): The name of the data file type to initialize a DataFrame for.

        The method uses the data file definitions to create an empty DataFrame with the appropriate columns for the specified file type.

        Returns:
            bool: True if the DataFrame is successfully initialized; False if the file_name does not match any known data file definition.
        """
        
        # start a new dataframe with the correct columns
        if file_name in self.data_file_definitions:
            self.data[file_name] = pd.DataFrame(columns=self.data_file_definitions[file_name])
            return True
        else:
            return False
    
    def get_employee_addresses(self):
        """
        Retrieves the DataFrame containing requested addresses for the project.

        If the requested addresses data has not been loaded into the project's data container, this method attempts 
        to load it from the corresponding CSV file within the project directory.

        Returns:
            pd.DataFrame: The DataFrame containing addresses, or an empty DataFrame if the data file does not exist or cannot be loaded.
        """

        # get the employee addresses dataframe, load it if necessary
        if self.data["employee_addresses.csv"] is None:
            self.load_data_file("employee_addresses.csv")
        return self.data["employee_addresses.csv"]
    
    def get_emp_gps(self):
        """
        Retrieves the DataFrame containing requested lat/long data for the project.

        If the requested addresses data has not been loaded into the project's data container, this method attempts 
        to load it from the corresponding CSV file within the project directory.

        Returns:
            pd.DataFrame: The DataFrame containing employee lat/longs, or an empty DataFrame if the data file does not exist or cannot be loaded.
        
        An abstraction for employee gps data, if use gps fuzzing is enabled, return the fuzzed data, else return the original.
        """

        if self.use_gps_fuzzing:
            return self.get_gps_fuzz()
        else:
            return self.get_employee_gps()
        
    def get_employee_gps(self):
        """
        Retrieves the DataFrame containing requested lat/long data for the project.

        If the requested data has not been loaded into the project's data container, this method attempts 
        to load it from the corresponding CSV file within the project directory.

        Returns:
            pd.DataFrame: The DataFrame containing employee lat/longs, or an empty DataFrame if the data file does not exist or cannot be loaded.
        
        """
        # get the employee gps dataframe, load it if necessary
        if self.data["employee_gps.csv"] is None:
            self.load_data_file("employee_gps.csv")
        return self.data["employee_gps.csv"]
    
    def get_gps_fuzz(self):
        """
        Retrieves the DataFrame containing requested lat/long data for the project.

        If the requested data has not been loaded into the project's data container, this method attempts 
        to load it from the corresponding CSV file within the project directory.

        Returns:
            pd.DataFrame: The DataFrame containing fuzzed employee lat/longs, or an empty DataFrame if the data file does not exist or cannot be loaded.
        
        """
        
        # get the gps fuzz dataframe, load it if necessary
        if self.data["gps_fuzz.csv"] is None:
            self.load_data_file("gps_fuzz.csv")
        return self.data["gps_fuzz.csv"]
    
    def get_office_addresses(self):
        """
        Retrieves the DataFrame containing requested addresses for the project.

        If the requested addresses data has not been loaded into the project's data container, this method attempts 
        to load it from the corresponding CSV file within the project directory.

        Returns:
            pd.DataFrame: The DataFrame containing addresses, or an empty DataFrame if the data file does not exist or cannot be loaded.
        """
        
        # get the office addresses dataframe, load it if necessary
        if self.data["office_addresses.csv"] is None:
            self.load_data_file("office_addresses.csv")
        return self.data["office_addresses.csv"]
    
    def get_office_gps(self):
        """
        Retrieves the DataFrame containing requested lat/long data for the project.

        If the requested data has not been loaded into the project's data container, this method attempts 
        to load it from the corresponding CSV file within the project directory.

        Returns:
            pd.DataFrame: The DataFrame containing office lat/longs, or an empty DataFrame if the data file does not exist or cannot be loaded.
        
        """
        # get the office gps dataframe, load it if necessary
        if self.data["office_gps.csv"] is None:
            self.load_data_file("office_gps.csv")
        return self.data["office_gps.csv"]
    
    def get_commute_data(self):
        """
        Retrieves the DataFrame containing requested commute_data table for the project.

        If the requested data has not been loaded into the project's data container, this method attempts 
        to load it from the corresponding CSV file within the project directory.

        Returns:
            pd.DataFrame: The DataFrame containing all lat/long source/destination combinations and the resulting
            calculations and analyses, or an empty DataFrame if the data file does not exist or cannot be loaded.
        
        """
        
        # get the commute data dataframe, load it if necessary
        if self.data["commute_data.csv"] is None:
            self.load_data_file("commute_data.csv")
        return self.data["commute_data.csv"]
    