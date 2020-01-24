#!/bin/bash
set -e
DIR=$1
shift 1
cd $DIR
exec sh -c "PYTHONPATH=$DIR jupyter lab --config=config/jupyter_notebook_config.py $@"
