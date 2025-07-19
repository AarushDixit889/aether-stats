# AetherStats CLI: Comprehensive Documentation

AetherStats CLI is your intelligent assistant designed to streamline and enhance statistical workflows. It provides a robust set of commands for project initialization, component creation, data registration, version control, AI-powered analysis, and report generation, empowering statisticians to manage their projects efficiently and ensure reproducibility.

-----

## Table of Contents

1.  Introduction
2.  Key Features
3.  Installation
4.  Global Options
5.  Commands
      * `init`
      * `create`]
      * `register
      * `list`
      * `status`
      * `commit`
      * `explore`
      * `analyze`
      * `gen-logs`
      * `generate`
6.  Usage Examples
7.  Contributing
8.  License

-----

## 1\. Introduction

AetherStats CLI aims to be an indispensable tool for statisticians, offering a unified command-line interface to manage the entire lifecycle of a statistical project. From setting up a new environment to performing AI-assisted data exploration and maintaining a robust version history, AetherStats simplifies complex tasks and promotes best practices in statistical research and development.

-----

## 2\. Key Features

  * **Project Initialization & Structure:** Rapidly set up new projects with a predefined, standardized directory structure, Git integration, and a dedicated virtual environment.
  * **Component Management:** Create and organize various project components like scripts, notebooks, and reports.
  * **File Registration:** Maintain a clear manifest of all important project files (data, models, reports) for easy tracking and reference.
  * **Version Control & Reproducibility:** Integrate with Git and automatically snapshot key project files into a `logs.txt` for enhanced reproducibility and historical tracking.
  * **AI-Powered Insights:** Leverage artificial intelligence to quickly explore datasets and answer specific analytical questions.
  * **Automated Generation:** Generate code snippets or reports to automate routine tasks and produce consistent outputs.
  * **Project Status Monitoring:** Get real-time updates on your project's manifest and Git status.

-----

## 3\. Installation

```bash
# Provide installation instructions here.
# Example:
# pip install aether-stats
# Or:
# git clone https://github.com/yourusername/aether-stats.git
# cd aether-stats
# pip install -e .
```

-----

## 4\. Global Options

These options are available globally with the `aether-stats` command.

  * **`--install-completion`**

      * **Description:** Install completion for the current shell.
      * **Usage:**
        ```bash
        aether-stats --install-completion
        ```

  * **`--show-completion`**

      * **Description:** Show completion for the current shell, to copy it or customize the installation.
      * **Usage:**
        ```bash
        aether-stats --show-completion
        ```

  * **`--help`**

      * **Description:** Show the main help message and exit.
      * **Usage:**
        ```bash
        aether-stats --help
        ```
        *To get help for a specific command:*
        ```bash
        aether-stats [command] --help
        ```

-----

## 5\. Commands

### `init`

  * **Description:** Initializes a new AetherStats project with a standardized directory structure, Git, and `uv` virtual environment.
  * **Usage:**
    ```bash
    aether-stats init [PROJECT_NAME]
    ```
  * **Arguments:**
      * `PROJECT_NAME` (optional): The name of the new project directory. If not provided, the current directory will be initialized.
  * **Examples:**
      * Initialize a new project named `my_stats_project` in a new directory:
        ```bash
        aether-stats init my_stats_project
        ```
      * Initialize the current directory as an AetherStats project:
        ```bash
        aether-stats init
        ```

### `create`

  * **Description:** Creates a new component (script, notebook, report, task) within the current AetherStats project.
  * **Usage:**
    ```bash
    aether-stats create <TYPE> <NAME>
    ```
  * **Arguments:**
      * `TYPE`: The type of component to create (e.g., `script`, `notebook`, `report`, `task`).
      * `NAME`: The name of the new component file (e.g., `analysis_script`, `eda_notebook`).
  * **Examples:**
      * Create a new Python script named `data_preprocessing.py`:
        ```bash
        aether-stats create script data_preprocessing
        ```
      * Create a new Jupyter notebook named `exploratory_data_analysis.ipynb`:
        ```bash
        aether-stats create notebook exploratory_data_analysis
        ```
      * Create a new report template named `quarterly_report.md`:
        ```bash
        aether-stats create report quarterly_report
        ```

### `register`

  * **Description:** Registers a file (data, model, report, etc.) within the current AetherStats project's manifest.
  * **Usage:**
    ```bash
    aether-stats register <TYPE> <FILE_PATH> [--alias ALIAS]
    ```
  * **Arguments:**
      * `TYPE`: The category of the file (e.g., `data`, `model`, `report`, `script_output`).
      * `FILE_PATH`: The path to the file to register.
  * **Options:**
      * `--alias ALIAS`: An optional alias or friendly name for the registered file.
  * **Examples:**
      * Register a CSV data file:
        ```bash
        aether-stats register data data/raw_data.csv --alias raw_customer_data
        ```
      * Register a trained model file:
        ```bash
        aether-stats register model models/linear_regression.pkl
        ```
      * Register a generated report:
        ```bash
        aether-stats register report reports/final_report.pdf --alias sales_summary
        ```

### `list`

  * **Description:** Lists registered files, components, or logs within the project.
  * **Usage:**
    ```bash
    aether-stats list [TYPE]
    ```
  * **Arguments:**
      * `TYPE` (optional): The type of items to list (e.g., `data`, `models`, `components`, `logs`). If omitted, lists all registered items.
  * **Examples:**
      * List all registered files and components:
        ```bash
        aether-stats list
        ```
      * List only registered data files:
        ```bash
        aether-stats list data
        ```
      * List project components (scripts, notebooks, etc.):
        ```bash
        aether-stats list components
        ```
      * Display recent log entries:
        ```bash
        aether-stats list logs
        ```

### `status`

  * **Description:** Displays the current status of the AetherStats project, including manifest summary and Git status.
  * **Usage:**
    ```bash
    aether-stats status
    ```
  * **Examples:**
      * Check the overall project status:
        ```bash
        aether-stats status
        ```

### `commit`

  * **Description:** Performs a Git commit of changes and saves the content of registered and relevant project files into the `logs.txt` file as a snapshot.
  * **Usage:**
    ```bash
    aether-stats commit [-m "MESSAGE"]
    ```
  * **Options:**
      * `-m "MESSAGE"`: A commit message describing the changes.
  * **Examples:**
      * Commit current changes with a message:
        ```bash
        aether-stats commit -m "Implemented data cleaning script and updated EDA notebook."
        ```

### `explore`

  * **Description:** Uses AI to provide an initial overview and insights for a registered data file.
  * **Usage:**
    ```bash
    aether-stats explore <DATA_FILE_ALIAS_OR_PATH>
    ```
  * **Arguments:**
      * `DATA_FILE_ALIAS_OR_PATH`: The alias or path of a registered data file to explore.
  * **Examples:**
      * Get an AI-powered overview of `raw_customer_data`:
        ```bash
        aether-stats explore raw_customer_data
        ```
      * Explore a data file by its path:
        ```bash
        aether-stats explore data/sales.csv
        ```

### `analyze`

  * **Description:** Uses AI to answer a specific question about a registered data file.
  * **Usage:**
    ```bash
    aether-stats analyze <DATA_FILE_ALIAS_OR_PATH> -q "QUESTION"
    ```
  * **Arguments:**
      * `DATA_FILE_ALIAS_OR_PATH`: The alias or path of a registered data file to analyze.
  * **Options:**
      * `-q "QUESTION"`: The specific question to ask the AI about the data.
  * **Examples:**
      * Ask AI about customer demographics in `raw_customer_data`:
        ```bash
        aether-stats analyze raw_customer_data -q "What are the key demographic trends in this dataset?"
        ```
      * Query a sales dataset:
        ```bash
        aether-stats analyze data/sales.csv -q "What is the average sales per region?"
        ```

### `gen-logs`

  * **Description:** Display or verify the contents of the `logs.txt` file.
  * **Usage:**
    ```bash
    aether-stats gen-logs [--verify]
    ```
  * **Options:**
      * `--verify`: Verify the integrity of the log entries (e.g., checksums, file existence).
  * **Examples:**
      * Display the entire `logs.txt` file:
        ```bash
        aether-stats gen-logs
        ```
      * Verify the integrity of the log file:
        ```bash
        aether-stats gen-logs --verify
        ```

### `generate`

  * **Description:** Generate code or a report.
  * **Usage:**
    ```bash
    aether-stats generate <TYPE> [OPTIONS]
    ```
  * **Arguments:**
      * `TYPE`: The type of artifact to generate (e.g., `code`, `report`).
  * **Options:**
      * Specific options will depend on the `TYPE` being generated. For example, for `code` it might be `--language` and `--prompt`. For `report` it might be `--template` and `--data`.
  * **Examples:**
      * Generate a Python script for a specific task:
        ```bash
        aether-stats generate code --language python --prompt "a script to perform linear regression on 'my_data.csv'"
        ```
      * Generate a summary report based on a template and registered data:
        ```bash
        aether-stats generate report --template "executive_summary" --data "sales_summary"
        ```

-----

## 6\. Usage Examples

Here are a few common workflows using AetherStats CLI:

**Scenario 1: Starting a New Project and Initial Data Exploration**

```bash
# 1. Initialize a new project
aether-stats init my_new_analysis

