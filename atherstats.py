# app.py
import typer
import os
from pathlib import Path
import shutil
import subprocess
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys # Import sys for cli_command_args logging

# Import Rich components
from rich.traceback import install
install()
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from typing_extensions import Annotated

# Import agents from agents.py (Assuming this file exists and contains the agents and their output models)
from agents import (
    register_file_auto_describe_agent,
    aether_explain_agent, # Re-added for completeness if needed elsewhere
    aether_insight_agent,
    aether_analysis_agent,
    aether_code_generation_agent,
    aether_report_agent,
    # Import output models for type hinting
    RegisterFileAutoDescribeOutput,
    AetherInsightOutput, # New: Import for explore command
    AnalysisOutput,
    CodeGenerationOutput, # Kept for generate command
    MarkdownReportOutput # Kept for generate command
)

# Initialize Rich Console
console = Console()

app = typer.Typer(help="AetherStats CLI: Your intelligent assistant for statistical workflows.")

# Define nested typer app for 'generate' command
generate_app = typer.Typer(help="Generate code or a report.")
app.add_typer(generate_app, name="generate")


# --- Project Configuration ---
# Use Path objects for consistency
# Initialize PROJECT_ROOT to None globally.
# This variable will be set by the main_callback or init command.
PROJECT_ROOT: Optional[Path] = None
AETHERSTATS_DIR_NAME = ".aetherstats"
MANIFEST_FILE_NAME = "manifest.json"
LOG_FILE_NAME = "logs.txt"

# --- Utility Functions ---

def _find_project_root() -> Optional[Path]:
    """
    Traverses up the directory tree to find the project root.
    A project root is identified by the presence of an '.aetherstats' directory.
    """
    current_dir = Path.cwd()
    # Check current_dir and then its parents up to the file system root
    while True:
        if (current_dir / AETHERSTATS_DIR_NAME).is_dir():
            return current_dir
        if current_dir == current_dir.parent: # Reached file system root
            break
        current_dir = current_dir.parent
    return None # Not in an AetherStats project

def _is_in_project_dir() -> bool:
    """
    Checks if the current working directory is inside an AetherStats project.
    """
    return _find_project_root() is not None

def _get_manifest_path(project_root: Path) -> Path:
    """Returns the path to the project's manifest file."""
    return project_root / AETHERSTATS_DIR_NAME / MANIFEST_FILE_NAME

def _load_manifest(project_root: Path) -> List[dict]:
    """Loads the project manifest, creating an empty one if it doesn't exist."""
    manifest_path = _get_manifest_path(project_root)
    if not manifest_path.exists():
        return []
    try:
        with open(manifest_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        console.print(f"[bold red]Warning:[/bold red] Manifest file '{manifest_path}' is corrupted. Starting with empty manifest.")
        return []

def _save_manifest(project_root: Path, manifest_data: List[dict]) -> None:
    """Saves the project manifest."""
    manifest_path = _get_manifest_path(project_root)
    manifest_path.parent.mkdir(parents=True, exist_ok=True) # Ensure .aetherstats dir exists
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=4)

def _get_log_file_path(project_root: Path) -> Path:
    """Returns the full path to the logs.txt file."""
    return project_root / AETHERSTATS_DIR_NAME / LOG_FILE_NAME

