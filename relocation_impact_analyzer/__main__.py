"""
Relocation Impact Analyzer Entry Point

Author: Victor Foulk
License: MIT License
Date: 2024-03-15
Version: 0.0.1 Pre-Alpha

This script acts as the primary entry point for the Relocation Impact Analyzer, a tool designed to aid a customer in assessing the impacts of office 
relocation. It interprets command-line arguments to initiate various components of the analysis, including data conversion, commute analysis, 
and graphical representation of the findings.  Aside from instantiating the UI which runs forever, the script can be used to execute specific
actions on a given project, such as converting addresses to GPS coordinates, generating commute data, or producing graphical outputs.  The latter cases
are longer running operations that are run in a separate thread to allow the UI to continue to be responsive, hence this command line entry point.

Usage:
    python -m relocation_impact_analyzer: with no arguments, instantiates a websever on localhost to serve UI
    python -m relocation_impact_analyzer <project_name> <action> [<action_specific_argument>]: 
            executes the specified action on the given project

Actions:
    do_convert_addresses_latlong: Converts project addresses into latitude-longitude coordinates.
    do_gen_commute: Generates commute data for employees based on current and potential new office locations.
    do_gen_graphs: Produces graphical representations of the analysis outcomes.

Each action is designed to progress the analysis, with some safeguards in place to ensure the necessary data is available before proceeding.
"""

import sys, os
from relocation_impact_analyzer.ui import *

def main():
    """Main function that parses command line arguments and initiates appropriate actions."""
    # get the command line arguments
    args = sys.argv
    
    # Process command-line arguments and direct flow based on input
    if len(args) == 1:
        # No arguments provided, default to running the UI (run is defined in ui.py)
        run()
        return 0
    elif len(args) == 2:
        # Insufficient arguments for any operation
        print("Too few arguments provided.")
        return 1
    elif len(args) > 4:
        # More arguments provided than expected
        print("Too many arguments provided.")
        return 1
    
    # Expected arguments: project name and action
    proj, action = args[1], args[2]
    a = Analyzer()  # Initialize the analyzer object
    
    # Verify the specified project exists
    if proj not in a.list_projects():
        print("Project does not exist.")
        return 1
    
    # Load the specified project
    a.load_project(proj)
    
    # Perform the specified action
    # Actions include converting addresses, generating commute data, and creating graphs
    # Each action checks for required data files and logs operations accordingly
    if action == "do_convert_addresses_latlong":
        # Convert addresses to GPS coordinates
        return handle_convert_addresses_latlong(a, proj, args)
    elif action == "do_gen_commute":
        # Generate commute data
        return handle_gen_commute(a, proj, args)
    elif action == "do_gen_graphs":
        # Generate graphs based on commute data
        return handle_gen_graphs(a, proj, args)
    elif action == "do_gen_tables":
        # Generate tables based on commute data
        return handle_gen_tables(a, proj, args)
    else:
        # Action specified is not recognized
        print("Invalid action.")
        return 1

# Helper functions for each action to keep the main function clean
def handle_convert_addresses_latlong(analyzer, project, args):
    """
    Converts addresses to GPS coordinates for the specified project.

    This function verifies the availability of necessary data files for address conversion, performs the conversion,
    and logs the operation. If successful, it cleans up by removing the log file.  The log file is used by the UI to know 
    that a long-running process is underway.

    Parameters:
    - analyzer: The main analysis object which provides functionalities for conversion.
    - project: A string specifying the project name, used to locate project-specific data files and logging.
    - args: Command-line arguments passed to the script, not used in this function but included for consistency.

    Returns:
    - int: 0 if the conversion was successful, 1 if required data files are missing.
    
    Side effects:
    - Creates a log file in the project directory during processing, which is removed upon completion.
    """
    # verify the data files are available
    if "employee_addresses.csv" not in analyzer.project.list_data_files() or "office_addresses.csv" not in analyzer.project.list_data_files():
        print("Data files not available.")
        return 1
    else:
        # logfile will be a csv in the project directory
        logfile = analyzer.project.project_directory + "/" + project + "/address_conversion_log.csv"
        analyzer.convert_addresses_to_gps(log_csv=logfile)
        # remove the logfile if it exists
        if os.path.exists(logfile):
            os.remove(logfile)
        return 0

