# Python Best Practices

## Environment & Project Setup

### Package Management

- **Default to UV**: Use `uv` for all Python package management operations
- Commands: `uv sync`, `uv add <package>`, `uv run <command>`
- Configuration: Use `pyproject.toml` for dependencies and project metadata

### Environment Setup

- Create virtual environments with: `uv venv`
- Activate with: `.venv/Scripts/activate` (Windows) or `source .venv/bin/activate` (Unix)
- Install dependencies: `uv sync`

### Project Initialization

When starting a new Python project:

1. Create basic directory structure (src/, tests/, docs/, scripts/, etc.)
2. Initialize with `uv init`
3. Set up `pyproject.toml` with project metadata
4. Create `.gitignore` (Python, venv, IDE, OS-specific)
5. Add basic README.md

## Core Principles
- Write clear, readable code with meaningful variable and function names
- Prefer simple, functional solutions; avoid unnecessary classes or over-engineering
- Use vectorized operations (NumPy / pandas) instead of explicit loops when possible
- Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines

## Code Style
- Format with **Black** (88-character line limit)
- Sort imports with **isort**; group stdlib / third-party / local imports
- Naming: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants
- Prefer **absolute imports** over relative imports

## Type Hints & Documentation
- Add **type hints** to all public functions and class methods
- Use **Google-style docstrings** for public APIs
  _(document parameters, return values, raised exceptions)_
- Keep docstrings concise and update them when function signature changes

## Error Handling & Logging
- Wrap error-prone code in `try` / `except` blocks with **specific exceptions**
- Use `logging` for production code; `print` acceptable in scratch/exploration
- Avoid swallowing exceptions silently — log or re-raise when appropriate

## Dependencies
- **Only import libraries listed in `pyproject.toml`**
- **Ask before adding new dependencies**; update `pyproject.toml` explicitly
- Manage environment with **uv** (`uv lock`, `uv run`)

## Virtual Environment
- Always run scripts via `uv run` to ensure the correct environment

## Formatting Guide

### Section Headers

Use `# --- Section Name ---` to divide your code into logical parts.

Common headers:

* `# --- Imports ---`
* `# --- Constants ---`
* `# --- Helper Functions ---`
* `# --- Main Functions ---`
* `# --- Data Processing ---`
* `# --- Analysis ---`
* `# --- Visualization ---`
* `# --- Output ---`
* `# --- Testing ---`

### Cell Separators

Use `#%%` to split code into executable cells:

```python
#%% Imports
import pandas as pd
import numpy as np

#%% Data Load
data = pd.read_csv("data.csv")

#%% Analysis
summary = data.describe()
```

### Combined Usage

You can combine headers and cell separators:

```python
# --- Imports ---
#%%
import pandas as pd
import numpy as np

# --- Helper Functions ---
#%%
def compute_signal(prices, window):
    ...
```

## When to Use Formatting

### Section Headers:

* Files > 100 lines
* Start of major parts (functions, logic blocks)
* Before each project phase (e.g., data cleaning, modeling)

### Cell Separators:

* Each logical execution block
* Data load, processing, plotting, testing

## Formatting Best Practices

1. **Be Consistent**: Use the same format across files
2. **Name Clearly**: Describe each section clearly
3. **Logical Order**: imports → constants → helpers → main → testing
4. **Cell Independence**: Each cell should ideally run standalone
5. **Explain Sections**: Add a brief comment after each section header
