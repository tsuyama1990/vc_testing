#!bin/bash

# 1. Install Python 3.12.4 via pyenv (if not installed yet)
pyenv install 3.12.4
# 2. Set local Python version for your project directory
pyenv local 3.12.4
# 3. Tell Poetry to create a new virtual environment with the pyenv Python version
poetry env use $(pyenv which python)
# 4. Install dependencies (including dev if needed)
poetry install --with dev
# 5. Set up pre-commit hooks if you use pre-commit
poetry run pre-commit install
# 6. Activate the Poetry shell
poetry shell
