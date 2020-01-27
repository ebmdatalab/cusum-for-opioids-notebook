#!/bin/bash
set -e
DIR=$1
# This script is invoked as `docker_entrypoint.sh <PYTHONPATH> jupyter-notebook --opt1, opt2...
# or as `docker_entrypoint.sh <PYTHONPATH>  --opt1, opt2...
shift 1
if [ "$1" == "jupyter-notebook" ]; then
    shift 1
fi
cd $DIR
exec sh -c "PYTHONPATH=$DIR jupyter lab --debug  $@"