def handle_gen_commute(analyzer, project, args):
    """
    Generates commute data based on the project's available information.

    This function checks for the necessary data files and uses the analyzer to generate commute data,
    including calculating commute costs and emissions. Operations are logged, and the log file is cleaned
    up after completion.  The log file is used by the UI to know that a long-running process is underway.

    Parameters:
    - analyzer: The main analysis object equipped with methods to generate commute data.
    - project: A string indicating the project name for data file location and logging.
    - args: Command-line arguments passed to the script, not directly used in this function.

    Returns:
    - int: 0 if commute data generation is successful, 1 if required data files are not found.
    
    Side effects:
    - Produces a log file in the project directory, which is removed after the function completes.
    """    
    # verify the data files are available
    if (analyzer.project.use_gps_fuzzing and "gps_fuzz.csv" not in analyzer.project.list_data_files()) or "office_gps.csv" not in analyzer.project.list_data_files():
        print("Data files not available.")
        return 1
    else:
        logfile = analyzer.project.project_directory + "/" + project + "/commute_gen_log.csv"
        analyzer.get_commute_data(log_csv=logfile)
        analyzer.get_commute_cost()
        analyzer.get_commute_emissions()
        # remove the logfile if it exists
        if os.path.exists(logfile):
            os.remove(logfile)
        return 0

def handle_gen_graphs(analyzer, project, args):
    """
    Generates graphical representations of the commute data for a given project.

    Verifies the availability of the 'commute_data.csv' file before proceeding. It then
    generates graphs based on this data, with the option to regenerate a specific graph if
    an additional argument is provided. Operations are logged, and the log file is removed
    upon completion. The log file is used by the UI to know that a long-running process is underway.

    Parameters:
    - analyzer: The analysis object containing graph generation capabilities.
    - project: The project name, used for locating data files and determining the log file path.
    - args: Command-line arguments, where the fourth argument (if present) specifies a single graph to regenerate.

    Returns:
    - int: 0 if graphs were successfully generated, 1 if the 'commute_data.csv' file is missing.
    
    Side effects:
    - Generates a log file in the project directory during the operation, which is removed afterwards.
    """
    # verify the data files are available
    if "commute_data.csv" not in analyzer.project.list_data_files():
        print("Data files not available.")
        return 1
    else:
        logfile = analyzer.project.project_directory + "/" + project + "/graph_gen_log.csv"
        # if there's an argument after do_gen_graphs, it is a call to regenerate just one graph
        if len(args) == 4:
            analyzer.generate_graphs(args[3])
        else:
            analyzer.generate_graphs()
        # remove the logfile if it exists
        if os.path.exists(logfile):
            os.remove(logfile)
        return 0

def handle_gen_tables(analyzer, project, args):
    """
    Generates tabular representations of the commute data for a given project.

    Verifies the availability of the 'commute_data.csv' file before proceeding. It then
    generates tables based on this data, with the option to regenerate a specific table if
    an additional argument is provided. Operations are logged, and the log file is removed
    upon completion. The log file is used by the UI to know that a long-running process is underway.

    Parameters:
    - analyzer: The analysis object containing graph generation capabilities.
    - project: The project name, used for locating data files and determining the log file path.
    - args: Command-line arguments, where the fourth argument (if present) specifies a single table to regenerate.

    Returns:
    - int: 0 if graphs were successfully generated, 1 if the 'commute_data.csv' file is missing.
    
    Side effects:
    - Generates a log file in the project directory during the operation, which is removed afterwards.
    """
    # verify the data files are available
    if "commute_data.csv" not in analyzer.project.list_data_files():
        print("Data files not available.")
        return 1
    else:
        logfile = analyzer.project.project_directory + "/" + project + "/table_gen_log.csv"
        # if there's an argument after do_gen_graphs, it is a call to regenerate just one graph
        if len(args) == 4:
            analyzer.generate_tables(args[3])
        else:
            analyzer.generate_tables()
        # remove the logfile if it exists
        if os.path.exists(logfile):
            os.remove(logfile)
        return 0
    
if __name__ == "__main__":
    sys.exit(main())

