privatim
========

Getting Started
---------------


- Clone repository

  git clone git@github.com:seantis/privatim.git

- Change directory into your newly created project if not already there. Your
  current directory should be the same as this README.txt file and setup.py.

    cd privatim

- Create a Python virtual environment, if not already created.

    python3 -m venv venv


```
source venv/bin/activate
```

- Upgrade packaging tools, if necessary.
- 
    pip install --upgrade pip setuptools

- Install the project in editable mode with its testing requirements.

```
make install
```

- Load default data into the database using a script.

  ./initialize_db development.ini

- Run your project's tests.

    pytest

- Run your project.

    pserve development.ini

- Login at http://localhost:9090 with info@seantis.ch / test 
