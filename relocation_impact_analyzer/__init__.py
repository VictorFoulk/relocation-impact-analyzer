"""
Relocation Impact Analyzer Package

Author: Victor Foulk
License: MIT License
Date: 2024-03-15
Version: 0.0.1 Pre-Alpha

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

Note: This package adheres to ENMA 605 guidelines and legal requirements for the protection of sensitive information. 
It is part of a broader project aiming to enhance a customer'sstrategic planning process and provide a reusable framework for future analyses.
"""

from relocation_impact_analyzer.analyzer import *
from relocation_impact_analyzer.project import *
from relocation_impact_analyzer.g_api import *
from relocation_impact_analyzer.ui import *
from relocation_impact_analyzer.graphing import *
import os

