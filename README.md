privatim
========

Getting Started
---------------



```
git clone git@github.com:seantis/privatim.git
cd privatim
```

- Create a Python virtual environment, if not already created.

```
python3 -m venv venv
source venv/bin/activate
```

```
cp development.ini.example development.ini
# adjust `assets_dir` in development.ini to some directory (e.g. /tmp/privatim_assets)
```

- Upgrade packaging tools, if necessary.

```
pip install --upgrade pip setuptools
```

- Install the project in editable mode with its testing requirements.

```
make install
```

- Load default data into the database using a script.

```
initialize_db development.ini
```


- Run your project's tests.

```
pytest
```

## Run dev server

```
make run  # uses pserve
```

- Login at http://localhost:9090 with admin@example.org / test


# Manage dependencies

We use `uv` to manage dependencies

## Regenerate requirements files based on new dependencies

    ./requirements/compile.sh

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

    docker run --rm -p 8080:6543 -v $PWD/config:/app/config privatim-1 config/development.ini

then open http://127.0.0.1:8080/


## Miscellaneous
### Javascript dependencies
The project uses [Tom Select](https://github.com/orchidjs/tom-select) for some forms.
These files are included in the project. They have been downloaded from these CDN links:

```
<link href="https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/css/tom-select.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/js/tom-select.complete.min.js"></script>
```


