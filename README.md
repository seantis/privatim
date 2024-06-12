privatim [![Tests](https://github.com/seantis/privatim/actions/workflows/tests.yml/badge.svg)](https://github.com/seantis/privatim/actions/workflows/tests.yml) [![codecov](https://codecov.io/gh/seantis/privatim/graph/badge.svg?token=JQHTKXDVMJ)](https://codecov.io/gh/seantis/privatim) [![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
===============

Getting Started
---------------

tl,dr:
```
git clone git@github.com:seantis/privatim.git
cd privatim
python3 -m venv venv
source venv/bin/activate
make install
make run
```

```
cp development.ini.example development.ini
```

- Upgrade packaging tools, if necessary.

```
pip install --upgrade pip setuptools
```

- Install the project in editable mode with its testing requirements.

```
make install
```
- Add a user

```
add_user --email admin@example.org --password test  development.ini
```

- Load default data into the database using a script.

```
initialize_db development.ini --only-consultation
```

- Run your project's tests.

```
pytest
```

## Run dev server

```
make run
```

- Login at http://localhost:6543 with admin@example.org / test


# Manage dependencies

We use `uv` to manage dependencies. However, you don't need to directly interact with `uv`

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

## Testing the Dockerfile works

    docker run --rm -p 8080:6543 -v $PWD/config:/app/config privatim-1 development.ini

then open http://127.0.0.1:8080/


## Miscellaneous

###  Filestorage location
By default, files are managed by sqlalchemy-file and are saved in the ./files directory

### Javascript/Css dependencies

The project includes js/css files.
If you need to update them, you can find the sources in the following locations:

####  Tom Select
The project uses [Tom Select](https://github.com/orchidjs/tom-select) for some forms.
These files are included in the project. They have been downloaded from these CDN links:
```
<link href="https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/css/tom-select.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/js/tom-select.complete.min.js"></script>
```
