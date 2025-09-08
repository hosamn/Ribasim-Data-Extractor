#######################################################
#   Ribasim Data Extractor CLI - By Eng. Hosam El Nagar
#   Extract & analyze Ribasim simulation results' files
#   Based on https://gitlab.com/visr/his-python
#######################################################


# import os
# import sys
import click
# import argparse
# import seaborn as sns
import re
from pathlib import Path
from typing import List, Tuple, Optional  # Dict,
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime  # , timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
import inquirer

from his import read as readhis


# Setup #######################
base_path = r"C:\Ribasim7"
# Setup #######################

console = Console()


class RibasimDataExtractor:
    """Main class for extracting and processing Ribasim data."""

    def __init__(self, base_path: str = base_path):
        self.base_path = Path(base_path)
        self.selected_basin = None
        self.selected_case = None
        self.available_his_files = []

    def get_available_basins(self) -> List[str]:
        """Get list of available basins from folders ending with .rbn or .Rbd."""
        basins = []
        exclude_list = ["xxxx.rbn", "yyyy.rbd"]

        try:
            if not self.base_path.exists():
                console.print(f"[red]Error: Base path {self.base_path} does not exist[/red]")
                return basins

            for item in self.base_path.iterdir():
                if item.is_dir():
                    basin_name = item.name
                    if (basin_name.lower().endswith('.rbn') or basin_name.lower().endswith('.rbd')) and basin_name not in exclude_list:
                        basins.append(basin_name)

        except Exception as e:
            console.print(f"[red]Error reading basins: {e}[/red]")

        return sorted(basins)

    def get_available_cases(self, basin_name: str) -> List[Tuple[str, str]]:
        """Get list of available cases from CASELIST.CMT file."""
        cases = []
        caselist_path = self.base_path / basin_name / "CASELIST.CMT"

        try:
            if not caselist_path.exists():
                console.print(f"[yellow]Warning: CASELIST.CMT not found in {basin_name}[/yellow]")
                return cases

            with open(caselist_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Parse the format: case_number "case_name"
            pattern = r'(\d+)\s+"([^\"]+)"'
            matches = re.findall(pattern, content)

            for case_number, case_name in matches:
                # Verify the case folder exists
                case_folder = self.base_path / basin_name / case_number
                if case_folder.exists():
                    cases.append((case_number, case_name))

        except Exception as e:
            console.print(f"[red]Error reading cases: {e}[/red]")

        return cases

    def scan_his_files(self, basin_name: str, case_number: str) -> List[str]:
        """Scan for .his files in the selected case folder."""
        his_files = []
        case_path = self.base_path / basin_name / case_number

        try:
            if not case_path.exists():
                console.print(f"[red]Error: Case folder {case_path} does not exist[/red]")
                return his_files

            # Search for .his files recursively
            for his_file in case_path.rglob("*.his"):
                his_files.append(str(his_file.relative_to(case_path)))

        except Exception as e:
            console.print(f"[red]Error scanning .his files: {e}[/red]")

        return sorted(his_files)

    def extract_his_data(self, his_file_path: str) -> Optional[object]:
        """Extract data from a .his file using the provided his module."""
        try:
            full_path = self.base_path / self.selected_basin / self.selected_case / his_file_path

            if not full_path.exists():
                console.print(f"[red]Error: File {full_path} does not exist[/red]")
                return None

            # Use the readhis function from his module
            dataset = readhis(str(full_path))
            return dataset

        except Exception as e:
            console.print(f"[red]Error reading .his file {his_file_path}: {e}[/red]")
            return None

    def aggregate_data(self, dataset, aggregation_type: str = "daily") -> object:
        """Aggregate data based on the specified type."""
        try:
            if aggregation_type.lower() == "daily":
                # Resample to daily averages
                return dataset.resample(time="1D").mean()
            elif aggregation_type.lower() == "dekadal":
                # 3 periods per month (10-day periods)
                return dataset.resample(time="10D").mean()
            elif aggregation_type.lower() == "monthly":
                return dataset.resample(time="1M").mean()
            elif aggregation_type.lower() == "weekly":
                return dataset.resample(time="1W").mean()
            else:
                console.print(f"[yellow]Unknown aggregation type: {aggregation_type}. Using original data.[/yellow]")
                return dataset

        except Exception as e:
            console.print(f"[red]Error aggregating data: {e}[/red]")
            return dataset

    def display_data_summary(self, dataset):
        """Display a summary of the dataset."""
        try:
            table = Table(title="Dataset Summary")
            table.add_column("Parameter", style="cyan")
            table.add_column("Stations", style="magenta")
            table.add_column("Time Range", style="green")
            table.add_column("Data Points", style="yellow")

            for var_name in dataset.data_vars:
                var = dataset[var_name]
                time_range = f"{str(var.time.min().values)[:10]} to {str(var.time.max().values)[:10]}"
                data_points = var.size
                stations = len(var.station)

                table.add_row(var_name, str(stations), time_range, str(data_points))

            console.print(table)

            # Display attributes
            if hasattr(dataset, 'attrs') and dataset.attrs:
                console.print("\n[bold]Dataset Attributes:[/bold]")
                for key, value in dataset.attrs.items():
                    console.print(f"  {key}: {value}")

        except Exception as e:
            console.print(f"[red]Error displaying data summary: {e}[/red]")

    def plot_data(self, dataset, parameter: str, stations: List[str] = None, save_path: str = None):
        """Create plots for the selected data."""
        try:
            if parameter not in dataset.data_vars:
                console.print(f"[red]Parameter {parameter} not found in dataset[/red]")
                return

            var = dataset[parameter]

            if stations is None:
                # Select up to 10 stations for plotting
                stations = list(var.station.values)[:10]

            plt.figure(figsize=(12, 8))

            for station in stations:
                if station in var.station.values:
                    data = var.sel(station=station)
                    plt.plot(data.time, data.values, label=f"Station {station}", alpha=0.7)

            plt.title(f"{parameter} - Time Series")
            plt.xlabel("Time")
            plt.ylabel(f"{parameter} ({var.attrs.get('units', 'N/A')})")
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                console.print(f"[green]Plot saved to {save_path}[/green]")
            else:
                plt.show()

        except Exception as e:
            console.print(f"[red]Error plotting data: {e}[/red]")

    def export_data(self, dataset, export_format: str = "csv", output_path: str = None):
        """Export data to CSV or Excel format."""
        try:
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"ribasim_export_{timestamp}"

            if export_format.lower() == "csv":
                # Convert xarray dataset to pandas DataFrame and save as CSV
                df = dataset.to_dataframe()
                csv_path = f"{output_path}.csv"
                df.to_csv(csv_path)
                console.print(f"[green]Data exported to {csv_path}[/green]")

            elif export_format.lower() == "excel":
                # Export to Excel with multiple sheets for different parameters
                excel_path = f"{output_path}.xlsx"
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    # Write summary sheet
                    summary_data = {
                        'Parameter': list(dataset.data_vars.keys()),
                        'Stations': [len(dataset[var].station) for var in dataset.data_vars],
                        'Time_Points': [len(dataset[var].time) for var in dataset.data_vars],
                        'Units': [dataset[var].attrs.get('units', 'N/A') for var in dataset.data_vars]
                    }
                    pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

                    # Write data for each parameter
                    for var_name in dataset.data_vars:
                        df = dataset[var_name].to_dataframe()
                        sheet_name = var_name[:31]  # Excel sheet name limit
                        df.to_excel(writer, sheet_name=sheet_name)

                console.print(f"[green]Data exported to {excel_path}[/green]")

            else:
                console.print(f"[red]Unsupported export format: {export_format}[/red]")

        except Exception as e:
            console.print(f"[red]Error exporting data: {e}[/red]")


def interactive_mode():
    """Run the application in interactive mode."""
    extractor = RibasimDataExtractor()

    try:
        # Step 1: Select Basin
        console.print("\n[bold]Step 1: Select Basin[/bold]")
        basins = extractor.get_available_basins()

        if not basins:
            console.print("[red]No basins found. Please check the base path.[/red]")
            return

        basin_choices = [inquirer.List('basin', message="Select a basin", choices=basins)]
        basin_answer = inquirer.prompt(basin_choices)

        if not basin_answer:
            console.print("[yellow]Operation cancelled.[/yellow]")
            return

        extractor.selected_basin = basin_answer['basin']
        console.print(f"[green]Selected basin: {extractor.selected_basin}[/green]")

        # Step 2: Select Case
        console.print("\n[bold]Step 2: Select Case[/bold]")
        cases = extractor.get_available_cases(extractor.selected_basin)

        if not cases:
            console.print("[red]No cases found for the selected basin.[/red]")
            return

        case_choices = [f"{num} - {name}" for num, name in cases]
        case_selection = [inquirer.List('case', message="Select a case", choices=case_choices)]
        case_answer = inquirer.prompt(case_selection)

        if not case_answer:
            console.print("[yellow]Operation cancelled.[/yellow]")
            return

        extractor.selected_case = case_answer['case'].split(' - ')[0]
        console.print(f"[green]Selected case: {extractor.selected_case}[/green]")

        # Step 3: Scan for .his files
        console.print("\n[bold]Step 3: Available .his files[/bold]")
        his_files = extractor.scan_his_files(extractor.selected_basin, extractor.selected_case)

        if not his_files:
            console.print("[red]No .his files found in the selected case.[/red]")
            return

        his_choices = [inquirer.List('his_file', message="Select a .his file", choices=his_files)]
        his_answer = inquirer.prompt(his_choices)

        if not his_answer:
            console.print("[yellow]Operation cancelled.[/yellow]")
            return

        selected_his = his_answer['his_file']
        console.print(f"[green]Selected .his file: {selected_his}[/green]")

        # Step 4: Extract data
        console.print("\n[bold]Step 4: Extracting data...[/bold]")
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Loading data...", total=None)
            dataset = extractor.extract_his_data(selected_his)
            progress.update(task, description="Data loaded successfully!")

        if dataset is None:
            console.print("[red]Failed to extract data.[/red]")
            return

        # Step 5: Display summary and options
        extractor.display_data_summary(dataset)

        # Step 6: Processing options
        while True:
            console.print("\n[bold]Available Actions:[/bold]")
            actions = [
                "View detailed data",
                "Aggregate data",
                "Create plots",
                "Export data",
                "Exit"
            ]

            action_choices = [inquirer.List('action', message="What would you like to do?", choices=actions)]
            action_answer = inquirer.prompt(action_choices)

            if not action_answer or action_answer['action'] == "Exit":
                break

            action = action_answer['action']

            if action == "View detailed data":
                # Show first few rows of data
                df = dataset.to_dataframe()
                console.print("\n[bold]Data Preview:[/bold]")
                console.print(df.head().to_string())

            elif action == "Aggregate data":
                agg_types = ["daily", "dekadal", "weekly", "monthly"]
                agg_choices = [inquirer.List('agg_type', message="Select aggregation type", choices=agg_types)]
                agg_answer = inquirer.prompt(agg_choices)

                if agg_answer:
                    dataset = extractor.aggregate_data(dataset, agg_answer['agg_type'])
                    console.print(f"[green]Data aggregated using {agg_answer['agg_type']} method[/green]")
                    extractor.display_data_summary(dataset)

            elif action == "Create plots":
                parameters = list(dataset.data_vars.keys())
                param_choices = [inquirer.List('parameter', message="Select parameter to plot", choices=parameters)]
                param_answer = inquirer.prompt(param_choices)

                if param_answer:
                    save_plot = Confirm.ask("Save plot to file?")
                    save_path = None
                    if save_plot:
                        save_path = Prompt.ask("Enter save path (without extension)", default="ribasim_plot")
                        save_path += ".png"

                    extractor.plot_data(dataset, param_answer['parameter'], save_path=save_path)

            elif action == "Export data":
                export_formats = ["csv", "excel"]
                format_choices = [inquirer.List('format', message="Select export format", choices=export_formats)]
                format_answer = inquirer.prompt(format_choices)

                if format_answer:
                    output_path = Prompt.ask("Enter output filename (without extension)", default="ribasim_export")
                    extractor.export_data(dataset, format_answer['format'], output_path)

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")


def cli_mode(basin: str, case: str, his_file: str, export: str):
    """Run the application in non-interactive CLI mode."""
    extractor = RibasimDataExtractor()
    extractor.selected_basin = basin
    extractor.selected_case = case

    console.print("[bold]Running in non-interactive mode...[/bold]")
    console.print(f"Basin: {basin}, Case: {case}, File: {his_file}, Export: {export}")

    # Validate inputs
    if basin not in extractor.get_available_basins():
        console.print(f"[red]Error: Basin '{basin}' not found.[/red]")
        return

    case_folder_path = extractor.base_path / basin / case
    if not case_folder_path.exists() or not case_folder_path.is_dir():
        console.print(f"[red]Error: Case folder '{case}' not found in basin '{basin}'.[/red]")
        return

    available_files = extractor.scan_his_files(basin, case)
    if his_file not in available_files:
        console.print(f"[red]Error: .his file '{his_file}' not found in case '{case}'.[/red]")
        console.print(f"Available files: {available_files}")
        return

    # Extract data
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task(f"Loading data from {his_file}...", total=None)
        dataset = extractor.extract_his_data(his_file)
        progress.update(task, description="Data loaded successfully!")

    if dataset is None:
        console.print("[red]Failed to extract data.[/red]")
        return

    extractor.display_data_summary(dataset)

    # Export data
    if export:
        if export.lower() not in ["csv", "excel"]:
            console.print(f"[red]Error: Invalid export format '{export}'. Choose 'csv' or 'excel'.[/red]")
            return

        output_path = f"{Path(his_file).stem}_{export}"
        console.print(f"\n[bold]Exporting data to {export.upper()}...[/bold]")
        extractor.export_data(dataset, export, output_path)


@click.command()
@click.option('--basin', default=None, help='The basin name (e.g., "JCARWQV7.Rbd")')
@click.option('--case', default=None, help='The case number (e.g., "1")')
@click.option('--his-file', 'his_file', default=None, help='The .his file to process (relative to the case folder)')
@click.option('--export', default=None, help='Export format: "csv" or "excel"')
def main(basin: Optional[str], case: Optional[str], his_file: Optional[str], export: Optional[str]):
    """Main CLI interface.\n\nExample:   ribasim_extractor.py --basin "JCARWQV7.Rbd" --case "2" --his-file "TOTPLAN.HIS" --export "csv" """
    console.print(Panel.fit("""         🌊 Ribasim Data Extractor\n\nExtract & analyze Ribasim simulation results\n          By:  Eng. Hosam El-Nagar""", style="bold blue"))

    # If any CLI arguments are provided, run in non-interactive mode
    if any([basin, case, his_file, export]):
        if not all([basin, case, his_file]):
            console.print("[red]Error: --basin, --case, and --his-file are all required for non-interactive mode.[/red]")
            return
        cli_mode(basin, case, his_file, export)
    else:
        interactive_mode()

    console.print("\n[green]Thank you for using Ribasim Data Extractor![/green]")


if __name__ == "__main__":
    main()
