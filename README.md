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

PostgresSQL is required. Sqlite won't work. Version needs to be >=12.

Create the PostgreSQL database:
```
sudo -u postgres bash -c "psql <<EOF
CREATE USER dev WITH PASSWORD 'devpassword' LOGIN NOINHERIT;
ALTER USER dev WITH SUPERUSER;
CREATE DATABASE privatim;
GRANT ALL PRIVILEGES ON DATABASE privatim TO dev;
EOF"
```
If you've already built onegov one time, you can skip the user creation.
```
git clone git@github.com:seantis/privatim.git
cd privatim
python3 -m venv venv
source venv/bin/activate
make install
cp development.ini.example development.ini
```

- Add a user

```
add_user --email admin@example.org --password test --first_name Jane --last_name Dane development.ini
```

- Load default data into the database using a script (optional).

```
add_content development.ini
```

### Run dev server

```
make run
```


## Run the project's tests

```
pytest -n auto
```


- Login at http://localhost:6543 with admin@example.org / test


# Manage dependencies

We use `uv` to manage dependencies. However, you don't need to directly interact with `uv`. Generally you can just use `make install`, `make update` and `make compile` if you've added new dependencies. The `make compile` commands generates the `requirements.txt` and `test_requirements.txt` which is then used in production.


## Regenerate requirements files based on new dependencies

    ./requirements/compile.sh

This generates `requirements.txt` and `test_requirements.txt` based on the dependencies in setup.cfg`.
This is used by puppet and the CI to install the dependencies on the server.

## Upgrade dependencies to latest version

Specific dependency:

    ./requirements/compile.sh -P Pillow

All dependencies:

    ./requirements/compile.sh -U

## Upgrade local environment

    uv pip install -r requirements.txt -r test_requirements.txt

## Sync local environment with CI/Production

This will remove packages that have been manually installed locally

    uv pip sync requirements.txt test_requirements.txt



## Miscellaneous

###  Filestorage location
By default, files are managed by sqlalchemy-file and are saved in the ./files directory

### Export Translations

```
po-to-xls src/privatim/locale/fr/LC_MESSAGES/privatim.po
```

### Javascript/Css dependencies

The project includes js/css files.
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
