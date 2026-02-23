# Packaging and Distribution

`pCompiler` uses `hatchling` as its build backend, as configured in `pyproject.toml`. This follows modern Python packaging standards (PEP 517).

## Prerequisites

Ensure you have the `build` package installed:

```bash
pip install build
```

## Building the Package

To generate the distribution files (both professional `wheel` and source `sdist`), run:

```bash
python -m build
```

The output files will be located in the `dist/` directory:
- `pcompiler-0.1.0-py3-none-any.whl`
- `pcompiler-0.1.0.tar.gz`

## Local Installation

You can install the freshly built package using `pip`:

```bash
pip install dist/pcompiler-0.1.0-py3-none-any.whl
```

Or install in editable mode for development:

```bash
pip install -e .
```

## Publishing to PyPI

If you wish to share `pCompiler` with the world:

1.  **Register** an account on [PyPI](https://pypi.org/).
2.  **Install Twine**:
    ```bash
    pip install twine
    ```
3.  **Upload to PyPI**:
    ```bash
    twine upload dist/*
    ```

> [!IMPORTANT]
> Always increment the `version` field in `pyproject.toml` and `pcompiler/__init__.py` before uploading a new version to PyPI.
