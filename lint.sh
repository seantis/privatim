#!/bin/bash

flake8 src tests
./mypy.sh

