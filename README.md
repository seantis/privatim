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
./initialize_db development.ini
```


- Run your project's tests.

```
pytest
```

## Run

```
make run
```

- Login at http://localhost:9090 with info@seantis.ch / test