def _log_interaction(
    project_root: Path,
    action_type: str,
    cli_command_args: List[str], # The arguments directly from sys.argv[1:] or constructed for replay
    agent_output: Optional[Any] = None, # The output model from an agent call
    file_saved_path: Optional[Path] = None, # Path of any file created/modified by the action
    message: Optional[str] = None, # A general message for the log entry
    file_content_snapshot: Optional[Dict[str, str]] = None # Restored: Optional dictionary for file content snapshots
):
    """
    Logs the command, action type, any agent output, and any saved file paths as a JSON object per line.
    This log is designed to be replayable.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "action_type": action_type,
        "cli_command_args": cli_command_args,
        "message": message,
        "agent_output": agent_output.model_dump() if hasattr(agent_output, 'model_dump') else None, # Use model_dump for Pydantic models
        "file_saved_path": str(file_saved_path) if file_saved_path else None,
        "file_content_snapshot": file_content_snapshot # Restored: Include file content snapshot
    }
    log_file_path = _get_log_file_path(project_root)
    try:
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + "\n")
        console.print(f"[dim]Logged action '{action_type}' to {log_file_path}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error logging interaction: {e}[/bold red]")

def _get_file_summary_for_ai(file_path: Path) -> str:
    """
    Generates a text summary of a file for processing by AetherStats' intelligent features.
    Handles basic text files (CSV, TXT, MD, PY, JSON) by reading first few lines.
    For other types, provides basic info.
    """
    try:
        if file_path.suffix.lower() in ['.csv', '.txt', '.md', '.py', '.json']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [f.readline() for _ in range(5)] # Read first 5 lines
                content_sample = "".join(lines).strip()
            
            summary = f"File Type: {file_path.suffix.upper()} Text File\n"
            summary += f"File Name: {file_path.name}\n"
            summary += f"Size: {file_path.stat().st_size / 1024:.2f} KB\n"
            if file_path.suffix.lower() == '.csv':
                # Try to extract headers for CSV
                headers = content_sample.split('\n')[0].strip()
                summary += f"CSV Headers: {headers}\n"
                summary += f"First few lines:\n{content_sample}\n"
            else:
                summary += f"Content Sample:\n{content_sample}\n"
            return summary
        else:
            # For binary or unknown files
            return (
                f"File Type: Binary/Unknown ({file_path.suffix.upper()})\n"
                f"File Name: {file_path.name}\n"
                f"Size: {file_path.stat().st_size / 1024:.2f} KB\n"
                "Content cannot be directly read for analysis. Please provide a manual description."
            )
    except Exception as e:
        return f"Could not generate summary for {file_path.name}: {e}"

def _get_file_content_for_log(file_path: Path) -> Optional[str]:
    """
    Reads the content of a text file for logging.
    Returns None if the file is too large or not a readable text file.
    """
    MAX_LOG_FILE_SIZE_KB = 500 # Max 500KB to log file content
    if file_path.stat().st_size > MAX_LOG_FILE_SIZE_KB * 1024:
        console.print(f"[bold yellow]Warning:[/bold yellow] File '{file_path.name}' is too large ({file_path.stat().st_size / 1024:.2f} KB) to log its full content. Skipping.", style="bold yellow")
        return None
    
    try:
        # Attempt to read as UTF-8 text
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except UnicodeDecodeError:
        console.print(f"[bold yellow]Warning:[/bold yellow] File '{file_path.name}' is not a readable text file. Skipping content logging.", style="bold yellow")
        return None
    except Exception as e:
        console.print(f"[bold red]Error reading file '{file_path.name}' for logging: {e}[/bold red]", style="bold red")
        return None


def _run_uv_command(cwd: Path, args: List[str]) -> bool:
    """Helper to run uv commands with Rich status."""
    command = ["uv"] + args
    try:
        with console.status(f"[bold blue]Running uv command: {' '.join(command)}[/bold blue]"):
            result = subprocess.run(
                command,
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "VIRTUAL_ENV_PROMPT": f"({cwd.name})"} # Set prompt for uv venv
            )
            console.print(f"[green]uv output:[/green]\n[dim]{result.stdout}[/dim]")
            if result.stderr:
                console.print(f"[yellow]uv warnings/errors:[/yellow]\n[dim]{result.stderr}[/dim]")
            return True
    except FileNotFoundError:
        console.print("[bold red]Error: 'uv' command not found.[/bold red]")
        console.print("Please install uv: [cyan]pip install uv[/cyan] or [cyan]curl -LsSf https://astral.sh/uv/install.sh | sh[/cyan]")
        return False
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error running uv command: {e}[/bold red]")
        console.print(f"[red]STDOUT:[/red]\n[dim]{e.stdout}[/dim]")
        console.print(f"[red]STDERR:[/red]\n[dim]{e.stderr}[/dim]")
        return False
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred while running uv: {e}[/bold red]")
        return False

def _run_git_command(cwd: Path, args: List[str]) -> subprocess.CompletedProcess:
    """Helper to run git commands in the specified directory."""
    command = ["git"] + args
    
    with console.status(f"[bold blue]Running git command: {' '.join(command)}[/bold blue]"):
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                check=True,  # Raise CalledProcessError for non-zero exit codes
                capture_output=True,
                text=True,   # Decode stdout/stderr as text
                encoding='utf-8' # Explicitly set encoding for consistent output
            )
            return result
        except FileNotFoundError:
            console.print("[bold red]Error: Git command not found. Please ensure Git is installed and in your PATH.[/bold red]")
            raise # Re-raise to indicate critical failure
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error running git command: {e}[/bold red]")
            console.print(f"[red]STDOUT:[/red]\n[dim]{e.stdout}[/dim]")
            console.print(f"[red]STDERR:[/red]\n[dim]{e.stderr}[/dim]")
            raise # Re-raise to allow upstream handling


# --- Component Templates and Mappings ---
_COMPONENT_TYPES = {
    "script": {
        "dir": "scripts",
        "extension": ".py",
        "template": "#!/usr/bin/env python\n# AetherStats Generated Script\n\nimport pandas as pd\n\ndef main():\n    # Your analysis code here\n    pass\n\nif __name__ == '__main__':\n    main()\n"
    },
    "notebook": {
        "dir": "notebooks",
        "extension": ".ipynb",
        "template": """{
  "cells": [
    {
      "cell_type": "code",
      "execution_count": null,
      "metadata": {},
      "outputs": [],
      "source": [
        "# AetherStats Generated Jupyter Notebook"
      ]
    }
  ],
  "metadata": {
    "kernelspec": {
      "display_name": "Python 3",
      "language": "python",
      "name": "python3"
    },
    "language_info": {
      "codemirror_mode": {
        "name": "ipython",
        "version": 3
      },
      "file_extension": ".py",
      "mimetype": "text/x-python",
      "name": "python",
      "nbconvert_exporter": "python",
      "pygments_lexer": "ipython3",
      "version": ""
    }
  },
  "nbformat": 4,
  "nbformat_minor": 4
}
"""
    },
    "report": {
        "dir": "reports",
        "extension": ".md",
        "template": "# AetherStats Report: {name_title}\n\n## Overview\n\nThis report summarizes the findings for the '{name}' analysis.\n\n## Data Used\n\n## Methodology\n\n## Results\n\n## Conclusion\n\n---\n*Generated by AetherStats on {current_time_str}.*\n"
    },
    "task": {
        "dir": "metadata/tasks",
        "extension": ".md",
        "template": "# Task: {name_title}\n\n- **Status:** [ ] To Do\n- **Created:** {current_time_str}\n- **Assigned To:** \n\n## Description\n\nWrite a detailed description of the task here.\n\n## Steps\n\n- [ ] Step 1\n- [ ] Step 2\n\n"
    }
}

# Define valid data types for registration
_REGISTER_DATA_TYPES = ["raw_data", "processed_data", "model", "report", "script_output", "other"]


# --- Project Management Commands ---

@app.callback()
def main_callback(ctx: typer.Context):
    """
    Initializes the project root before any command runs.
    """
    global PROJECT_ROOT # Declare global to modify the module-level variable
    # Removed 'reproduce' from this check
    if ctx.invoked_subcommand != "init":
        PROJECT_ROOT = _find_project_root()
        if PROJECT_ROOT is None:
            console.print("Error: Not within an AetherStats project. Please run '[cyan]aetherstats init <project_name>[/cyan]' first.")
            raise typer.Exit(code=1)

@app.command(
    "init",
    help="Initializes a new AetherStats project with a standardized directory structure, Git, and uv virtual environment."
)
def init_project(
    project_name: str = typer.Argument(
        ...,
        help="The name of the new AetherStats project. A directory with this name will be created."
    ),
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Overwrite existing project directory if it exists. WARNING: This will delete existing files!"
    ),
    no_git: bool = typer.Option(
        False,
        "--no-git",
        help="Do not initialize a Git repository in the new project."
    ),
    no_uv: bool = typer.Option(
        False,
        "--no-uv",
        help="Do not initialize a 'uv' virtual environment in the new project."
    )
) -> None:
    """
    Initializes a new AetherStats project.

    This command creates a new directory with the given project_name and
    sets up a standardized folder structure for data, scripts, reports, etc.
    It also creates a hidden '.aetherstats' directory to mark the project root.
     optionally initializes a Git repository and a uv virtual environment.
    """
    global PROJECT_ROOT # Add global declaration here as well, since init can set it.
    project_path = Path.cwd() / project_name

    if project_path.exists():
        if force:
            if not Confirm.ask(
                f"[bold yellow]The directory '{project_name}' already exists.[/bold yellow] "
                "Are you sure you want to [bold red]delete its contents[/bold red] and re-initialize?",
                default=False, console=console
            ):
                console.print("[bold red]Aborting initialization.[/bold red]")
                raise typer.Exit(code=1)
            try:
                with console.status(f"[bold blue]Clearing existing directory '{project_name}'...[/bold blue]"):
                    shutil.rmtree(project_path)
                console.print(f"[bold green]Existing directory '{project_name}' cleared.[/bold green]")
            except OSError as e:
                console.print(f"[bold red]Error: Could not remove existing directory '{project_name}': {e}[/bold red]", highlight=False)
                raise typer.Exit(code=1)
        else:
            console.print(
                f"[bold red]Error: Directory '{project_name}' already exists. "
                "Use --force to overwrite.[/bold red]", highlight=False
            )
            raise typer.Exit(code=1)

    try:
        with Live(Spinner("dots", text=Text("Initializing AetherStats project...", style="bold cyan")),
                             transient=True, console=console) as live:
            
            # Create main project directory
            project_path.mkdir(parents=True, exist_ok=False)
            live.console.print(f"[bold green]Created project directory:[/bold green] {project_path}")

            # Define the subdirectories
            subdirectories = [
                "data/raw",
                "data/processed",
                "notebooks",
                "scripts",
                "reports",
                "models",
                "metadata",
                "metadata/tasks",
                "config",
                AETHERSTATS_DIR_NAME # Hidden directory to mark the project root
            ]

            # Create subdirectories
            for subdir in subdirectories:
                (project_path / subdir).mkdir(parents=True, exist_ok=True)
                live.console.print(f"[green]Created directory:[/green] {project_path / subdir}")

            # Define files to create
            current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")

            readme_content = f"""# {project_name.replace('_', ' ').title()} AetherStats Project

