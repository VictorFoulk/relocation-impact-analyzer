# Relocation Impact Analyizer

## Introduction

This package forms the core of the Relocation Impact Analyzer project, designed to support a customer in evaluating the implications 
of potential office relocation on employee commutes, environmental impact, and related financial considerations. 
It offers a comprehensive toolkit for analyzing various relocation scenarios, integrating geospatial intelligence, traffic analytics, 
and cost-benefit analyses to aid in strategic decision-making.

The Relocation Impact Analyzer facilitates a detailed examination of how changing the company's headquarters location could affect 
operational efficiency, employee satisfaction, and the organization's environmental footprint. By assessing these impacts across different 
relocation options, this package helps translate complex analytics into actionable insights and financial terms, contributing significantly 
to the overall business case evaluation.

Package Contents:
- analyzer: Contains core functionalities for conducting the impact analysis.
- project: Manages project-specific data and configurations.
- g_api: Interfaces with geospatial and traffic analytics APIs.
- ui: Provides a web-based user interface for interactive analysis and visualization.
- graphing: Supports the generation of graphical representations of analysis outcomes.

Additionally, this package initializes the package environment, setting up necessary configurations and routines essential for its operation.

Note: This package adheres to ENMA 605 guidelines and legal requirements for the protection of sensitive information such as employee identities. 
It is part of a broader project aiming to enhance a customer's strategic planning process and provide a reusable framework for future analyses.

## Features

- Analyze and visualize commute data.
- Calculate commute costs and environmental impact.
- Support for GPS data fuzzing for privacy.
- Extensible to various data inputs and customizable analysis parameters.

## Installation

Clone the repository if you wish, otherwise just download the ZIP file from GitHub:

```bash
git clone https://github.com/VictorFoulk/relocation-impact-analyzer.git
```
Create a virtual environment

```bash
python3 -m venv path-to-folder-you-desire
```

Activate the virtual environment

```bash
source ./path-to-your-venv/bin/activate
```

Copy the relocation_impact_analyzer package contents into your venv folder.

```bash
cp -r dowload-folder/relocation_impact_analyzer path-to-folder-you-desire/.
```
Install dependencies:

```bash
pip3 install -r requirements.txt
```

Install the package:

```bash
python3 setup.py install
```

Deactivate venv when done

```bash
deactivate
```

For more information on managing virutal environments and manualy installing pre-alpha stage packages, see [https://docs.python.org/3/tutorial/venv.html]
## Usage

To start the Relocation Impact Analyzer UI, start your vitual environment and simply use the -m flag to run the module. When done, use <CTRL+C> to kill the server, or the "Stop Server" button on the UI itself.

```console
source ./path-to-folder-you-desire/bin/activate
python3 -m relocation_impact_analyzer
```
Alternatively, you may use "&" to run the process in the background, in which chase the "Stop Server" button on the UI will be required to stop the server.  Additionally, you will not be able to see the debug output.
```console
python3 -m relocation_impact_analyzer &
```
Once the UI server is running, it may be accessed via brower by navigating to:
```
http://localhost:8080
```

When done, exit your virtual environment.

```console
deactivate
```

### User Workflow Documentation for Relocation Impact Analyzer UI

#### Overview
The Relocation Impact Analyzer User Interface (UI) is designed to guide users through a step-by-step workflow for analyzing the impact of employee relocations. Each phase of the analysis unlocks sequentially, ensuring that the user completes necessary actions before progressing. The interface consists of distinct sections, each with controls that correspond to a specific stage of analysis. Green checkmarks appear next to controls and sections upon completion, providing visual confirmation of progress.

#### Workflow Steps

1. **Start Project**  
   - **Manage System Settings**: Adjust global system settings, including the server and API keys.
   - **Create New Project**: Begin a new analysis project by entering a unique project name.
   - **Manage Existing Projects**: Load, edit, or delete existing projects.
   - **Loaded Project Name**: Displays the name of the currently active project.
   - **Project Analysis Phase**: Indicates the current phase of the project.
   - **System Messages**: Provides feedback and status updates to the user.

2. **Load Data**  
   - **Upload a Data File**: Import data files into the project, such as employee and office addresses or GPS coordinates. Files are automatically renamed based on the type of data uploaded.
   - **Manage Existing Data Files**: View or delete data files that have already been uploaded to the project.

3. **Generate Analysis Data**  
   - **Convert Addresses to Lat/Long**: Utilizes the Google Maps API to convert address data into latitude and longitude coordinates.
   - **Fuzz Employee Lat/Long**: Adds random variability to employee GPS data for privacy.
   - **Generate Commute Data**: Uses Google Maps API to calculate detailed commute data.
   - **Update Derivative Data**: Recalculates costs and emissions data without rerunning API calls, useful for parameter changes.

4. **Graphical Analyses**  
   - **Generate Graphs**: Produces various graphs to visually analyze data.

#### Phase Progression and Control Boxes
Each row of functionality corresponds to a specific phase in the analysis process. Controls within each row are progressively revealed as required actions are completed. For example, the option to fuzz employee GPS data appears only after the addresses have been converted to lat/long coordinates.

#### Completion Indicators
- **Control Level**: When a specific action within a control box is completed, a green check appears next to the control, signaling successful execution of that task.
- **Row Level**: Once all controls within a row are satisfied, a green check appears on the row's icon, denoting that the entire phase is complete.

#### Interface Behavior
- Controls are enabled or disabled based on the project's current phase.
- The interface prevents users from progressing to subsequent phases without completing the current one.
- Relevant controls become available as the project advances through phases, ensuring the user follows a logical and efficient workflow.
- Green checks provide immediate visual feedback, improving user experience and workflow clarity.

#### Additional UI Features
- Modals for system settings and project variables allow for in-depth configuration without leaving the main interface.
- Links to documentation and data file formats support the user in preparing and uploading appropriate data.

#### Notes for Users
- API rate limits from external services such as Google Maps may require waiting periods between certain actions.
- Users should monitor system messages for any errors or important notifications.
- Regularly saving progress and configurations is advised to prevent loss of data.

This documentation captures the essence of the workflow based on the provided UI and code discussions. It is designed to guide users smoothly through the analysis process while providing feedback and control.

## Requirements

This project requires Python 3.6+ and the following Python libraries:
- Cartopy
- googlemaps
- matplotlib
- numpy
- pandas
- python-dotenv
- requests_toolbelt
- scipy
- setuptools

See `requirements.txt` for a complete list of dependencies.

## Contributing

Contributions are welcome!

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE) file for details.

## Contact

For any queries or further information, you can contact me via email at my gmail address, which is first dot last @.