# 2. Navigate into the project directory
cd my_new_analysis

# 3. Place your raw data file (e.g., 'customer_data.csv') into the 'data' directory.

# 4. Register the data file
aether-stats register data data/customer_data.csv --alias customer_info

# 5. Get an initial AI-powered overview of the data
aether-stats explore customer_info

# 6. Ask a specific question about the data
aether-stats analyze customer_info -q "What is the distribution of customer ages?"

# 7. Commit your initial setup and data registration
aether-stats commit -m "Initial project setup and registered customer_data.csv"
```

**Scenario 2: Creating a Script and Generating a Report**

```bash
# Assuming you are in an existing AetherStats project

# 1. Create a new Python script for data processing
aether-stats create script process_customer_data

# 2. (Manually edit 'scripts/process_customer_data.py' to add your logic)

# 3. Register the output of your script (e.g., a cleaned dataset)
#    (Assuming 'scripts/process_customer_data.py' generates 'data/cleaned_customer_data.csv')
aether-stats register data data/cleaned_customer_data.csv --alias cleaned_customers

# 4. Generate a report based on the cleaned data
aether-stats generate report --template "standard_analysis" --data "cleaned_customers"

# 5. Commit your changes
aether-stats commit -m "Added data processing script and generated initial report."
```

-----

## 7\. Contributing

We welcome contributions to AetherStats CLI\! If you have suggestions, bug reports, or want to contribute code, please refer to our contribution guidelines.

```bash
# [Link to CONTRIBUTING.md if you have one, e.g., https://github.com/yourusername/aether-stats/blob/main/CONTRIBUTING.md]
```

-----

## 8\. License

AetherStats CLI is distributed under the [Your License Type] License.

```bash
# [Link to LICENSE file if you have one, e.g., https://github.com/yourusername/aether-stats/blob/main/LICENSE]
```