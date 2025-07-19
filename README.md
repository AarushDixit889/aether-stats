Okay, here's a comprehensive documentation for your CLI tool, referring to it as **AetherStats** as requested for this documentation, while acknowledging it's "Dantum" in other contexts.

-----

# AetherStats CLI Documentation

**Note:** In our previous conversations and in the code itself, this tool is referred to as "Dantum". For the purpose of this documentation, it will be referred to as "AetherStats".

## Introduction

AetherStats is a command-line interface (CLI) tool designed to streamline and automate common tasks in data science workflows. It provides an intelligent assistant experience for managing projects, environments, and data operations, making your data science development more structured and efficient.

AetherStats leverages popular tools like `Git` for version control, `uv` for lightning-fast Python environment management, and `pandas` for data handling, wrapped in a user-friendly `Typer` interface.

## Installation

To use AetherStats, clone it from its [repository](https://github.com/AarushDixit889/aether-stats)

## Commands

AetherStats provides a set of top-level commands, some of which have nested sub-commands for more specific functionalities.

### `aetherstats init`

Initializes a new AetherStats project with the standardized directory structure, sets up a Git repository (optional), and configures a `uv` virtual environment (optional).

**Usage:**

```bash
aetherstats init <project_name> [OPTIONS]
```

**Arguments:**

  * `<project_name>`: The name of the new project. A new directory with this name will be created.

**Options:**

  * `--force`, `-f`: Overwrite the project directory if it already exists. **WARNING: This will delete existing files\!**
  * `--no-git`: Do not initialize a Git repository in the new project.
  * `--no-uv`: Do not initialize a `uv` virtual environment in the new project.

**Examples:**

  * Initialize a new project named `my_data_analysis`:
    ```bash
    aetherstats init my_data_analysis
    ```
  * Initialize a project and overwrite if it exists:
    ```bash
    aetherstats init existing_project --force
    ```
  * Initialize without Git and uv:
    ```bash
    aetherstats init minimal_project --no-git --no-uv
    ```

### `aetherstats env`

Manages the Python virtual environment for your AetherStats project using `uv`. All `env` commands must be run from within your AetherStats project directory.

**Usage:**

```bash
aetherstats env <command> [ARGS]... [OPTIONS]...
```

#### `aetherstats env install`

Installs Python packages into the project's `uv` virtual environment. By default, installed packages are added to `requirements.txt` and `uv.lock` is updated for reproducibility.

**Usage:**

```bash
aetherstats env install <packages>... [OPTIONS]
```

**Arguments:**

  * `<packages>`: One or more package names to install (e.g., `numpy pandas "scipy>=1.10"`).

**Options:**

  * `--pip-arg`, `-p`: Pass additional arguments directly to the underlying `uv pip install` command (e.g., `-p --no-deps`).
  * `--no-save`: Do not save the installed packages to `requirements.txt` and do not update `uv.lock`.

**Examples:**

  * Install `scikit-learn`:
    ```bash
    aetherstats env install scikit-learn
    ```
  * Install `jupyterlab` and `seaborn`, passing a pip argument:
    ```bash
    aetherstats env install jupyterlab seaborn -p --upgrade-strategy eager
    ```
  * Install a package without saving it to `requirements.txt`:
    ```bash
    aetherstats env install debugpy --no-save
    ```

#### `aetherstats env uninstall`

Uninstalls packages from the project's `uv` virtual environment. By default, uninstalled packages are removed from `requirements.txt` and `uv.lock` is updated.

**Usage:**

```bash
aetherstats env uninstall <packages>... [OPTIONS]
```

**Arguments:**

  * `<packages>`: One or more package names to uninstall.

**Options:**

  * `--pip-arg`, `-p`: Pass additional arguments directly to the underlying `uv pip uninstall` command (e.g., `-p -y` to auto-confirm).
  * `--no-save`: Do not remove the uninstalled packages from `requirements.txt` and do not update `uv.lock`.

**Examples:**

  * Uninstall `scikit-learn`:
    ```bash
    aetherstats env uninstall scikit-learn
    ```
  * Uninstall multiple packages silently:
    ```bash
    aetherstats env uninstall jupyterlab seaborn -p -y
    ```

#### `aetherstats env list`

Lists all packages currently installed in the project's `uv` virtual environment.

**Usage:**

```bash
aetherstats env list
```

**Example:**

```bash
aetherstats env list
```

#### `aetherstats env sync`

Synchronizes the project's `uv` virtual environment with `requirements.txt` and `uv.lock`. This command ensures that your environment matches the declared dependencies, installing missing packages and removing extraneous ones.

**Usage:**

```bash
aetherstats env sync
```

**Example:**

```bash
aetherstats env sync
```

### `aetherstats data`

Provides commands for managing and processing data within your AetherStats project. All `data` commands must be run from within your AetherStats project directory.

**Usage:**

```bash
aetherstats data <command> [ARGS]... [OPTIONS]...
```

#### `aetherstats data ingest`

Ingests data from CSV or Excel files, loads them into a pandas DataFrame, and saves them to a specified output path, typically in `data/raw` or `data/processed`.

**Usage:**

```bash
aetherstats data ingest <source_path> <output_path> [OPTIONS]
```

**Arguments:**

  * `<source_path>`: Path to the input CSV or Excel file.
  * `<output_path>`: Path where the ingested data will be saved (e.g., `data/raw/my_data.parquet`).

**Options (Input Options):**

  * `--type`, `-t` (required): Type of the source file. Must be `'csv'` or `'excel'`.
  * `--header`/`--no-header`: Whether the input file has a header row. Defaults to `--header` (True).
  * `--sep`: Separator character for CSV files (e.g., `','` or `'\t'`). Defaults to `,`.
  * `--sheet`: Specific sheet name for Excel files. If not provided, the first sheet will be used.

**Options (Output Options):**

  * `--output-format`, `-f`: Format to save the ingested data. Must be `'csv'` or `'parquet'`. Defaults to `parquet`.

**Examples:**

  * Ingest a CSV file with default settings, save as Parquet:
    ```bash
    aetherstats data ingest data/raw/sales.csv data/processed/sales.parquet --type csv
    ```
  * Ingest a TSV file (tab-separated) without a header, save as CSV:
    ```bash
    aetherstats data ingest data/raw/users.tsv data/processed/users.csv --type csv --no-header --sep '\t' --output-format csv
    ```
  * Ingest an Excel file from a specific sheet:
    ```bash
    aetherstats data ingest data/raw/financials.xlsx data/processed/quarterly_report.parquet --type excel --sheet "Q1_Data"
    ```
  * Ingest an Excel file where the first row is data, not headers:
    ```bash
    aetherstats data ingest data/raw/no_header_excel.xlsx data/processed/no_header.parquet --type excel --no-header
    ```

-----
