#!/bin/bash

set -eu
umask 077
cd $(dirname $0) && cd ..
singularity run --no-home -e -B /srv/datasets.datalad.org/shub/logs -B $PWD _service_/service.sif _service_/serve.py _data_/images.json &
disown
