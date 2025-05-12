privatim [![Tests](https://github.com/seantis/privatim/actions/workflows/tests.yml/badge.svg)](https://github.com/seantis/privatim/actions/workflows/tests.yml) [![codecov](https://codecov.io/gh/seantis/privatim/graph/badge.svg?token=JQHTKXDVMJ)](https://codecov.io/gh/seantis/privatim) [![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
===============

Getting Started
---------------

Linux:
```bash
sudo apt update && sudo apt install libpoppler-cpp-dev libpq-dev python3-dev build-essential weasyprint
```

MacOS:
```bash
brew update && brew install postgresql poppler python libpq weasyprint
```

Create the PostgreSQL (Version >=12) database:
```
sudo -u postgres bash -c "psql <<EOF
CREATE USER dev WITH PASSWORD 'postgres' LOGIN NOINHERIT;
ALTER USER dev WITH SUPERUSER;
CREATE DATABASE privatim;
GRANT ALL PRIVILEGES ON DATABASE privatim TO dev;
EOF"
```

```
git clone git@github.com:seantis/privatim.git
cd privatim
python3.11 -m venv venv
source venv/bin/activate
make install
cp development.ini.example development.ini

# Add a user
add_user --email admin@example.org --password test --first_name Jane --last_name Dane development.ini

# Load default data into the database using a script (optional).
add_content development.ini
```

### Run dev server:
```
make run
```

## Run the project's tests
```
pytest -n auto
```

- Login at http://localhost:6543 with admin@example.org / test


# Pre-Commit

Make sure to enable pre-commit using:

    uv tool install pre-commit
    pre-commit install



Setup JavaScript toolchain (optional)
===================================
Currently only used for the Editor.

1. Install nvm [from here](https://github.com/nvm-sh/nvm?tab=readme-ov-file#install--update-script)

2. Restart your terminal or run:
   ```
   source ~/.bashrc
   ```

3. Install and use Node.js v18:
   ```
   nvm install 18
   nvm use 18
   ```

<details>
<summary>Set default Node.js version (click to expand)</summary>

This will set the default to be the most current version of node:
```
nvm alias default node
```
and then you'll need to run:
```
nvm use default
```
</details>

4. Verify installation:
   ```
   node --version # should return some version of v18
   ```

5. Build the frontend:

   ```
   make frontend
   ```



# Manage dependencies

If you add a new dependency to `setup.cfg`, you need to run `make compile` to update the `requirements.txt` file.
The `make compile` commands generates a `requirements.txt`.
This is then used by puppet and also the CI to install the dependencies.


## Regenerate requirements files based on new dependencies

    ./requirements/compile.sh


## Upgrade dependencies to latest version

Specific dependency:

    ./requirements/compile.sh -P Pillow

All dependencies:

    ./requirements/compile.sh -U

## Upgrade local environment

    uv pip install -r requirements.txt

## Sync local environment with CI/Production

This will remove packages that have been manually installed locally

    uv pip sync requirements.txt

## Miscellaneous

###  Filestorage location
By default, files are managed by sqlalchemy-file and are saved in the `files/` directory (relative to the repository root).

### Export Translations

```
pip install poxls
po-to-xls src/privatim/locale/fr/LC_MESSAGES/privatim.po
```
Will generate the `xlsx` file in the current working dir.

### Javascript/Css dependencies

Here we track all the statically included JavaScript assets.
If you need to update them, you can find the sources in the following locations:

###  Tom Select
The project uses [Tom Select](https://github.com/orchidjs/tom-select) for some forms.
These files are included in the project. They have been downloaded from these CDN links:
```
<link href="https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/css/tom-select.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/js/tom-select.complete.min.js"></script>
```

###  Sortable.js
For sorting with drag and drop, downloaded this:

https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/modular/sortable.core.esm.js