An AetherStats project for: **{project_name.replace('_', ' ').title()}**.

This project provides a standardized structure for your statistical analyses.

## Directory Structure:
- `data/raw/`: Original, immutable datasets.
- `data/processed/`: Cleaned, transformed, or derived datasets.
- `notebooks/`: Jupyter notebooks or interactive exploration files.
- `scripts/`: Production-ready scripts for data processing, analysis, and modeling.
- `reports/`: Generated reports, visualizations, presentations, and final documents.
- `models/`: Saved trained statistical models.
- `metadata/`: Project-specific configuration, task lists, or other metadata files.
- `metadata/tasks/`: Markdown files for individual tasks.
- `config/`: Project-specific configuration files.
- `.{AETHERSTATS_DIR_NAME}/`: Internal AetherStats project markers and configurations (do not modify manually).
- `.venv/`: [bold green]uv[/bold green] virtual environment (if initialized).

## Getting Started:
1. Navigate into the project directory: [bold cyan]cd {project_name}[/cyan]
2. [bold green]If using uv:[/bold green] Activate the environment: `source .venv/bin/activate` (Linux/macOS) or `.venv\\Scripts\\activate` (Windows PowerShell).
3. Install dependencies: `aetherstats install` (or `uv pip install -r requirements.txt`)
4. Use AetherStats commands to manage your workflow, e.g., `aetherstats register data/raw/my_dataset.csv`.
5. Create new components: `aetherstats create script my_analysis`

---
*Generated by AetherStats at {current_time_str}.*
"""

            gitignore_content = f"""
