# TODO List for Ribasim Data Extractor

## High Priority

- [x] **Add Command-Line Arguments:** Implement a full CLI interface using `click` or `argparse` to allow for non-interactive use and scripting. For example: `python ribasim_extractor.py --basin "MyBasin.rbn" --case 1 --export csv`.
- [x] **Show used option Arguments** after an export, show the CLI arguments that can be used to execute the same current task again directly in non-interactive mode.
- [ ] **Display file metadata:** while the user is choosing between the his files, the first part of the file's description from [Dataset Attributes - header] is shown to help the user understand the file's content.
- [ ] **Output file name** change the default outbut file name to be like [Basin_Name-Case-Name-first_part_of_His_description]
- [ ] **Open with Default viewer** after selecting the his file, add the option: "Open with ODS_View" (in the Available Actions) to open the file in the viewer from "C:\Ribasim7\Programs\ODS_View\ODS_View.exe"
- [ ] **Parameter Filtering:** After selecting a `.his` file and showing the data, allow the user to choose specific parameters to load or analyze if they want (a "Select Parameter" option in the Available Actions). This will improve performance and reduce memory usage for large files.
- [ ] **Load Cases from folders** read the case list directly from folder names along with using caselist.cmt, then display a comment beside the case name wether it is in the caselist or not, like this: "Case xx CASE_NAME (in case list)" or "Case xx CASE_NAME (not in case list)"

## Feature Enhancements

- [ ] **Multi-File/Case Comparison:** Allow the user to select multiple `.his` files or cases to compare results. This would involve:
- [ ] Modifying the UI to support multiple selections.
- [ ] Updating the plotting logic to show data from different sources on the same graph.
- [ ] **Detailed Statistical Analysis:** Add an action to show a table with detailed statistics (mean, median, min, max, standard deviation) for the selected data series.
- [ ] **Advanced Plotting Options:** Give users more control over plots, such as specifying date ranges, custom titles/labels, and choosing different plot styles.

## Low Priority

- [ ] **Implement Logging:** Use Python's `logging` module to write status messages and errors to a log file (`extractor.log`).
- [ ] **Add Unit Tests:** Create a `tests/` directory and add unit tests for core functions in `RibasimDataExtractor` and the `his.read` function to ensure reliability.
- [ ] **Package Application:** Create a `setup.py` so the project can be properly packaged and installed using `pip`.
