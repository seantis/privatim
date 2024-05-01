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

## Miscellaneous
### Javascript dependencies
The project uses [Tom Select](https://github.com/orchidjs/tom-select) for some forms.
These files are included in the project. They have been downloaded from these CDN links:

```
<link href="https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/css/tom-select.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/js/tom-select.complete.min.js"></script>
```
