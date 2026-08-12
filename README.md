# boilerplater

A CLI tool for scaffolding new projects from Jinja2 template directories.
Define typed variables directly in your templates, load default values from YAML data files, and fill in the rest 
interactively through a terminal form.

### Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Setup](#setup)
  - [Template Structure](#template-structure)
  - [Typed Variables](#typed-variables)
  - [Data Files](#data-files)
- [Modules & Add-ons](#modules--add-ons)
- [Per-Template Configs](#per-template-configs)
- [Usage](#usage)
  - [Arguments](#arguments)
  - [Options](#options)
  - [Examples](#examples)
  - [Shell Completion](#shell-completion)
- [Configuring Boilerplater](#configuring-boilerplater)
  - [Config Options](#config-options)
  - [Jinja2 Settings](#jinja2-settings)
- [Default Variables](#default-variables)
- [License](#license)


## Features


- **Interactive TUI form** 
  - Prompts for any undeclared variables using a clean [Textual](https://github.com/Textualize/textual) TUI
  - Annotate variables with PEP 484-style type hints (`{{ count: int }}`) for type-based input validation
- **YAML data files** 
  - Pre-supply common variables (author name, email, etc.)
- **Binary-safe** 
  - Text files are rendered as Jinja2 templates; binary files (images, archives, ELF binaries) are copied verbatim using 
    libmagic detection
  - Optionally, supply a list of glob patterns to extend the list of copy-only files.
- **Permission-preserving** 
  - File modes are carried over from the template to the output
- **Modules & add-ons** 
  - Share reusable pieces (Dockerfiles, CI configs, etc.) across templates, either required automatically or offered as 
    an opt-in checklist per project
- **Per-template config** 
  - Control which files are excluded, force-copied, or cleaned up, and what runs after rendering, on a per-template or 
    per-module basis
- **Layered configuration** 
  - Defaults, environment variables, a YAML config file, and CLI options each override the last
- **Dry-run mode** 
  - Preview which files would be created without writing anything to disk

---

## Requirements

- Linux / MacOS
  - The libmagic1 library must be installed for binary file detection 
- Python 3.10+


```bash
# Debian / Ubuntu
apt install libmagic1

# macOS
brew install libmagic
```

---

## Installation

```bash
pip install boilerplater
```

Or with [pipx](https://pypa.github.io/pipx/) (recommended for CLI tools):

```bash
pipx install boilerplater
```

---

## Setup

Boilerplater expects three directories:

| Directory         | Default                               | Purpose                                         |
|-------------------|---------------------------------------|-------------------------------------------------|
| `--templates-dir` | `~/.local/opt/boilerplater/templates` | Your project template directories               |
| `--data-dir`      | `~/.local/opt/boilerplater/data`      | YAML files containing pre-supplied variables    |
| `--modules-dir`   | `<templates-dir>/modules`             | Shared [modules and add-ons](#modules--add-ons) |

None of these are created for you automatically - pass `--init` on your first
run and boilerplater will create whichever of the three don't already exist.

### Template Structure

Templates are organised into **categories** (e.g. language or framework) and
**templates** (e.g. project type):

<pre>
<code>
~/.local/opt/boilerplater/templates/ # <-- Default 'templates_dir' value
  python/                            # <-- Category
    cli/                             # <-- Template
      {{ module_name }}/             # <-- Variable File Name
        __init__.py
        __main__.py
      boilerplater.yml                # <-- <a href="#per-template-configs">Per-template Config (optional)</a>
      pyproject.toml
      README.md
    cffi_module/                     # <-- Template
      {{ module_name }}/
        src/
          {{ module_name }}.c
        __init__.py
        main.py
        build_{{ module_name }}.py
      pyproject.toml
      setup.py
      README.md
  rust/                              # <-- Category
    cli/                             # <-- Template
      src/
        main.rs
      Cargo.toml
  modules/                           # <-- Modules dir (see Modules & Add-ons)
    docker/
      Dockerfile
      boilerplater.yml
</code></pre>


Any file that libmagic identifies as a text type is rendered as a Jinja2
template. Everything else is copied as-is.

### Typed Variables

Variables can carry an optional type annotation in the template tag:

```
{{ variable_name: type }}
```

Supported types and their form widgets:

| Type              | Widget                    |
|-------------------|---------------------------|
| `str`             | Text input                |
| `int`             | Integer input (validated) |
| `float`           | Number input (validated)  |
| `bool`            | Checkbox                  |
| `Choice([...])`   | Select dropdown           |

For example, `{{ environment: Choice(["dev", "staging", "prod"]) }}` renders a dropdown with those three options.

The annotation is stripped before rendering - `{{ count: int }}` becomes `{{ count }}` at render time.

### Data Files

Place any number of `.yaml` files in your data directory to pre-supply variables across all templates. 
Any variable defined here won't appear in the interactive form.

```yaml
# ~/.local/opt/boilerplater/data/user.yaml
author: Samwise Gamgee
email: mayorofhobbiton@example.com
github: mayorgamgee
```

---

## Modules & Add-ons

Modules live in `--modules-dir`, one subdirectory per module, each with its own `boilerplater.yml`. 
A module is itself a small template - its files are rendered and copied the same way a project template's are.

A module is included in a project in one of two ways:

- **Required** - listed in the project template's `requirements`, it's always included.
- **Optional (add-on)** - listed in the project template's `add_ons`, it's offered as a checklist before rendering begins.

Modules can require other modules in turn (`requirements` on the module itself), and boilerplater resolves the chain 
automatically. 
A module also declares which categories it's valid for via `target_categories`, either a list of category names or `"*"` 
for all categories.
Boilerplater raises an error if a module is required by a template whose category isn't in that list.

```yaml
# ~/.local/opt/boilerplater/templates/modules/docker/boilerplater.yml
description: Adds a Dockerfile and .dockerignore
target_categories: ["python", "rust"]
```

```yaml
# ~/.local/opt/boilerplater/templates/python/cli/boilerplater.yml
requirements: ["pre-commit"]
add_ons: ["docker"]
```

---

## Per-Template Configs

Any project template or module may include a `boilerplater.yml` in its root directory to customize how it's processed. 
All fields are optional.

| Field                     | Applies to         | Description                                                                                     | Default                        |
|---------------------------|--------------------|-------------------------------------------------------------------------------------------------|--------------------------------| 
| `description`             | template, module   | Free-text description, shown in tooling                                                         | `""`                           |
| `requirements`            | template, module   | Names of modules that must always be included                                                   | `[]`                           |
| `variable_default_values` | template, module   | Default values offered for undeclared template variables                                        | `{}`                           |
| `exclude_patterns`        | template, module   | Glob patterns for files to skip entirely                                                        | `["boilerplater.yml"]`         |
| `force_copy_patterns`     | template, module   | Glob patterns for files to copy verbatim instead of rendering as Jinja2                         | `["*.j2"]`                     |
| `cleanup_patterns`        | template, module   | Glob patterns, relative to the output directory, deleted after rendering completes              | `[".placeholder", ".gitkeep"]` |
| `run_on_complete_scripts` | template, module   | Paths (relative to the output directory) to executable scripts run after rendering completes    | `[]`                           |
| `add_ons`                 | template only      | Names of modules offered as an opt-in checklist before rendering                                | `[]`                           |
| `target_categories`       | module only        | Categories the module is valid for; `"*"` for all                                               | `None` (module is unusable)    |

`name` and `category`/`path` are set automatically from the directory structure and don't need to be specified.

---

## Usage

```bash
boilerplater <target-path> [OPTIONS]
```

### Arguments

| Argument      | Description                             |
|---------------|-----------------------------------------|
| `target-path` | Where the new project will be created   |

### Options

| Option               | Short | Description                                                                     | Default                               |
|----------------------|-------|---------------------------------------------------------------------------------|---------------------------------------|
| `--init`             |       | Create `--templates-dir`, `--modules-dir`, and `--data-dir` if they don't exist | `False`                               |
| `--templates-dir`    |       | Path to your templates                                                          | `~/.local/opt/boilerplater/templates` |
| `--data-dir`         |       | Path to your YAML data files                                                    | `~/.local/opt/boilerplater/data`      |
| `--modules-dir`      |       | Path to your shared modules                                                     | `<templates-dir>/modules`             |
| `--category`         | `-c`  | Template category (e.g. `python`)                                               | prompted                              |
| `--template`         | `-t`  | Template name (e.g. `cli`)                                                      | prompted                              |
| `--config-file`      | `-C`  | Path to a [boilerplater config file](#configuring-boilerplater)                 | `$PWD/.boilerplater.yml`              |
| `--log-level`        |       | Logging verbosity                                                               | `INFO`                                |
| `--dry-run`          |       | List output files instead of rendering templates / copying files                | `False`                               |

### Examples

**Fully interactive** - prompts for category, template, and any undeclared variables:

```bash
boilerplater ~/projects/my-new-app
```

**Category provided** - prompts for template only:

```bash
boilerplater ~/projects/my-new-app -c python
```

**Fully specified** - prompts only for undeclared template variables:

```bash
boilerplater ~/projects/my-new-app -c python -t cli
```

### Shell Completion

Boilerplater supports tab completion for `--category` and `--template` via Typer.

To install completions for your shell:

```bash
boilerplater --install-completion
```

> Typer is aware of what shell you are using and will install the completion in the corresponding directory. <br>
> For bash: `$HOME/.bash_completions/boilerplater.sh`
> For fish: `$HOME/.config/fish/completions/boilerplater.fish`
> For zsh: `$HOME/.zfunc/_boilerplater` <br>


## Configuring Boilerplater

Values are loaded into `BoilerplaterConfig` in the following order, each overriding the last:

1. `BoilerplaterConfig`'s defaults
2. Environment variables
3. Config file contents
4. CLI options (where a matching config option exists)

Environment variables are prefixed with `BOILERPLATER_`. For example, to set the `data_dir` config option, 
set `BOILERPLATER_DATA_DIR`.

The config file format is YAML. Its default location is `$PWD/.boilerplater.yml`; override it with `--config-file` / `-C`, 
or the `BOILERPLATER_CONFIG_FILE` environment variable. If the file exists, its values are merged in as described above.


### Config Options

| Name          | CLI Option              | Description                                                                                                                   | Default                                  |
|---------------|-------------------------|-------------------------------------------------------------------------------------------------------------------------------|------------------------------------------|
| config_file   | `--config-file` or `-C` | Location of the boilerplater config file                                                                                      | `None`                                   |
| templates_dir | `--templates-dir`       | Your project template directories                                                                                             | `"~/.local/opt/boilerplater/templates"`  |
| data_dir      | `--data-dir`            | YAML files containing pre-supplied variables                                                                                  | `"~/.local/opt/boilerplater/data"`       |
| modules_dir   | `--modules-dir`         | Shared modules, for reusable components or opt-in add-ons                                                                     | `<templates_dir>/modules` (if it exists) |
| log_level     | `--log-level`           | Verbosity of the log output. See [Python Documentation](https://docs.python.org/3/library/logging.html#logging-levels).       | `"info"`                                 |
| dry_run       | `--dry-run`             | List output files instead of rendering templates / copying files.                                                             | `False`                                  |
| target_path   | positional argument #0  | The output directory of the rendered template.                                                                                | `None`                                   |
| category      | `--category` or `-c`    | The name of one of `templates_dir`'s child directories.                                                                       | `None`                                   |
| template      | `--template` or `-t`    | The name of one of `category`'s child directories. The contents of this directory are used as the template for `target_path`. | `None`                                   |

#### Jinja2 Settings

`BoilerplaterConfig` sets the following `jinja2.Environment` init options.
Certain projects need to override these (any other template system that
adopts Jinja2's style, such as Helm charts).

| kwarg                        | description                                                                                      | default  |
|------------------------------|--------------------------------------------------------------------------------------------------|----------|
| jinja2_block_start_string    | The string marking the beginning of a block.                                                     | `"{%"`   |
| jinja2_block_end_string      | The string marking the end of a block.                                                           | `"%}"`   |
| jinja2_variable_start_string | The string marking the beginning of a print statement.                                           | `"{{"`   |
| jinja2_variable_end_string   | The string marking the beginning of a block.                                                     | `"}}"`   |
| jinja2_comment_start_string  | The string marking the beginning of a comment.                                                   | `"{#"`   |
| jinja2_comment_end_string    | The string marking the end of a comment.                                                         | `"#}"`   |
| jinja2_line_statement_prefix | If given and a string, this will be used as prefix for line based statements.                    | `None`   |
| jinja2_line_comment_prefix   | If given and a string, this will be used as prefix for line based comments.                      | `None`   |
| jinja2_trim_blocks           | If this is set to True the first newline after a block is removed (block, not variable tag!).    | `False`  |
| jinja2_lstrip_blocks         | If this is set to True leading spaces and tabs are stripped from the start of a line to a block. | `False`  |
| jinja2_newline_sequence      | The sequence that starts a newline. Must be one of `'\r'`, `'\n'` or `'\r\n'`.                   | `"\n"`   |
| jinja2_keep_trailing_newline | Preserve the trailing newline when rendering templates.                                          | `False`  |


### Default Variables

The following variables are always available in templates without needing to be declared in a data file or prompted:

| Variable       | Value                                          | Purpose                                                                          | Example                                       |
|----------------|------------------------------------------------|----------------------------------------------------------------------------------|-----------------------------------------------|
| `now`          | `datetime.now()` at time of invocation         | When the current date is required as a variable                                  | `Copyright {{ now.year }}`                    |
| `module_name`  | `target-path` stem, slugified with underscores | For use in path names and import statements, or wherever snake_case is preferred | `from {{ module_name }}.config import Config` |
| `package_name` | `target-path` stem, as-is                      | For use in documentation or other cases where the project name is used verbatim  | `## Installing {{ package_name }}`            |


## License

[MIT](./LICENSE)
