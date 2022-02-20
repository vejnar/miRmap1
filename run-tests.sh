#!/bin/bash

PYTHONPATH=$PYTHONPATH:"$(pwd)/src"

python3 -m unittest discover -s tests

