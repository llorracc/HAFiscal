#!/bin/bash

# Make sure the necessary requirements are available
source ./reproduce/reproduce_environment.sh

# Change directory to the location of the Python script
cd Code/HA-Models

# Run the Python script
python reproduce_min.py