# AetherStats specific ignores
/{AETHERSTATS_DIR_NAME}/
/models/
/data/processed/ # Often large and reproducible from raw + scripts
/reports/*.pdf   # Generated PDFs
/reports/*.html  # Generated HTML reports

# uv virtual environment
/.venv/

# Common ignores
*.pyc
__pycache__/
.env
.DS_Store
*.ipynb_checkpoints/
"""
            files_to_create = {
                "README.md": readme_content,
                ".gitignore": gitignore_content,
                "requirements.txt": "pandas\nnumpy\nscipy\nmatplotlib\nseaborn\nsklearn\nrich\ntyper\n" # Basic common deps
            }

            # Create files
            for name, content in files_to_create.items():
                file_path = project_path / name
                with open(file_path, "w") as f:
                    f.write(content)
                live.console.print(f"[green]Created file:[/green] {file_path}")
            
            # Create initial manifest file
            _save_manifest(project_path, [])
            live.console.print(f"[green]Created manifest file:[/green] {_get_manifest_path(project_path)}")
            # Create initial log file
            (_get_log_file_path(project_path)).touch()
            live.console.print(f"[green]Created log file:[/green] {_get_log_file_path(project_path)}")


        # Initialize Git repository
        if not no_git:
            try:
                # Change directory to the new project root before initializing Git
                original_cwd = Path.cwd() # Save original cwd
                os.chdir(project_path)
                
                # Use the _run_git_command helper here
                _run_git_command(project_path, ["init"])
                console.print("[bold blue]Initialized empty Git repository.[/bold blue]")

                _run_git_command(project_path, ["add", "."])
                _run_git_command(project_path, ["commit", "-m", "Initial AetherStats project setup"])
                console.print("[bold blue]Performed initial Git commit.[/bold blue]")
                
            except Exception as e: # Catch any exception from _run_git_command
                console.print(f"[bold yellow]Warning: Git initialization failed: {e}[/bold yellow]", highlight=False)
                console.print("[bold yellow]Please ensure Git is installed and configured correctly.[/bold yellow]")
            finally:
                # Change back to the original directory
                os.chdir(original_cwd)
        
        # Initialize uv virtual environment
        if not no_uv:
            console.print("[dim]---[/dim]")
            console.print("[bold blue]Setting up uv virtual environment...[/bold blue]")
            
            original_cwd = Path.cwd()
            os.chdir(project_path)
            
            # Check if .venv already exists (shouldn't happen on new init)
            if not (project_path / ".venv").is_dir():
                if _run_uv_command(project_path, ["venv", ".venv"]):
                    console.print("[bold green]uv virtual environment created at ./.venv[/bold green]")
                else:
                    console.print("[bold red]Failed to create uv virtual environment.[/bold red]")
                    os.chdir(original_cwd)
                    raise typer.Exit(code=1)
            else:
                console.print("[dim]uv virtual environment already exists. Skipping creation.[/dim]")

            # Always attempt to install dependencies if requirements.txt exists
            if (project_path / "requirements.txt").exists():
                if _run_uv_command(project_path, ["pip", "install", "-r", "requirements.txt"]):
                    console.print("[bold green]Initial dependencies installed via uv.[/bold green]")
                else:
                    console.print("[bold red]Failed to install initial dependencies with uv.[/bold red]")
            else:
                console.print("[dim]No requirements.txt found. Skipping initial dependency install.[/dim]")

            os.chdir(original_cwd)

        console.print(
            Panel(
                f"[bold green]Successfully initialized AetherStats project '{project_name}'![/bold green]\n\n"
                f"Your project is located at: [cyan]{project_path}[/cyan]\n"
                "Navigate into your project directory using: [bold cyan]cd {project_name}[/cyan]",
                title="[bold green]Project Initialized[/bold green]",
                border_style="green"
            )
        )
        if not no_git:
            console.print("[bold blue]A Git repository has been initialized. Don't forget to commit your changes![/bold blue]")
        
        console.print("[bold yellow]Remember to activate your virtual environment for local development:[/bold yellow]")
        console.print(f"  [cyan]cd {project_name}[/cyan]")
        console.print("  [cyan]source .venv/bin/activate[/cyan] (Linux/macOS)")
        console.print("  [cyan].venv\\Scripts\\activate[/cyan] (Windows PowerShell)")

        # Log the init action *after* successful initialization
        # Set PROJECT_ROOT here as well, for commands that might run immediately after init
        PROJECT_ROOT = project_path
        _log_interaction(
            project_path,
            "init",
            cli_command_args=["init", project_name, "--force"] if force else ["init", project_name],
            message=f"Project '{project_name}' initialized."
        )

    except OSError as e:
        console.print(f"[bold red]Error initializing project '{project_name}': {e}[/bold red]", highlight=False)
        # Clean up partially created directory if an error occurred
        if project_path.exists() and not force:
            try:
                shutil.rmtree(project_path)
                console.print(f"[bold red]Partially created directory '{project_name}' removed due to error.[/bold red]", highlight=False)
            except OSError as cleanup_e:
                console.print(f"[bold red]Error during cleanup: {cleanup_e}[/bold red]", highlight=False)
        raise typer.Exit(code=1)


@app.command(
    "create",
    help="Creates a new component (script, notebook, report, task) within the current AetherStats project."
)
def create_component(
    component_type: str = typer.Argument(
        ...,
        help=f"The type of component to create. Choose from: {', '.join(_COMPONENT_TYPES.keys())}"
    ),
    name: str = typer.Argument(
        ...,
        help="The name of the component (e.g., 'data_cleaning' or 'quarterly_report')."
    )
) -> None:
    """
    Creates a new project component like a script, notebook, report, or task.
    """
    # project_root is guaranteed to be set by main_callback
    project_root = PROJECT_ROOT

    # 2. Validate component type
    component_info = _COMPONENT_TYPES.get(component_type.lower())
    if not component_info:
        console.print(
            f"[bold red]Error:[/bold red] Invalid component type '[bold yellow]{component_type}[/bold yellow]'.\n"
            f"Valid types are: [bold cyan]{', '.join(_COMPONENT_TYPES.keys())}[/cyan]."
        )
        raise typer.Exit(code=1)

    target_dir = project_root / component_info["dir"]
    file_name = f"{name}{component_info['extension']}"
    file_path = target_dir / file_name

    # 3. Check if component already exists
    if file_path.exists():
        console.print(
            f"[bold yellow]Warning:[/bold yellow] A {component_type} named '[bold cyan]{name}[/bold cyan]' already exists at:\n"
            f"{file_path}\n"
            "Consider choosing a different name or manually deleting the existing file if you wish to replace it."
        )
        raise typer.Exit(code=1)

    # 4. Create the component
    try:
        with console.status(f"[bold blue]Creating {component_type} '{name}'...[/bold blue]"):
            # Ensure the target directory exists (it should from init, but good to be safe)
            target_dir.mkdir(parents=True, exist_ok=True)

            template_content = component_info["template"]
            current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
            name_title = name.replace('_', ' ').title()

            # Format template with dynamic values
            formatted_content = template_content.format(
                name=name,
                name_title=name_title,
                current_time_str=current_time_str
            )

            with open(file_path, "w") as f:
                f.write(formatted_content)
            
        console.print(
            f"[bold green]Successfully created {component_type} '[bold cyan]{name}[/bold cyan]' at:[/bold green] {file_path}"
        )
        console.print(f"You can now edit this file in your favorite editor.")

        # Log the create action
        _log_interaction(
            project_root,
            "create",
            cli_command_args=["create", component_type, name],
            file_saved_path=file_path.relative_to(project_root),
            message=f"Created {component_type} '{name}'."
        )

    except OSError as e:
        console.print(f"[bold red]Error creating {component_type} '{name}': {e}[/bold red]", highlight=False)
        raise typer.Exit(code=1)


@app.command(
    "register",
    help="Registers a file (data, model, report, etc.) within the current AetherStats project's manifest."
)
def register_file(
    file_path: str = typer.Argument(
        ...,
        help="The path to the file to register, relative to the project root."
    ),
    data_type: str = typer.Option(
        ...,
        "--type", "-t",
        help=f"The type of data being registered. Choose from: {', '.join(_REGISTER_DATA_TYPES)}"
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description", "-d",
        help="A brief description of the file's content or purpose."
    ),
    auto_describe: bool = typer.Option(
        False,
        "--auto-describe",
        help="Use AetherStats' intelligent features to automatically generate a description for the file."
    )
) -> None:
    """
    Registers a file (data, model, report, etc.) within the current AetherStats project.
    Metadata about the file is stored in a manifest.json file.
    """
    # project_root is guaranteed to be set by main_callback
    project_root = PROJECT_ROOT

    # 2. Validate file path
    absolute_file_path = Path.cwd() / file_path
    if not absolute_file_path.exists():
        console.print(f"[bold red]Error:[/bold red] File not found: '[bold yellow]{file_path}[/bold yellow]'. Please provide a valid path.", highlight=False)
        raise typer.Exit(code=1)
    
    # 3. Validate data type
    if data_type.lower() not in _REGISTER_DATA_TYPES:
        console.print(
            f"[bold red]Error:[/bold red] Invalid data type '[bold yellow]{data_type}[/bold yellow]'.\n"
            f"Valid types are: [bold cyan]{', '.join(_REGISTER_DATA_TYPES)}[/cyan]."
        )
        raise typer.Exit(code=1)

    # 4. Handle auto-description with intelligent features
    if auto_describe:
        if description:
            console.print("[bold yellow]Warning:[/bold yellow] Both --description and --auto-describe were provided. Using auto-generated description.", highlight=False)
            
        file_summary_for_ai = _get_file_summary_for_ai(absolute_file_path)
        
        with console.status("[bold magenta]AetherStats is generating file description...[/bold magenta]"):
            try:
                agent_response = register_file_auto_describe_agent.run_sync(
                    f"Please give a useful and concise explanation and report about the data described below:\n\n{file_summary_for_ai}"
                )
                auto_desc_output: RegisterFileAutoDescribeOutput = agent_response.output
                
                description = (
                    f"Overview: {auto_desc_output.overview}\n"
                    f"Key Variables: {', '.join([f"{v['name']} ({v['description']})" for v in auto_desc_output.key_variables])}\n"
                    f"Observations: {'; '.join(auto_desc_output.observations)}\n"
                    f"Potential Issues: {'; '.join(auto_desc_output.potential_issues)}\n"
                    f"Suggested Next Steps: {'; '.join(auto_desc_output.suggested_next_steps)}"
                )
                console.print("[bold green]Auto-description generated successfully![/bold green]")
            except Exception as e:
                console.print(f"[bold red]Error generating auto-description: {e}[/bold red]")
                console.print("[bold yellow]Proceeding with empty description.[/bold yellow]")
                description = None
    
    # Load existing manifest
    manifest_data = _load_manifest(project_root)

    # Check if the file is already registered and update or add
    file_registered = False
    for entry in manifest_data:
        if entry["path"] == str(absolute_file_path):
            if not Confirm.ask(
                f"[bold yellow]File '{file_path}' is already registered.[/bold yellow] Do you want to update its entry?",
                default=True, console=console
            ):
                console.print("[bold red]Aborting registration update.[/bold red]")
                raise typer.Exit(code=1)
            
            # Update existing entry
            entry["type"] = data_type
            entry["description"] = description if description is not None else entry.get("description", "No description provided.")
            entry["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry["size_bytes"] = absolute_file_path.stat().st_size
            file_registered = True
            console.print(f"[bold green]Updated manifest entry for:[/bold green] {absolute_file_path}")
            break

    if not file_registered:
        # Add new entry
        new_entry = {
            "path": str(absolute_file_path),
            "type": data_type,
            "description": description if description is not None else "No description provided.",
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "size_bytes": absolute_file_path.stat().st_size
        }
        manifest_data.append(new_entry)
        console.print(f"[bold green]Registered new file:[/bold green] '{absolute_file_path}'")

    _save_manifest(project_root, manifest_data)
    
    # Log the register action
    _log_interaction(
        project_root,
        "register",
        cli_command_args=[
            "register", file_path, "--type", data_type, 
            "--description", description if description else "Auto-described" if auto_describe else "No description"
        ] + (["--auto-describe"] if auto_describe else []), # Dynamically add auto_describe flag
        message=f"Registered file '{file_path}' as '{data_type}'."
    )

    console.print("[bold cyan]Manifest updated successfully.[/bold cyan]")


@app.command(
    "list",
    help="Lists registered files, components, or logs within the project."
)
def list_content(
    content_type: Annotated[
        str, typer.Argument(help="The type of content to list: 'files', 'components', or 'logs'.")
    ]
) -> None:
    """
    Lists various types of content within the AetherStats project.
    """
    project_root = PROJECT_ROOT

    if content_type == "files":
        manifest_data = _load_manifest(project_root)
        if not manifest_data:
            console.print("[bold yellow]No files registered in the manifest.[/bold yellow]")
            return

        table = Table(title="[bold blue]Registered Files[/bold blue]", show_lines=True)
        table.add_column("[cyan]Path[/cyan]", style="dim", no_wrap=False)
        table.add_column("[cyan]Type[/cyan]", style="green")
        table.add_column("[cyan]Description[/cyan]", style="white")
        table.add_column("[cyan]Last Modified[/cyan]", style="magenta")
        table.add_column("[cyan]Size (KB)[/cyan]", style="yellow")

        for entry in manifest_data:
            path = entry.get("path", "N/A")
            data_type = entry.get("type", "N/A")
            description = entry.get("description", "No description.")
            last_modified = entry.get("last_modified", "N/A")
            size_bytes = entry.get("size_bytes")
            size_kb = f"{size_bytes / 1024:.2f}" if size_bytes is not None else "N/A"
            table.add_row(path, data_type, description, last_modified, size_kb)
        console.print(table)

    elif content_type == "components":
        table = Table(title="[bold blue]Available Component Types[/bold blue]", show_lines=True)
        table.add_column("[cyan]Type[/cyan]", style="green")
        table.add_column("[cyan]Directory[/cyan]", style="dim")
        table.add_column("[cyan]Extension[/cyan]", style="magenta")
        
        for comp_type, info in _COMPONENT_TYPES.items():
            table.add_row(comp_type, info["dir"], info["extension"])
        console.print(table)
        
        console.print("\n[bold blue]Existing Project Components:[/bold blue]")
        component_table = Table(show_lines=True)
        component_table.add_column("[cyan]Type[/cyan]", style="green")
        component_table.add_column("[cyan]Name[/cyan]", style="white")
        component_table.add_column("[cyan]Path[/cyan]", style="dim")

        found_any = False
        for comp_type, info in _COMPONENT_TYPES.items():
            target_dir = project_root / info["dir"]
            if target_dir.exists():
                for f in target_dir.iterdir():
                    if f.is_file() and f.suffix == info["extension"]:
                        component_table.add_row(comp_type, f.stem, str(f.relative_to(project_root)))
                        found_any = True
        
        if found_any:
            console.print(component_table)
        else:
            console.print("[bold yellow]No components found in project directories.[/bold yellow]")


    elif content_type == "logs":
        log_file_path = _get_log_file_path(project_root)
        if not log_file_path.exists() or log_file_path.stat().st_size == 0:
            console.print("[bold yellow]No log entries found.[/bold yellow]")
            return

        table = Table(title="[bold blue]AetherStats Interaction Log[/bold blue]", show_lines=True)
        table.add_column("[cyan]Timestamp[/cyan]", style="magenta")
        table.add_column("[cyan]Action Type[/cyan]", style="green")
        table.add_column("[cyan]CLI Command[/cyan]", style="white", no_wrap=False)
        table.add_column("[cyan]Message[/cyan]", style="dim")
        table.add_column("[cyan]File Saved[/cyan]", style="yellow")
        table.add_column("[cyan]Content Snapshot[/cyan]", style="cyan", no_wrap=False)

        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        timestamp = entry.get("timestamp", "N/A")
                        action_type = entry.get("action_type", "N/A")
                        cli_command = "aetherstats " + " ".join(entry.get("cli_command_args", []))
                        message = entry.get("message", "N/A")
                        file_saved_path = entry.get("file_saved_path", "N/A")
                        
                        # Handle content snapshot
                        content_snapshot = entry.get("file_content_snapshot")
                        content_summary = ""
                        if content_snapshot:
                            if isinstance(content_snapshot, dict):
                                # If it's a dict, it contains file paths as keys and content as values
                                content_items = []
                                for p, c in content_snapshot.items():
                                    content_items.append(f"• {p}: {c[:50]}..." if c else f"• {p}: [empty]")
                                content_summary = "\n".join(content_items)
                                if len(content_snapshot) > 1:
                                    content_summary = f"[multiple files]\n" + content_summary
                            else: # Should not happen if always dict, but for safety
                                content_summary = str(content_snapshot)[:100] + "..." if content_snapshot else "N/A"
                        else:
                            content_summary = "N/A"
                        
                        table.add_row(timestamp, action_type, cli_command, message, file_saved_path, content_summary)
                    except json.JSONDecodeError:
                        console.print(f"[bold red]Warning: Malformed log entry skipped:[/bold red] {line.strip()}", style="bold red")
            console.print(table)
        except Exception as e:
            console.print(f"[bold red]Error reading log file: {e}[/bold red]")

    else:
        console.print(f"[bold red]Error:[/bold red] Invalid content type '[bold yellow]{content_type}[/bold yellow]'.\n"
                      f"Valid types are: [bold cyan]'files', 'components', 'logs'[/cyan].")
        raise typer.Exit(code=1)


@app.command(
    "status",
    help="Displays the current status of the AetherStats project, including manifest summary and Git status."
)
def project_status() -> None:
    """
    Displays a summary of the current AetherStats project status.
    """
    project_root = PROJECT_ROOT

    console.print(Panel(f"[bold green]AetherStats Project Status: {project_root.name}[/bold green]", border_style="green"))

    # Manifest Summary
    manifest_data = _load_manifest(project_root)
    console.print(f"[bold blue]Manifest Summary:[/bold blue]")
    if manifest_data:
        console.print(f"  [green]Total Registered Files:[/green] {len(manifest_data)}")
        
        # Count by type
        type_counts = {}
        for entry in manifest_data:
            file_type = entry.get("type", "unknown")
            type_counts[file_type] = type_counts.get(file_type, 0) + 1
        
        for file_type, count in type_counts.items():
            console.print(f"  - [yellow]{file_type.replace('_', ' ').title()}:[/yellow] {count}")
    else:
        console.print("  [bold yellow]No files currently registered in the manifest.[/bold yellow]")

    # Git Status
    console.print("\n[bold blue]Git Status:[/bold blue]")
    try:
        # Check if Git repo exists
        git_dir = project_root / ".git"
        if not git_dir.is_dir():
            console.print("  [dim]Not a Git repository. Skipping Git status.[/dim]")
            return # Exit early if no git repo

        # Run git status command
        git_status_result = _run_git_command(project_root, ["status", "--porcelain"])
        status_output = git_status_result.stdout.strip()

        if status_output:
            console.print("  [bold yellow]Uncommitted changes detected by Git:[/bold yellow]")
            console.print(Text(status_output, style="dim"))
        else:
            console.print("  [bold green]Git working tree clean.[/bold green]")

        # Get latest commit info
        try:
            git_log_result = _run_git_command(project_root, ["log", "-1", "--pretty=format:%h %s (%cr)"])
            latest_commit = git_log_result.stdout.strip()
            console.print(f"  [bold green]Latest Git Commit:[/bold green] {latest_commit}")
        except subprocess.CalledProcessError: # This will catch if there are no commits yet
            console.print("  [dim]No Git commits yet.[/dim]")

    except Exception as e: # Catch any error from _run_git_command (e.g., git not installed)
        console.print(f"  [bold red]Error checking Git status: {e}[/bold red]")


@app.command(
    "commit",
    help="Performs a Git commit of changes and saves the content of registered and relevant project files into the logs.txt file as a snapshot."
)
def commit_project(
    message: Annotated[
        str, typer.Option("--message", "-m", help="A message describing this commit and content snapshot.")
    ] = "AetherStats automated commit"
) -> None:
    """
    Performs a Git commit of current changes and also saves a snapshot of the current content
    of all registered files (and potentially others) into the project's logs.txt file.
    """
    project_root = PROJECT_ROOT

    console.print(f"[bold blue]Starting AetherStats commit process with message: '{message}'...[/bold blue]")

    # --- Part 1: Gather file content for logs.txt snapshot ---
    files_to_snapshot: Dict[str, str] = {}
    
    console.print("[bold blue]Gathering file contents for content snapshot...[/bold blue]")
    with console.status("[bold magenta]Reading file contents...[/bold magenta]"):
        # 1. Snapshot contents of registered files
        manifest_data = _load_manifest(project_root)
        if not manifest_data:
            console.print("[bold yellow]No files registered in the manifest. Consider registering important files with 'aetherstats register'.[/bold yellow]")
        else:
            for entry in manifest_data:
                relative_path_str = entry["path"]
                absolute_path = project_root / relative_path_str
                if absolute_path.is_file():
                    content = _get_file_content_for_log(absolute_path)
                    if content is not None:
                        files_to_snapshot[relative_path_str] = content
                else:
                    console.print(f"[bold yellow]Warning:[/bold yellow] Registered file '{relative_path_str}' not found. Skipping snapshot.", style="bold yellow")

        # 2. Snapshot contents of other important project files (e.g., all .py scripts, all .md reports)
        # You can customize this list to include other file types/locations you want to always snapshot.
        common_project_dirs_to_snapshot = [
            "scripts",
            "reports",
            "notebooks",
            "config",
            # Add other directories if needed, e.g., "data/processed" if you want to snapshot processed data content
        ]
        
        for dir_name in common_project_dirs_to_snapshot:
            current_dir = project_root / dir_name
            if current_dir.is_dir():
                for file_path_in_dir in current_dir.rglob("*"): # Recursive glob for all files/dirs
                    if file_path_in_dir.is_file() and file_path_in_dir.suffix.lower() in ['.py', '.md', '.json', '.txt', '.csv', '.ipynb']: # Only snapshot text-based files
                        relative_file_path = str(file_path_in_dir.relative_to(project_root))
                        if relative_file_path not in files_to_snapshot: # Avoid duplicating if already from manifest
                            content = _get_file_content_for_log(file_path_in_dir)
                            if content is not None:
                                files_to_snapshot[relative_file_path] = content

    if not files_to_snapshot:
        console.print("[bold yellow]No readable files found for content snapshot.[/bold yellow]")
        # We can still proceed with Git commit if there are changes.

    # --- Part 2: Perform Git Commit ---
    console.print("\n[bold blue]Performing Git commit...[/bold blue]")
    try:
        # Check if Git repo exists
        git_dir = project_root / ".git"
        if not git_dir.is_dir():
            console.print("[bold yellow]Warning:[/bold yellow] Not a Git repository. Skipping Git commit. Please run 'aetherstats init --no-uv' if you want Git version control.", highlight=False)
            # If no Git repo, we still log the content snapshot, but exit the Git part
            is_git_commit_successful = False
        else:
            # Stage all changes in the project directory
            _run_git_command(project_root, ["add", "."])
            console.print("[bold green]All changes staged for Git commit.[/bold green]")

            # Perform the commit
            _run_git_command(project_root, ["commit", "-m", message])
            console.print(f"[bold green]Git commit successful with message: '{message}'.[/bold green]")
            is_git_commit_successful = True

    except Exception as e:
        console.print(f"[bold red]Error during Git commit: {e}[/bold red]", highlight=False)
        console.print("[bold yellow]Git commit failed. Proceeding to log content snapshot (if any).[/bold yellow]")
        is_git_commit_successful = False

    # --- Part 3: Log interaction to logs.txt (including file content snapshot) ---
    commit_status_message = "Git commit successful." if is_git_commit_successful else "Git commit failed or skipped."
    log_message = f"Commit completed: '{message}'. {commit_status_message} Snapshotted {len(files_to_snapshot)} files."

    _log_interaction(
        project_root,
        "commit", # Action type indicating a full commit (Git + content snapshot)
        cli_command_args=["commit", "-m", message],
        message=log_message,
        file_content_snapshot=files_to_snapshot # Pass the dictionary of file contents
    )

    console.print(f"[bold green]AetherStats commit process finished.[/bold green]")
    console.print(f"[dim]Detailed content snapshot logged to logs.txt.[/dim]")


## New AI-Powered Commands

@app.command(
    "explore",
    help="Uses AI to provide an initial overview and insights for a registered data file."
)
def explore_data(
    file_path: Annotated[
        str, typer.Argument(help="The path to the data file to explore, relative to the project root.")
    ]
) -> None:
    """
    Explores a registered data file using an AI agent, providing a summary, key observations,
    and suggested next steps.
    """
    project_root = PROJECT_ROOT
    absolute_file_path = Path.cwd() / file_path

    if not absolute_file_path.exists():
        console.print(f"[bold red]Error:[/bold red] File not found: '[bold yellow]{file_path}[/bold yellow]'. Please provide a valid path.", highlight=False)
        raise typer.Exit(code=1)

    try:
        relative_to_project_root = absolute_file_path.relative_to(project_root)
    except ValueError:
        console.print(
            f"[bold red]Error:[/bold red] The file '[bold yellow]{file_path}[/bold yellow]' is not located within the current AetherStats project directory: [cyan]{project_root}[/cyan]",
            highlight=False
        )
        raise typer.Exit(code=1)

    file_summary_for_ai = _get_file_summary_for_ai(absolute_file_path)
    
    console.print(f"[bold magenta]AetherStats is exploring '{relative_to_project_root}'...[/bold magenta]")
    with console.status("[bold magenta]Invoking Aether Insight Agent...[/bold magenta]"):
        try:
            # We provide the file summary along with the registered description from manifest
            manifest_data = _load_manifest(project_root)
            registered_entry = next((entry for entry in manifest_data if entry["path"] == str(relative_to_project_root)), None)
            
            manifest_description = registered_entry.get("description", "No detailed description in manifest.") if registered_entry else "File is not registered or has no description in manifest."

            prompt_content = (
                f"Analyze the following file summary and its associated manifest description:\n\n"
                f"File Summary:\n{file_summary_for_ai}\n\n"
                f"Manifest Description: {manifest_description}\n\n"
                "Provide a concise summary, highlight key observations, point out potential issues, "
                "suggest relevant visualizations, and outline clear next steps for analysis."
            )
            
            agent_response = aether_insight_agent.run_sync(prompt_content)
            insight_output: AetherInsightOutput = agent_response.output

            console.print(Panel(
                f"[bold green]Insights for {relative_to_project_root.name}:[/bold green]\n\n"
                f"[cyan]Summary:[/cyan] {insight_output.summary}\n\n"
                f"[cyan]Key Observations:[/cyan]\n" + "\n".join([f"- {obs}" for obs in insight_output.key_observations]) + "\n\n" +
                f"[cyan]Potential Issues:[/cyan]\n" + "\n".join([f"- {issue}" for issue in insight_output.potential_issues]) + "\n\n" +
                f"[cyan]Suggested Visualizations:[/cyan]\n" + "\n".join([f"- {viz}" for viz in insight_output.suggested_visualizations]) + "\n\n" +
                f"[cyan]Suggested Next Steps:[/cyan]\n" + "\n".join([f"- {step}" for step in insight_output.suggested_next_steps]),
                title="[bold green]AetherStats Explore Result[/bold green]",
                border_style="green"
            ))

            _log_interaction(
                project_root,
                "explore",
                cli_command_args=["explore", file_path],
                agent_output=insight_output,
                message=f"Explored file '{file_path}'."
            )

        except Exception as e:
            console.print(f"[bold red]Error during data exploration: {e}[/bold red]", highlight=False)
            _log_interaction(
                project_root,
                "explore",
                cli_command_args=["explore", file_path],
                message=f"Failed to explore file '{file_path}': {e}"
            )
            raise typer.Exit(code=1)


@app.command(
    "analyze",
    help="Uses AI to answer a specific question about a registered data file."
)
def analyze_data(
    file_path: Annotated[
        str, typer.Argument(help="The path to the data file to analyze, relative to the project root.")
    ],
    question: Annotated[
        str, typer.Option("--question", "-q", help="The question to ask about the data.")
    ]
) -> None:
    """
    Analyzes a registered data file based on a natural language question using an AI agent.
    """
    project_root = PROJECT_ROOT
    absolute_file_path = Path.cwd() / file_path

    if not absolute_file_path.exists():
        console.print(f"[bold red]Error:[/bold red] File not found: '[bold yellow]{file_path}[/bold yellow]'. Please provide a valid path.", highlight=False)
        raise typer.Exit(code=1)

    try:
        relative_to_project_root = absolute_file_path.relative_to(project_root)
    except ValueError:
        console.print(
            f"[bold red]Error:[/bold red] The file '[bold yellow]{file_path}[/bold yellow]' is not located within the current AetherStats project directory: [cyan]{project_root}[/cyan]",
            highlight=False
        )
        raise typer.Exit(code=1)

    file_summary_for_ai = _get_file_summary_for_ai(absolute_file_path)

    console.print(f"[bold magenta]AetherStats is analyzing '{relative_to_project_root}' with your question...[/bold magenta]")
    with console.status("[bold magenta]Invoking Aether Analysis Agent...[/bold magenta]"):
        try:
            # We provide the file summary along with the registered description from manifest
            manifest_data = _load_manifest(project_root)
            registered_entry = next((entry for entry in manifest_data if entry["path"] == str(relative_to_project_root)), None)
            
            manifest_description = registered_entry.get("description", "No detailed description in manifest.") if registered_entry else "File is not registered or has no description in manifest."

            prompt_content = (
                f"Given the following file summary and its manifest description, answer the question:\n\n"
                f"File Summary:\n{file_summary_for_ai}\n\n"
                f"Manifest Description: {manifest_description}\n\n"
                f"Question: {question}\n\n"
                "Provide a clear answer, and if applicable, suggest a Python code snippet using pandas to perform the analysis."
            )

            agent_response = aether_analysis_agent.run_sync(prompt_content)
            analysis_output: AnalysisOutput = agent_response.output

            console.print(Panel(
                f"[bold green]Analysis for {relative_to_project_root.name}:[/bold green]\n\n"
                f"[cyan]Question:[/cyan] {question}\n\n"
                f"[cyan]Answer:[/cyan] {analysis_output.answer}\n\n" +
                (f"[cyan]Suggested Code:[/cyan]\n[dim]{analysis_output.suggested_code}[/dim]" if analysis_output.suggested_code else "[dim]No specific code suggested for this analysis.[/dim]"),
                title="[bold green]AetherStats Analyze Result[/bold green]",
                border_style="green"
            ))

            _log_interaction(
                project_root,
                "analyze",
                cli_command_args=["analyze", file_path, "--question", question],
                agent_output=analysis_output,
                message=f"Analyzed file '{file_path}' with question: '{question}'."
            )

        except Exception as e:
            console.print(f"[bold red]Error during data analysis: {e}[/bold red]", highlight=False)
            _log_interaction(
                project_root,
                "analyze",
                cli_command_args=["analyze", file_path, "--question", question],
                message=f"Failed to analyze file '{file_path}': {e}"
            )
            raise typer.Exit(code=1)


@generate_app.command("code")
def generate_code(
    prompt: Annotated[str, typer.Option(help="Describe the Python code you want to generate (e.g., 'Python code to clean missing values in a pandas DataFrame').")],
    _reproducing: bool = typer.Option(False, "--_reproducing", hidden=True)
):
    """Generate Python code for a data task."""
    # project_root is guaranteed to be set by main_callback
    project_root = PROJECT_ROOT
    file_saved: Optional[Path] = None
    generated_code_output = None

    console.print("[bold yellow]Initiating AetherStats Code Generation...[/bold yellow]")

    try:
        with console.status("[bold magenta]AetherStats is generating code...[/bold magenta]"): # This is console.status, fine.
            agent_response = aether_code_generation_agent.run_sync(code_request_prompt=prompt)
        
        generated_code_output = agent_response.output
        if not isinstance(generated_code_output, CodeGenerationOutput):
            console.print(f"Unexpected output type for generate code: {type(generated_code_output)}")
            raise typer.Exit(code=1)
        
        filename_suggestion = generated_code_output.filename_suggestion
        # Ensure it's a .py file if not specified
        if not filename_suggestion.endswith(".py"):
            filename_suggestion = f"{filename_suggestion.split('.')[0]}.py" # Take name before first dot, add .py

        filename = Path("scripts") / filename_suggestion
        full_path = project_root / filename
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(generated_code_output.code)
        file_saved = filename # Relative path for manifest/log
        
        if not _reproducing:
            console.print(f"Generated code saved to: {full_path}")
            console.print(f"Explanation: {generated_code_output.explanation}")
        else:
            console.print(f"[dim]Re-generated code to: {full_path}[/dim]")
        
        # Suggest installing required packages
        if generated_code_output.required_packages:
            if not _reproducing:
                console.print(f"Required Packages: [bold]{', '.join(generated_code_output.required_packages)}[/bold]")
                console.print(f"You might need to install them: aetherstats install {' '.join(generated_code_output.required_packages)}")
            
            # Update requirements.txt if new packages are suggested
            requirements_path = project_root / "requirements.txt"
            try:
                with open(requirements_path, "a+") as f_req:
                    f_req.seek(0)
                    existing_packages = set(line.strip().split("==")[0] for line in f_req if line.strip() and not line.startswith("#"))
                    new_packages_to_add = [p for p in generated_code_output.required_packages if p.split("==")[0] not in existing_packages]
                    if new_packages_to_add:
                        f_req.write("\n" + "\n".join(new_packages_to_add) + "\n")
                        if not _reproducing: console.print(f"[bold green]Added new packages to requirements.txt:[/bold green] {', '.join(new_packages_to_add)}")
                        else: console.print(f"[dim]Added new packages to requirements.txt: {', '.join(new_packages_to_add)}[/dim]")

                        # If reproducing, also try to install these packages immediately
                        if _reproducing:
                            console.print(f"[bold blue]Installing newly added packages via uv during reproduction...[/bold blue]")
                            if not _run_uv_command(project_root, ["pip", "install"] + new_packages_to_add):
                                console.print("[bold yellow]Warning: Failed to install some packages during reproduction. Manual intervention may be needed.[/bold yellow]")

            except Exception as e:
                console.print(f"[bold yellow]Warning: Could not update requirements.txt: {e}[/bold red]")

        # Log the generate code action
        _log_interaction(project_root, "generate_code", cli_command_args=["generate", "code", "--prompt", prompt], agent_output=generated_code_output, file_saved_path=file_saved, message="Generated Python code.")
    except Exception as e:
        console.print(f"[bold red]Error during code generation: {e}[/bold red]")
        raise typer.Exit(code=1)

@generate_app.command("report")
def generate_report(
    prompt: Annotated[str, typer.Option(help="Describe the content for the Markdown report (e.g., 'A summary report of sales data including key trends and outliers').")],
    _reproducing: bool = typer.Option(False, "--_reproducing", hidden=True)
):
    """Generate a Markdown report."""
    # project_root is guaranteed to be set by main_callback
    project_root = PROJECT_ROOT
    file_saved: Optional[Path] = None
    generated_report_output = None

    console.print("[bold yellow]Initiating AetherStats Report Generation...[/bold yellow]")

    try:
        with console.status("[bold magenta]AetherStats is generating report...[/bold magenta]"): # This is console.status, fine.
            agent_response = aether_report_agent.run_sync(report_prompt_elements=prompt)
        
        generated_report_output = agent_response.output
        if not isinstance(generated_report_output, MarkdownReportOutput):
            console.print(f"Unexpected output type for generate report: {type(generated_report_output)}")
            raise typer.Exit(code=1)
        
        suggested_filename = generated_report_output.title.lower().replace(' ', '_').replace('/', '_').replace('\\', '_')
        if not suggested_filename.endswith(".md"):
            suggested_filename += ".md"
        filename = Path("reports") / suggested_filename
        full_path = project_root / filename
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(generated_report_output.markdown_content)
        file_saved = filename # Relative path for manifest/log
        
        if not _reproducing:
            console.print(f"Generated report saved to: {full_path}")
            console.print(f"Title: [bold]{generated_report_output.title}[/bold]")
            console.print(f"Summary: {generated_report_output.summary}")
        else:
            console.print(f"[dim]Re-generated report to: {full_path}[/dim]")
        
        # Log the generate report action
        _log_interaction(project_root, "generate_report", cli_command_args=["generate", "report", "--prompt", prompt], agent_output=generated_report_output, file_saved_path=file_saved, message="Generated Markdown report.")
    except Exception as e:
        console.print(f"[bold red]Error during report generation: {e}[/bold red]")
        raise typer.Exit(code=1)

@app.command("gen-logs")
def gen_logs_command():
    """Display or verify the contents of the logs.txt file."""
    # project_root is guaranteed to be set by main_callback
    project_root = PROJECT_ROOT
    log_file_path = _get_log_file_path(project_root)
    
    console.print(f"\n--- Contents of {log_file_path} ---")
    try:
        if not log_file_path.exists():
            console.print(f"[bold yellow]No logs.txt found at {log_file_path}. Start interacting with AetherStats to create one.[/bold yellow]")
            return

        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    log_entry = json.loads(line)
                    console.print(f"[{line_num}] [dim]{log_entry.get('timestamp')}[/dim]: [bold]{log_entry.get('cli_command_args', 'N/A')}[/bold] -> Type: [magenta]{log_entry.get('action_type')}[/magenta]")
                    if log_entry.get('file_saved_path'):
                        console.print(f"    Saved: {log_entry.get('file_saved_path')}")
                    if log_entry.get('message'):
                        console.print(f"    Message: [italic]{log_entry.get('message')}[/italic]")
                    # Optionally display a snippet of agent_output if not too long
                    agent_output_summary = str(log_entry.get('agent_output', ''))
                    if len(agent_output_summary) > 100:
                        agent_output_summary = agent_output_summary[:97] + "..."
                    if agent_output_summary and agent_output_summary != 'None':
                        console.print(f"    Agent Output Snippet: [italic]{agent_output_summary}[/italic]")

                except json.JSONDecodeError:
                    console.print(f"[{line_num}] [bold red]Malformed log entry: {line.strip()}[/bold red]")
        console.print("\n--- Log verification complete ---")
    except Exception as e:
        console.print(f"[bold red]Error reading logs.txt: {e}[/bold red]")

if __name__ == "__main__":
    app()