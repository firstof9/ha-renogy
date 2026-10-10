# Contributing to ha-renogy

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

> **AI coding agents**: Please also read [AGENTS.md](AGENTS.md), which covers architecture, Modbus register mappings, and repository-specific patterns in detail.

## Getting started

We recommend using [`uv`](https://docs.astral.sh/uv/) to manage your local environment and dependencies:

```bash
git clone https://github.com/firstof9/ha-renogy
cd ha-renogy

# Create and activate Python 3.14 virtual environment
uv venv --python 3.14
source .venv/bin/activate

# Install test and development requirements
uv pip install -r requirements_test.txt

# Install pre-commit hooks
pre-commit install
```

## Running tests

```bash
# Run tests directly with pytest
pytest

# Or run with uv in an ephemeral environment
uv run --with-requirements requirements_test.txt pytest

# Run a single test file
pytest tests/test_validator.py -v

# Run full test matrix with tox
uv tool run --with tox-uv --with tox-gh-actions tox
```

## Linting & formatting

Code formatting and linting are handled by `ruff` and `codespell` via `pre-commit` / `prek`:

```bash
pre-commit run --all-files
# or using uv + prek
uv run prek run --all-files
```

## Pull requests

1. Fork the repo and create your branch (`git checkout -b fix/short-description`).
2. Keep pull requests focused and atomic.
3. Ensure all tests and linting checks pass locally before opening a pull request.
4. **Translations**: If adding or altering user-facing configuration strings, update `custom_components/renogy/strings.json` and mirror changes into `custom_components/renogy/translations/en.json`.
5. **BLE Parsers & Registers**: If updating Modbus register blocks or parsing in `ble_parsers.py`, add corresponding fixtures and tests in `tests/test_parsers.py`.
6. **Validation Limits**: If adding numerical sensors to `ble_validator.py`, ensure ranges accommodate all supported hardware configurations without rejecting valid data.
7. Reference related issues in your PR description (e.g. `Fixes #125`).

## Reporting bugs

Report bugs by [opening a new issue](../../issues/new/choose).

**Great bug reports** include:
- A clear description of the issue
- Steps to reproduce
- What version of Home Assistant and `ha-renogy` you are running
- Hardware model (e.g., Rover 40, Rover 60, Smart Lithium Battery) and connection type (Renogy Hub / Cloud API, BT-1, BT-2)
- Relevant Home Assistant logs showing errors or data rejection warnings

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
