## Ribasim Data Extractor CLI - By Eng. Hosam El Nagar

Extract & analyze Ribasim simulation results' files


  ### Project Overview


  This project is a Python-based command-line interface (CLI) application named "Ribasim Data Extractor". Its primary purpose is to extract, analyze, and
  visualize data from Ribasim simulation files, specifically focusing on .his files. The application is designed to be interactive, guiding the user through a
  series of steps to select the data they are interested in.

  ### Core Functionality


   1. Basin and Case Selection: The user is prompted to select a "Basin" from a list of available .rbn or .Rbd folders located in C:\Ribasim7. After selecting a
      basin, the application reads a CASELIST.CMT file within the basin's folder to present a list of "Cases" for the user to choose from.
   2. .his File Selection: Once a case is selected, the application scans the corresponding case folder for .his files and allows the user to select one for
      analysis.
   3. Data Extraction and Processing: The application uses a custom his module (Based on https://gitlab.com/visr/his-python) to read the binary .his files. This module, based
      on xarray and pandas, parses the file format and extracts the simulation data.
   4. Data Analysis and Visualization: After extraction, the user is presented with a menu of actions to choose from.


  You can now run the application in two ways:


   1. Interactive Mode (no arguments):
  `shell
      python ribasim_extractor.py
      `
      This will launch the familiar interactive menu.


   2. Non-Interactive Mode (with arguments):
  `shell
      python ribasim_extractor.py --basin "JCARWQV7.Rbd" --case "2" --his-file "some_file.his" --export "csv"
      `
      This will directly process the specified file and export it without any user prompts. Note that --basin, --case, and --his-file are all
  required to use this mode.