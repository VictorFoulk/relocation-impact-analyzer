"""
User Interface for the Relocation Impact Analyzer

The HTTP_UI class implements a simple HTTP server to serve as the user interface for the Relocation Impact Analyzer. 
It handles HTTP GET and POST requests, providing a web-based interface for creating, managing, and analyzing projects. 
This interface allows users to upload data files, view project status, and initiate analysis tasks directly from their web browsers.

This server is built using Python's http.server module and is designed for ease of use and demonstration purposes only. 
It is not secure for public or production deployment without additional security measures. Features include project creation and deletion, 
data file management, analysis phase tracking, and status updates on long-running tasks such as address geocoding or commute data generation.

Author: Victor Foulk
License: MIT License
Date: 2024-03-15
Version: 0.0.1 Pre-Alpha
"""

# Creates a simple test UI for the relocation impact analyzer
# NOTE: This is not intended for a production deployment as this webserver 
# is not hardened or secure for a production environment

# create a webserver on port 8080

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qsl
from relocation_impact_analyzer.analyzer import *
import re
import pandas as pd
from requests_toolbelt.multipart.decoder import MultipartDecoder
from io import StringIO
import traceback
import os, json

class HTTP_UI(BaseHTTPRequestHandler):
    # create an __init__ method then call parent __init__ method
    def __init__(self, *args, **kwargs):
        """
        Initializes the HTTP_UI instance with necessary attributes and calls the superclass initializer.

        This constructor sets up variables for managing template variable replacements, status messages, 
        and error messages for dynamic content generation in response to HTTP requests.
        """

        self.var_queue = {}
        self.status_message = ""
        self.status_error = ""
        super(HTTP_UI, self).__init__(*args, **kwargs)
        
        

    def do_GET(self):
        """
        Handles GET requests to the HTTP server.

        This method serves various content based on the requested URL path, including static assets like images and the main index.html page. 
        It dynamically generates HTML content by replacing template variables based on the current state of projects and analysis. 
        Also handles special queries for project status updates and analysis phase information.
        """

        # placeholder for adding javscript to the html
        javascriptSTR = ""
        # if there is an attribute last_post_action, then we will add a variable to the javascript to display a message
        if hasattr(self, 'last_post_action'):
            javascriptSTR += "\n last_post_action='" + self.last_post_action + "';"
            delattr(self, 'last_post_action')
        
        parsed_path = urlparse(self.path)
        # get subfolder from path
        subfolders = parsed_path.path.split('/')

        # the images folder is in the base relocation_impact_analyzer folder
        # the plots folder is in the project folder under project_name/plots
        query = dict(parse_qsl(parsed_path.query))
        # evaluate the path, if path is an image file, read and send the image
        if parsed_path.path.endswith('.png') or parsed_path.path.endswith('.ico'): # only image files we'll response to
            # if the path is ico, add "images/" to the path (this handles the favicon.ico use case)
            self.send_response(200)
            self.end_headers()
            if parsed_path.path.endswith('.ico'):
                parsed_path = urlparse('/images' + parsed_path.path)
            
            base = 'relocation_impact_analyzer'
            # plot use case will have a URL like http://localhost:8080/project_name/plots/plot_name.png
            # check length of subfolders, if 3, then verify the second subfoler is plots, and change the
            # base directory to the project directory
            if len(subfolders) == 4: # plot use case
                # create an analyzer object and list the projects
                a = Analyzer()
                projects = a.list_projects()
                if subfolders[1] in projects and subfolders[2] == "plots":
                    a.load_project(subfolders[1])
                    base = a.project.project_directory + "/" 
            with open(base + parsed_path.path, 'rb') as file:
                self.wfile.write(file.read())
            # we are done with this request, return
            return
        
        # create an analyzer object and list the projects
        a = Analyzer()
        projects = a.list_projects()
        if "project" in query:
            if os.path.exists(a.project.project_directory + "/" + query['project'] + "/commute_gen_log.csv"):
                javascriptSTR += "\n commute_gen_log_exists=true;"
            if os.path.exists(a.project.project_directory + "/" + query['project'] + "/address_conversion_log.csv"):
                javascriptSTR += "\n address_conversion_log_exists=true;"            
            if os.path.exists(a.project.project_directory + "/" + query['project'] + "/graph_gen_log.csv"):
                javascriptSTR += "\n graph_gen_log_exists=true;"
            if os.path.exists(a.project.project_directory + "/" + query['project'] + "/table_gen_log.csv"):
                javascriptSTR += "\n table_gen_log_exists=true;"


        if "project" in query and "get_status" in query:
            # if the query string directs getting the status, then we will send the status message and error
            # verify the project exists
            if query['project'] not in projects:
                self.self.status_error += "Error getting status for project " + query['project'] + ". Project does not exist. "
            else:
                a.load_project(query['project'])
                # if get_status is do_gen_commute, then we will send the status of the commute generation
                if query['get_status'] == "do_gen_commute":
                    # if there is an commute_gen_log.csv file, then we send in progress, otherwise we send complete
                    if os.path.exists(a.project.project_directory + "/" + query['project'] + "/commute_gen_log.csv"):
                        self.status_message += "Commute generation in progress."
                    else:
                        self.status_message += "Commute generation complete."
                # if get_status is do_convert_addresses_latlong, then we will send the status of the address conversion
                elif query['get_status'] == "do_convert_addresses_latlong":
                    # if there is an address_conversion_log.csv file, then we send in progress, otherwise we send complete
                    if os.path.exists(a.project.project_directory + "/" + query['project'] + "/address_conversion_log.csv"):
                        self.status_message += "Address conversion in progress."
                    else:
                        self.status_message += "Address conversion complete."
                # if get_status is do_gen_graphs, then we will send the status of the graph generation
                elif query['get_status'] == "do_gen_graphs":
                    # if there is an graph_gen_log.csv file, then we send in progress, otherwise we send complete
                    if os.path.exists(a.project.project_directory + "/" + query['project'] + "/graph_gen_log.csv"):
                        self.status_message += "Graph generation in progress."
                    else:
                        self.status_message += "Graph generation complete."
                # if get_status is do_gen_tables, then we will send the status of the table generation
                elif query['get_status'] == "do_gen_tables":
                    # if there is an table_gen_log.csv file, then we send in progress, otherwise we send complete
                    if os.path.exists(a.project.project_directory + "/" + query['project'] + "/table_gen_log.csv"):
                        self.status_message += "Table generation in progress."
                    else:
                        self.status_message += "Table generation complete."
                self.send_response(200)
                self.end_headers()
            self.wfile.write(bytes(self.status_message + self.status_error,'utf-8'))
            return
        if "project" in query and "get_aphase" in query:
            # if the query string directs getting the analysis phase, then we will send the analysis phase
            # verify the project exists
            if query['project'] not in projects:
                self.status_error += "Error getting analysis phase for project " + query['project'] + ". Project does not exist. "
            else:
                a.load_project(query['project'])
                self.send_response(200)
                self.end_headers()
            self.wfile.write(bytes(str(a.analysis_phase),'utf-8'))
            return
        # otherwise, we're going to send the index.html file
        # read index.html file as a template string
        st = ""
        with open('relocation_impact_analyzer/index.html', 'r') as file:
            st = file.read() #.encode('utf-8')

        # if the query string directs creating a project, then we will create the project, then display the project's data
        if 'create_project' in query:
            # verify the project doesn't already exist, error if it does
            if query['create_project'] in projects:
                self.status_error += "Error creating project " + query['create_project'] + ". Project already exists. "
            else:
                a.create_project(query['create_project'])
                a.load_project(query['create_project'])
                self.load_project_vars(a.project)
                projects = a.list_projects()
                javascriptSTR += "\n pname='" + a.project.project_name + "';"
                self.queue_template_var("{{PROJECT_PHASE}}",str(a.analysis_phase))
                javascriptSTR += "\n aphase=" + str(a.analysis_phase) + ";"
                self.status_message += "Project '" + query['create_project'] + "' created. "
        
        # else if the query string directs flushing the project, then we will flush the project, then display the project's data
        elif 'flush_project' in query:
            if query['flush_project'] not in projects:
                self.status_error += "Error flushing project " + query['flush_project'] + ". Project does not exist. "
            else:
                a.load_project(query['flush_project'])
                a.project.flush_project()
                a.project.save_project()
                a.project.project_name = query['flush_project']
                self.load_project_vars(a.project,)
                projects = a.list_projects()
                javascriptSTR += "\n pname='" + a.project.project_name + "';"
                self.queue_template_var("{{PROJECT_PHASE}}",str(a.analysis_phase))
                javascriptSTR += "\n aphase=" + str(a.analysis_phase) + ";"
                self.status_message += "Project '" + query['flush_project'] + "' flushed. "

        # else if the query string directs deleting the project, then we will delete the project
        elif 'delete_project' in query:
            if query['delete_project'] not in projects:
                self.status_error += "Error deleting project " + query['delete_project'] + ". Project does not exist. "
            else:
                a.load_project(query['delete_project'])
                a.project.delete_project()
                projects = a.list_projects()                
                self.status_message += "Project '" + query['delete_project'] + "' deleted. "
        # elif the query string directs viewing a data file, we will read that file and send it as a file
        elif 'view_data_file' in query:
            if query['project'] not in projects:
                self.status_error += "Error viewing data file " + query['view_data_file'] + ". Project does not exist. "
            else:
                a.load_project(query['project'])
                if query['view_data_file'] not in a.project.list_data_files():
                    self.status_error += "Error viewing data file " + query['view_data_file'] + ". File does not exist. "
                else:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/csv')
                    self.send_header('Content-Disposition', 'attachment; filename="' + query['view_data_file'] + '"')
                    self.end_headers()
                    a.project.load_data_file(query['view_data_file'])
                    self.wfile.write(bytes(a.project.data[query['view_data_file']].to_csv(index=False, sep=';'), 'utf-8'))
                    return
        # if the query string designates a project, then we will verify that project exists, then display the project's data, otherise error
        elif 'project' in query and query['project'] in projects:
            a.load_project(query['project'])
            if "load_project" in query:
                self.status_message += "Project '" + query['project'] + "' loaded. "
            self.load_project_vars(a.project)
            javascriptSTR += "\n pname='" + a.project.project_name + "';"
            self.queue_template_var("{{PROJECT_PHASE}}",str(a.analysis_phase))
            javascriptSTR += "\n aphase=" + str(a.analysis_phase) + ";"
        elif 'project' in query and query['project'] not in projects:
            self.status_error += "Error loading project " + query['project'] + ". Project does not exist. "

        # if a project is loaded, we pass the current_project name to formatting
        current_project = a.project.project_name if a.project else ""

        # if there's no message, then we will display the default message
        if self.status_message == "" and self.status_error == "":
            self.status_message += "System Ready. "

        # update template string with the status messages and remaining vars

        # if not os.path.exists(a.env_file) then this is the first run, add a javascript var to track
        javascriptSTR += "\n first_run=" + str(1 if not os.path.exists(a.env_file) else 0) + ";"
        frw = "Looks like our first run, welcome! <br> Verify/save the system settings to continue. <br/>Then, load or create a new project." if not os.path.exists(a.env_file) else ""
        
        # if the employee_addresses and office_address files are missing, we tell the user they're required
        uuw = ""
        if current_project != "":
            if "employee_addresses.csv" not in a.project.list_data_files():
                uuw += "employee " 
            if "office_addresses.csv" not in a.project.list_data_files():
                uuw += "office " if uuw == "" else "and office "
            uuw = "<br/>" if uuw =="" else "<span class='notice'>User must upload " + uuw + "addresses to continue.</span><br/>"
        self.queue_template_var("{{FILE_UPLOADS_NEEDED}}", uuw)
        # replace the template string with the query parameters
    

        self.queue_template_var("{{FIRST_RUN_WARNING}}", frw)
        self.queue_template_var("{{EXISTING_PROJECT_LIST}}", self.format_option_list(projects, current_project) )
        self.queue_template_var("{{STATUS_MESSAGE}}", self.status_message)
        self.queue_template_var("{{STATUS_ERROR}}", self.status_error)
        self.queue_template_var("{{PROJECT_VARIABLES}}", javascriptSTR)
        self.queue_template_var("{{DEFAULT_PROJECTS_DIRECTORY}}", a.project_directory)
        self.queue_template_var("{{GLOBAL_GMAPS_API_KEY}}", a.gAPI_key)

        # if there's a project loaded, let's populate any data files
        if current_project != "":
            self.queue_template_var("{{DATA_FILES}}", self.format_option_list(a.project.list_data_files()))
            self.queue_template_var("{{GRAPHS}}", self.get_graphs_template(a.project),priority=True)
            self.queue_template_var("{{TABLES}}", self.get_tables_template(a.project),priority=True)

        self.send_response(200)
        self.end_headers()
        
        st = self.do_replace_template_vars(st)
        # strip any remaining template variables surrounded by {{ and }} by regex match, with no spaces
        st = re.sub(r'{{.*?}}', '', st)

        self.wfile.write(bytes(st,'utf-8')) 
        
    def do_POST(self):
        """
        Handles POST requests to the HTTP server, processing form data submitted by the user.

        This method supports updating system and project-specific variables, uploading data files, initiating analysis tasks, and more. 
        After processing the POST data, it redirects to the GET handler to update the user interface accordingly.
        """

        # handle the posted data then pass off to the get method
        
        # if there are no posted data, then we will return the get method, otherwise we will process the posted data
        # look for the update_project_vars=true in the post data, and if present, we will update the project variables
        content_length = int(self.headers['Content-Length'])
        ctype = self.headers.get('Content-Type')
        post_data = self.rfile.read(content_length).decode('utf-8')
            
        if 'multipart/form-data' in ctype:
            post_data = MultipartDecoder(bytes(post_data,'utf-8'),ctype)
            post_data = self.parse_multipart(post_data)
            
        else:
            post_data = dict(parse_qsl(post_data))
        
        # first and foremost, if we're asked to kill the server, do so
        if "do_stop_server" in post_data:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(bytes("Server Stopped.",'utf-8'))
            exit(1)
            

        a = Analyzer()
        # if we are directed to save system vars, then we will save the system vars
        if 'update_system_vars' in post_data:
            g = "" if "global_gmaps_api_key" not in post_data else post_data['global_gmaps_api_key']
            d = "" if "default_projects_directory" not in post_data else post_data['default_projects_directory']
            a.save_env(gAPI_key=g, project_directory=d)
            self.status_message += "System-wide variables updated."
        # update the project variables use case
        elif 'update_project_vars' in post_data and post_data['update_project_vars'] == "true":
            # verify project exists
            if post_data['project_name_ro'] not in a.list_projects():
                self.status_error += "Error updating project " + post_data['project_name'] + ". Project does not exist. "
            else:
                a.project.project_name = "" if "project_name_ro" not in post_data else post_data['project_name_ro']
                a.project.project_directory = "" if "project_directory" not in post_data else post_data['project_directory']
                a.project.sources = "" if "sources" not in post_data else post_data['sources']
                a.project.destinations = "" if "destinations" not in post_data else post_data['destinations']
                a.project.use_gps_fuzzing = True if 'use_gps_fuzzing' in post_data and post_data['use_gps_fuzzing'] == 'on' else False
                a.project.gps_fuzz_factor = 0 if "gps_fuzz_factor" not in post_data else float(post_data['gps_fuzz_factor'])
                a.project.address_to_gps_fuzz = "" if "address_to_gps_fuzz" not in post_data else post_data['address_to_gps_fuzz']
                a.project.GMAPS_API_KEY = "" if "GMAPS_API_KEY" not in post_data else post_data['GMAPS_API_KEY']
                a.project.commute_range_cut_off = 0 if "commute_range_cut_off" not in post_data else float(post_data['commute_range_cut_off'])
                a.project.commute_range_cut_off_unit = "" if "commute_range_cut_off_unit" not in post_data else post_data['commute_range_cut_off_unit']
                a.project.commute_days_per_week = 0 if "commute_days_per_week" not in post_data else int(post_data['commute_days_per_week'])
                a.project.commute_weeks_per_year = 0 if "commute_weeks_per_year" not in post_data else int(post_data['commute_weeks_per_year'])
                a.project.morning_commute_start = "" if "morning_commute_start" not in post_data else post_data['morning_commute_start']
                a.project.evening_commute_start = "" if "evening_commute_start" not in post_data else post_data['evening_commute_start']
                a.project.mileage_rate = 0 if "mileage_rate" not in post_data else float(post_data['mileage_rate'])
                a.project.CO2_per_mile = 0 if "CO2_per_mile" not in post_data else float(post_data['CO2_per_mile'])
                a.project.traffic_regime_1 = 0  # Note: This is read-only and always 0 as per your example
                a.project.traffic_regime_2 = 0 if "traffic_regime_2" not in post_data else float(post_data['traffic_regime_2'])
                a.project.traffic_regime_3 = 0 if "traffic_regime_3" not in post_data else float(post_data['traffic_regime_3'])
                a.project.traffic_regime_1_coeff = 0 if "traffic_regime_1_coeff" not in post_data else float(post_data['traffic_regime_1_coeff'])
                a.project.traffic_regime_2_coeff = 0 if "traffic_regime_2_coeff" not in post_data else float(post_data['traffic_regime_2_coeff'])
                a.project.traffic_regime_3_coeff = 0 if "traffic_regime_3_coeff" not in post_data else float(post_data['traffic_regime_3_coeff'])
                a.project.CO2_credit_cost = 0 if "CO2_credit_cost" not in post_data else float(post_data['CO2_credit_cost'])
                a.project.median_salary = 0 if "median_salary" not in post_data else float(post_data['median_salary'])
                a.project.turnover_threshold_due_to_cost = 0 if "turnover_threshold_cost" not in post_data else float(post_data['turnover_threshold_cost'])
                a.project.turnover_probability_time_cost = 0 if "turnover_probability_time_cost" not in post_data else float(post_data['turnover_probability_time_cost'])
                a.project.employee_replacement_cost = 0 if "employee_replacement_cost" not in post_data else float(post_data['employee_replacement_cost'])

                a.project.save_project()
                self.status_message += "Project '" + post_data['project_name_ro'] + "' updated. "

        # if there are data files to load, then we will load the data files
        elif "do_upload_data_file" in post_data:
            
            # verify project exists
            if post_data['project_name'] not in a.list_projects():
                self.status_error += "Error loading data file for project " + post_data['project_name'] + ". Project does not exist. "
            # verify the posted file is a .csv file
            elif not post_data['data_file']['filename'].endswith('.csv'):
                self.status_error += "Error loading data file for project " + post_data['project_name'] + ". File is not a .csv file. "
            else:
                # all good, load the project and the data file
                a.load_project(post_data['project_name'])
                data_file_map = {
                    "employee_addresses":"employee_addresses.csv",
                    "employee_gps":"employee_gps.csv",
                    "employee_gps_fuzzed":"gps_fuzz.csv",
                    "office_addresses":"office_addresses.csv",
                    "office_gps":"office_gps.csv",
                    "commute_data":"commute_data.csv" 
                }
                # the data in the posted file is a CSV, try load it into a dataframe, except error if it fails
                try:
                    df = pd.read_csv(StringIO(post_data['data_file']['Content-Data']),sep=";")
                    #attach the dataframe to the project to validate
                    #setattr(a.project, data_file_map[post_data['data_file_type']], df)
                    a.project.data[data_file_map[post_data['data_file_type']]] = df
                    # validate the dataframe
                    if a.project.validate_dataframe(data_file_map[post_data['data_file_type']]):
                        # save the project
                        a.project.save_project()
                        # update the status message
                        self.status_message += "Data file '" + data_file_map[post_data['data_file_type']] + "' loaded from " + post_data['data_file']['filename'] +". "
                    else:
                        self.status_error += "Error loading  " + post_data['data_file']['filename'] + ". <br/> File is not a valid .csv file. "
                except Exception as e:
                    # print exception to the console
                    print(type(e).__name__, e) 
                    print(traceback.format_exc())
                    self.status_error += "Error loading " + post_data['data_file']['filename'] + ".<br/> File is not a valid .csv file. "
                
        # if there are data files to delete, then we will delete the data files
        elif "delete_data_file" in post_data:
            # verify project exists
            if post_data['project_name'] not in a.list_projects():
                self.status_error += "Error deleting data file " + post_data['delete_data_file'] + " for project " + post_data['project_name'] + ". Project does not exist. "
            a.load_project(post_data['project_name'])
            if post_data['delete_data_file'] not in a.project.list_data_files():
                print(post_data['delete_data_file'])
                self.status_error += "Error deleting data file " + post_data['delete_data_file'] + " for project " + post_data['project_name'] + ". File does not exist. "
            else:
                a.project.delete_data_file(post_data['delete_data_file'])
                a.project.save_project()
                self.status_message += "Data file '" + post_data['delete_data_file'] + "' deleted. "

        # if the request is to convert data files to GPS, then we will convert the data files to GPS
        elif "do_convert_addresses_latlong" in post_data:
            # verify project exists
            if post_data['project_name'] not in a.list_projects():
                self.status_error += "Error converting addresses to lat/long for project " + post_data['project_name'] + ". Project does not exist. "
            else:
                a.load_project(post_data['project_name'])
                if "employee_addresses.csv" not in a.project.list_data_files() or "office_addresses.csv" not in a.project.list_data_files():
                    self.status_error += "Error converting addresses to lat/long for project " + post_data['project_name'] + ". Lat/Long data files are missing. "
                else:
                     # create a background process to generate the commute data
                    # first get the filesystem location of the relocate_impact_analyzer module
                    # then run the __main__ module with the project and action as arguments
                    proj = a.project.project_name
                    action = "do_convert_addresses_latlong"
                    # call system call to run asynchonous process
                    r = os.system("python3 -m relocation_impact_analyzer " + proj + " " + action + " &")
                    if r != 0:
                        self.status_error += "Error converting lat/longs data for project " + post_data['project_name'] + ". "
                    else:
                        self.status_message += "Lat/Long conversion started for project '" + post_data['project_name'] + "'. "
                    # set a flag for the get method to know what just happend
                    self.last_post_action = "do_convert_addresses_latlong"
                    # make sure the logfile exists, if not, create it before proceding
                    if not os.path.exists(a.project.project_directory + "/" + post_data['project_name'] + "/address_conversion_log.csv"):
                        with open(a.project.project_directory + "/" + post_data['project_name'] + "/address_conversion_log.csv", 'w') as file:
                            file.write("Address Conversion Log\n")
                    """
                    a.convert_addresses_to_gps()
                    a.project.save_project()
                    self.status_message += "Addresses converted to GPS for project '" + post_data['project_name'] + "'. "
                    """
        # if the request is to do_fuzzing, then we will do the fuzzing
        elif "do_fuzzing" in post_data:
            # verify project exists
            if post_data['project_name'] not in a.list_projects():
                self.status_error += "Error fuzzing lat/long for project " + post_data['project_name'] + ". Project does not exist. "
            else:
                a.load_project(post_data['project_name'])
                if "employee_addresses.csv" not in a.project.list_data_files() or "office_addresses.csv" not in a.project.list_data_files():
                    self.status_error += "Error fuzzing lat/long for project " + post_data['project_name'] + ". Lat/Long data files are missing. "
                elif a.project.use_gps_fuzzing == False:
                    self.status_error += "Error fuzzing lat/long for project " + post_data['project_name'] + ". lat/long fuzzing is disabled for project. "
                else:
                    a.fuzz_employee_gps()
                    a.project.save_project()
                    self.status_message += "Lat/Long fuzzed for project '" + post_data['project_name'] + "'. "

        # if the request is to generate commute data, then we will generate the commute data
        elif "do_gen_commute" in post_data:
            # verify project exists
            if post_data['project_name'] not in a.list_projects():
                self.status_error += "Error generating commute data for project " + post_data['project_name'] + ". Project does not exist. "
            else:
                a.load_project(post_data['project_name'])
                if (a.project.use_gps_fuzzing and "gps_fuzz.csv" not in a.project.list_data_files()) or "office_gps.csv" not in a.project.list_data_files():
                    self.status_error += "Error generating commute data for project " + post_data['project_name'] + ". Needed data files are missing. "
                else:
                    # create a background process to generate the commute data
                    # first get the filesystem location of the relocate_impact_analyzer module
                    # then run the __main__ module with the project and action as arguments
                    proj = a.project.project_name
                    action = "do_gen_commute"
                    # call system call to run asynchonous process THIS IS NOT IDEAL, BUT IT WORKS... this can't make it to production
                    r = os.system("python3 -m relocation_impact_analyzer " + proj + " " + action + " &")
                    if r != 0:
                        self.status_error += "Error generating commute data for project " + post_data['project_name'] + ". "
                    else:
                        self.status_message += "Commute data generation started for project '" + post_data['project_name'] + "'. "
                    # set a flag for the get method to know what just happend
                    self.last_post_action = "do_gen_commute"
                    # make sure the logfile exists, if not, create it before proceding
                    if not os.path.exists(a.project.project_directory + "/" + post_data['project_name'] + "/commute_gen_log.csv"):
                        with open(a.project.project_directory + "/" + post_data['project_name'] + "/commute_gen_log.csv", 'w') as file:
                            file.write("Commute Generation Log\n")

                    """a.get_commute_data()
                    a.get_commute_cost()
                    a.get_commute_emissions()
                    a.project.save_project()
                    self.status_message += "Commute data generated for project '" + post_data['project_name'] + "'. "
                    """

        # if the request is to generate commute data, then we will generate the commute data
        elif "do_update_calcs" in post_data:
            # verify project exists
            if post_data['project_name'] not in a.list_projects():
                self.status_error += "Error generating commute data for project " + post_data['project_name'] + ". Project does not exist. "
            else:
                a.load_project(post_data['project_name'])
                if "commute_data.csv" not in a.project.list_data_files():
                    self.status_error += "Error updating commute data for project " + post_data['project_name'] + ". Needed data files are missing. "
                else:
                    a.get_commute_cost()
                    a.get_commute_emissions()
                    a.project.save_project()
                    self.last_post_action = "do_update_calcs"
                    self.status_message += "Commute data updated for project '" + post_data['project_name'] + "'. "

        # if the request is to generate graph data, then we will generate the graph data
        elif "do_gen_graphs" in post_data or "regen_graph" in post_data:
            # verify project exists
            if post_data['project_name'] not in a.list_projects():
                self.status_error += "Error generating graph data for project " + post_data['project_name'] + ". Project does not exist. "
            else:
                a.load_project(post_data['project_name'])
                if "commute_data.csv" not in a.project.list_data_files():
                    self.status_error += "Error generating graph data for project " + post_data['project_name'] + ". Needed data files are missing. "
                else:
                    #a.generate_graphs()
                    # create a background process to generate the graph data
                    # first get the filesystem location of the relocate_impact_analyzer module
                    # then run the __main__ module with the project and action as arguments
                    proj = post_data['project_name']
                    action = "do_gen_graphs"
                    if "regen_graph" in post_data:
                        action += " " + post_data['regen_graph']
                    # call system call to run asynchonous process
                    r = os.system("python3 -m relocation_impact_analyzer " + proj + " " + action + " &")
                    if r != 0:
                        self.status_error += "Error generating graph data for project " + post_data['project_name'] + ". "
                    else:
                        self.status_message += "Graph data generation started for project '" + post_data['project_name'] + "'. "
                    # set a flag for the get method to know what just happend
                    self.last_post_action = "do_gen_graphs"
                    # make sure the logfile exists, if not, create it before proceding
                    if not os.path.exists(a.project.project_directory + "/" + post_data['project_name'] + "/graph_gen_log.csv"):
                        with open(a.project.project_directory + "/" + post_data['project_name'] + "/graph_gen_log.csv", 'w') as file:
                            file.write("Graph Generation Log\n")                          

        # if the request is to generate table data, then we will generate the table data
        elif "do_gen_tables" in post_data or "regen_table" in post_data:
            # verify project exists
            if post_data['project_name'] not in a.list_projects():
                self.status_error += "Error generating table data for project " + post_data['project_name'] + ". Project does not exist. "
            else:
                a.load_project(post_data['project_name'])
                if "commute_data.csv" not in a.project.list_data_files():
                    self.status_error += "Error generating table data for project " + post_data['project_name'] + ". Needed data files are missing. "
                else:
                    #a.generate_graphs()
                    # create a background process to generate the table data
                    # first get the filesystem location of the relocate_impact_analyzer module
                    # then run the __main__ module with the project and action as arguments
                    proj = post_data['project_name']
                    action = "do_gen_tables"
                    if "regen_table" in post_data:
                        action += " " + post_data['regen_table']
                    # call system call to run asynchonous process
                    r = os.system("python3 -m relocation_impact_analyzer " + proj + " " + action + " &")
                    if r != 0:
                        self.status_error += "Error generating table data for project " + post_data['project_name'] + ". "
                    else:
                        self.status_message += "Table data generation started for project '" + post_data['project_name'] + "'. "
                    # set a flag for the get method to know what just happend
                    self.last_post_action = "do_gen_tables"
                    # make sure the logfile exists, if not, create it before proceding
                    if not os.path.exists(a.project.project_directory + "/" + post_data['project_name'] + "/table_gen_log.csv"):
                        with open(a.project.project_directory + "/" + post_data['project_name'] + "/table_gen_log.csv", 'w') as file:
                            file.write("Table Generation Log\n")                          



        # hand the request off to the get method to finish rendering the page
        self.do_GET()

    def get_graphs_template(self,project):
        """
        Generates HTML content for displaying graphs associated with a project.

        Args:
            project (Project): The project object for which graphs are to be displayed.

        Returns:
            str: A string containing HTML for embedding and interacting with project-specific graphs within the web interface.
        """

        return_str = ""
        graphs_html = """
                    <div class="plot-container image-container">
                        <h2>{{TITLE}}</h2>
                        <span class="plot-description">{{PLOT-DESCRIPTION}}</span><br/>
                            <img src="{{PROJECT_NAME}}/plots/{{FILENAME}}" alt="{{TITLE}}" 
                                    id="{{GRAPH}}" name="{{GRAPH}}">
                        <br/>
                        <form method="post" action="/?project={{PROJECT_NAME}}#Graphical_Analysis">
                            <input type="hidden" name="regen_graph" value="{{GRAPH}}">
                            <input type="hidden" name="project_name" value="{{PROJECT_NAME}}">
                            <input type="submit" value="Regenerate Graph">
                        </form>
                        <image src="/images/view-large.png" alt="View Large" class="view-large">
                    </div>
            """
        # read the graphs.json from plots dir
        # if the file exists, read the file, then for each graph in the list, create a div with the graph and title
        json_file = os.path.join(project.project_directory, project.project_name, "plots/graphs.json")
        
        if os.path.exists(json_file):
            with open(json_file, 'r') as file:
                graphs_list = json.load(file)
            # for each graph in the list, the key is the template var, the value is the value, call 
            for graph in graphs_list:
                tmp = graphs_html
                tmp = self.do_replace_template_var(tmp, "{{TITLE}}", graph['TITLE'])
                tmp = self.do_replace_template_var(tmp, "{{FILENAME}}", graph['FILENAME'])
                tmp = self.do_replace_template_var(tmp, "{{GRAPH}}", graph['GRAPH'])
                tmp = self.do_replace_template_var(tmp, "{{PLOT-DESCRIPTION}}", graph['PLOT-DESCRIPTION'])
                return_str += tmp + "\n                "
            return return_str
        else:
             return "<h2>No Graphs Available</h2>"

    def get_tables_template(self,project):
        """
        Generates HTML content for displaying tables associated with a project.

        Args:
            project (Project): The project object for which tables are to be displayed.

        Returns:
            str: A string containing HTML for embedding and interacting with project-specific tables within the web interface.
        """

        return_str = ""
        table_html = """
                    <div class="table_container">
                        <h2>{{TITLE}}</h2>
                        <span class="table-description">{{TABLE-DESCRIPTION}}</span><br/>
                            <div class="table-responsive">
                                {{TABLE-DATA}}
                            </div>
                        <br/>
                        <form method="post" action="/?project={{PROJECT_NAME}}#Report_Management">
                            <input type="hidden" name="regen_table" value="{{TABLE}}">
                            <input type="hidden" name="project_name" value="{{PROJECT_NAME}}">
                            <input type="submit" value="Regenerate Table">
                        </form>
                    </div>
            """
        # read the tables.json from tables dir
        # if tables dir doesn't exist, create it
        if not os.path.exists(os.path.join(project.project_directory, project.project_name, "tables")):
            os.makedirs(os.path.join(project.project_directory, project.project_name, "tables"))
        
        json_file = os.path.join(project.project_directory, project.project_name, "tables/tables.json")
        if os.path.exists(json_file):
            with open(json_file, 'r') as file:
                tables_list = json.load(file)
            # for each graph in the list, the key is the template var, the value is the value, call 
            for table in tables_list:
                tmp = table_html
                # attempt to read a {{table}}.html file from the tables dir, if it doesn't exist error
                if not os.path.exists(os.path.join(project.project_directory, project.project_name, "tables", table['FILENAME'])):
                    raise FileNotFoundError("Table file not found: " + os.path.join(project.project_directory, project.project_name, "tables", table['FILENAME']))
                with open(os.path.join(project.project_directory, project.project_name, "tables", table['FILENAME']), 'r') as file:
                    table_data = file.read()
                tmp = self.do_replace_template_var(tmp, "{{TITLE}}", table['TITLE'])
                tmp = self.do_replace_template_var(tmp, "{{FILENAME}}", table['FILENAME'])
                tmp = self.do_replace_template_var(tmp, "{{TABLE-DATA}}", table_data)
                tmp = self.do_replace_template_var(tmp, "{{TABLE-DESCRIPTION}}", table['TABLE-DESCRIPTION'])
                return_str += tmp + "\n                "
            return return_str
        else:
             return "<h2>No Tables Available</h2>"
        

    def queue_template_var(self, var_name, var_value,priority=False):
        """
        Queues a template variable for replacement in the HTML content.

        Args:
            var_name (str): The name of the template variable to replace.
            var_value (str): The value to replace the template variable with.
            priority (bool, optional): If True, the variable is placed at the front of the queue for early replacement. Defaults to False.
        """

        # add the requested template variable to the var_queue
        if priority:
            self.var_queue = {var_name: var_value, **self.var_queue}
        else:
            self.var_queue[var_name] = var_value

    def do_replace_template_vars(self,template_string):
        """
        Performs template variable replacement within a given HTML template string.

        Iterates over queued template variables, replacing placeholders in the template string with their corresponding values.

        Args:
            template_string (str): The HTML template string with placeholders for variable substitution.

        Returns:
            str: The updated HTML template string with all queued template variables replaced by their respective values.
        """

        # replace all the template variables in the template string with the values in the var_queue
        for var in self.var_queue:
            template_string = self.do_replace_template_var(template_string, var, self.var_queue[var])
        return template_string
    
    def do_replace_template_var(self,template_string, var_name, var_value):
        """
        Replaces a single template variable with its corresponding value in the HTML template string.

        Args:
            template_string (str): The HTML template string containing the placeholder for the variable.
            var_name (str): The placeholder name of the template variable to be replaced.
            var_value (str): The value to replace the template variable with.

        Returns:
            str: The HTML template string with the specified template variable replaced by its value.
        """
            
        # replace the requested template variable in the template string with the value
        template_string = template_string.replace(var_name, var_value)
        return template_string
    
    def format_option_list(self,options,current_option=None):
        """
        Generates HTML <option> elements for each item in a list, marking one as selected if specified.

        Useful for dynamically generating dropdown menus in the HTML interface with the current selection marked.

        Args:
            options (list): A list of option values to be included in the dropdown.
            current_option (str, optional): The value of the option to be marked as selected. Defaults to None.

        Returns:
            str: A string containing <option> tags for each item in the list, with the current_option (if any) marked as selected.
        """

        # create html options list from the list of projects
        ops = ""
        for option in options:
            cp = "selected" if option == current_option else ""
            ops += "<option " + cp + " value='" + option + "'>" + option + "</option>"
        return ops

    def load_project_vars(self,project):
        """
        Queues project-specific variables for replacement in the HTML content based on the current project's attributes.

        This method is called to update the web interface with details from a specific project, preparing variables for dynamic content generation.

        Args:
            project (Project): The project object whose attributes are to be reflected in the HTML content.
        """

        # load the project variables into the template queue

        self.queue_template_var("{{PROJECT_NAME}}", str(project.project_name))
        self.queue_template_var("{{PROJECT_DIRECTORY}}", str(project.project_directory))
        self.queue_template_var("{{SOURCES}}", str(project.sources))
        self.queue_template_var("{{DESTINATIONS}}", str(project.destinations))
        self.queue_template_var("{{USE_GPS_FUZZING}}", "checked" if project.use_gps_fuzzing else "")
        self.queue_template_var("{{GPS_FUZZ_FACTOR}}", str(project.gps_fuzz_factor))
        self.queue_template_var("{{GMAPS_API_KEY}}", str(project.GMAPS_API_KEY))
        self.queue_template_var("{{COMMUTE_RANGE_CUT_OFF}}", str(project.commute_range_cut_off))
        self.queue_template_var("{{COMMUTE_RANGE_CUT_OFF_UNIT}}", str(project.commute_range_cut_off_unit))
        self.queue_template_var("{{COMMUTE_DAYS_PER_WEEK}}", str(project.commute_days_per_week))
        self.queue_template_var("{{COMMUTE_WEEKS_PER_YEAR}}", str(project.commute_weeks_per_year))
        self.queue_template_var("{{MORNING_COMMUTE_START}}", str(project.morning_commute_start))
        self.queue_template_var("{{EVENING_COMMUTE_START}}", str(project.evening_commute_start))
        self.queue_template_var("{{MILEAGE_RATE}}", str(project.mileage_rate))
        self.queue_template_var("{{CO2_PER_MILE}}", str(project.CO2_per_mile))
        self.queue_template_var("{{TRAFFIC_REGIME_1}}", str(project.traffic_regime_1))
        self.queue_template_var("{{TRAFFIC_REGIME_2}}", str(project.traffic_regime_2))
        self.queue_template_var("{{TRAFFIC_REGIME_3}}", str(project.traffic_regime_3))
        self.queue_template_var("{{TRAFFIC_REGIME_1_COEFF}}", str(project.traffic_regime_1_coeff))
        self.queue_template_var("{{TRAFFIC_REGIME_2_COEFF}}", str(project.traffic_regime_2_coeff))
        self.queue_template_var("{{TRAFFIC_REGIME_3_COEFF}}", str(project.traffic_regime_3_coeff))
        self.queue_template_var("{{CO2_CREDIT_COST}}", str(project.CO2_credit_cost))
        self.queue_template_var("{{MEDIAN_SALARY}}", str(project.median_salary))
        self.queue_template_var("{{TURNOVER_THRESHOLD_COST}}", str(project.turnover_threshold_due_to_cost))
        self.queue_template_var("{{TURNOVER_PROBABILITY_TIME_COST}}", str(project.turnover_probability_time_cost))
        self.queue_template_var("{{EMPLOYEE_REPLACEMENT_COST}}", str(project.employee_replacement_cost))



        

    def parse_multipart(self,mp):
        """
        Parses multipart/form-data from a POST request into a more accessible dictionary format.

        This method is used when handling file uploads or forms with complex data. It converts the MultipartDecoder object into a 
        dictionary where each part's content is easily accessible.

        Args:
            mp (MultipartDecoder): The MultipartDecoder object containing the multipart/form-data from the POST request.

        Returns:
            dict: A dictionary representation of the multipart data, with keys for each form field and values for the field content or file data.
        """
        pass
        
        post_data = {}
        for part in mp.parts:
            # extract the key value pairs out of the header
            kv = self.parse_key_value_pairs(str(part.headers))
            # if the part headers has a key for Content-Type, it is a file, not a simple key value pair.
            if b'Content-Type' in part.headers:
                tmp = {}
                for each in kv:
                    tmp[each] = kv[each]
                tmp['Content-Type'] = str(part.headers[b'Content-Type'])
                tmp['Content-Data'] = str(part.text)
                post_data[kv['name']] = tmp
            else:
                post_data[kv['name']] = part.text
            
        return post_data

    def parse_key_value_pairs(self,input_string):
        """
        Extracts key-value pairs from a string, typically from the headers of a multipart/form-data part.

        Args:
            input_string (str): The string containing key-value pairs, often from part headers in multipart/form-data.

        Returns:
            dict: A dictionary where each key is a header name and the corresponding value is the header value.
        """
    
        # Pattern to match key=value pairs where value is in quotes
        pattern = r'(\w+)="([^"]*)"'
        
        # Find all matches of the pattern
        matches = re.findall(pattern, input_string)
        
        # Convert matches to a dictionary
        result = {key: value for key, value in matches}
        return result
    
def run(server_class=HTTPServer, handler_class=HTTP_UI):
    """
    Starts the HTTP server and serves the web interface for the Relocation Impact Analyzer.

    This function initializes and starts an HTTP server on a specified address and port, using HTTP_UI as the request handler class.

    Args:
        server_class (HTTPServer, optional): The HTTP server class to use. Defaults to HTTPServer.
        handler_class (HTTP_UI, optional): The request handler class. Defaults to HTTP_UI.

    This server setup is intended for demonstration purposes and lacks security features for production use.
    """
    
    server_address = ('127.0.0.1', 8080)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()
