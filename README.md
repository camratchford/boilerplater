# boilerplater

A CLI tool for scaffolding new projects from Jinja2 template directories.
Define typed variables directly in your templates, load default values from
YAML data files, and fill in the rest interactively through a terminal form.

---

## Features

- **Typed template variables** — annotate variables with PEP 484-style type
  hints (`{{ count: int }}`) to get the right input widget automatically
- **Interactive TUI form** — prompts for any undeclared variables using a
  clean terminal UI (powered by [Textual](https://github.com/Textualize/textual))
- **YAML data files** — pre-supply common variables (author name, email, etc.)
  so you're never asked for the same thing twice
- **Binary-safe** — text files are rendered as Jinja2 templates; binary files
  (images, archives, ELF binaries) are copied verbatim using libmagic detection
- **Permission-preserving** — file modes are carried over from the template to
  the output

---

## Requirements

- Linux / MacOS
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

Boilerplater expects two directories:

| Directory         | Default                               | Purpose                                      |
|-------------------|---------------------------------------|----------------------------------------------|
| `--templates-dir` | `~/.local/opt/boilerplater/templates` | Your project template directories            |
| `--data-dir`      | `~/.local/opt/boilerplater/data`      | YAML files containing pre-supplied variables |

Both are created automatically on first run if they don't exist.

### Template structure

Templates are organised into **categories** (e.g. language or framework) and
**templates** (e.g. project type):

```
~/.local/opt/boilerplater/templates/
  python/
    cli/
      {{ module_name }}/
        __init__.py
        __main__.py
      pyproject.toml
      README.md
  rust/
    cli/
      src/
        main.rs
      Cargo.toml
```

Any file that libmagic identifies as a text type is rendered as a Jinja2
template. Everything else is copied as-is.

### Typed variables

Variables can carry an optional type annotation in the template tag:

```
{{ variable_name: type }}
```

Supported types and their form widgets:

| Type           | Widget                    |
|----------------|---------------------------|
| `str`          | Text input                |
| `int`          | Integer input (validated) |
| `float`        | Number input (validated)  |
| `bool`         | Checkbox                  |
| `click.Choice` | Select dropdown           |

The annotation is stripped before rendering — `{{ count: int }}` becomes
`{{ count }}` at render time.

### Data files

Place any number of `.yaml` files in your data directory to pre-supply variables across all
templates. Any variable defined here won't appear in the interactive form.

```yaml
# ~/.local/opt/boilerplater/data/user.yaml
author: Samwise Gamgee
email: mayorofhobbiton@example.com
github: mayorgamgee
```

---

## Usage

```bash
boilerplater <target-path> [OPTIONS]
```

### Arguments

| Argument      | Description                           |
|---------------|---------------------------------------|
| `target-path` | Where the new project will be created |

### Options

| Option            | Short | Description                       | Default                               |
|-------------------|-------|-----------------------------------|---------------------------------------|
| `--templates-dir` |       | Path to your templates            | `~/.local/opt/boilerplater/templates` |
| `--data-dir`      |       | Path to your YAML data files      | `~/.local/opt/boilerplater/data`      |
| `--category`      | `-c`  | Template category (e.g. `python`) | prompted                              |
| `--template`      | `-t`  | Template name (e.g. `cli`)        | prompted                              |
| `--log-level`     |       | Logging verbosity                 | `WARNING`                             |

### Examples

**Fully interactive** — prompts for category, template, and any undeclared variables:

```bash
boilerplater ~/projects/my-new-app
```

**Category provided** — prompts for template only:

```bash
boilerplater ~/projects/my-new-app -p python
```

**Fully specified** — prompts only for undeclared template variables:

```bash
boilerplater ~/projects/my-new-app -p python -t cli
```

### Shell completion

Boilerplater supports tab completion for `--category` and `--template` via Typer.

To install completions for your shell:

```bash
boilerplater --install-completion
```

> Typer is aware of what shell you are using and will install the completion in the corresponding directory. <br>
> For bash: `$HOME/.bash_completions/boilerplater.sh`
> For fish: `$HOME/.config/fish/completions/boilerplater.fish`
> For zsh: `$HOME/.zfunc/_boilerplater` <br>

---

## Built-in defaults

The following variables are always available in templates without needing to be
declared in a data file or prompted:

| Variable       | Value                                          | Purpose                                                                         | Example                                       |
|----------------|------------------------------------------------|---------------------------------------------------------------------------------|-----------------------------------------------|
| `now`          | `datetime.now()` at time of invocation         | When the current date is required as a variable                                 | `Copyright {{ now.year }}`                    |
| `module_name`  | `target-path` stem, slugified with underscores | For use in path names and import statements or wherever snake case is prefered. | `from {{ module_name }}.config import Config` |
| `package_name` | `target-path` stem as-is                       | For use in documentation or other cases where the name of the project is used.  | `## Installing {{ package_name }}`            |

---

## License

[MIT](./LICENSE)
