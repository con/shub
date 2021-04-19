#!/bin/bash

set -eu

for d in */*/*/*; do
    if ! /bin/ls $d/ | grep -q . ; then
      echo "Removing $d since no files of interest. Has only:"
      ls -la $d/
      git rm -fr $d
    fi
done
