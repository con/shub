#!/bin/bash

set -eu

for d in */*/*/*; do
    if ! /bin/ls $d/ | grep -q . ; then
      echo "Removing $d since no files of interest. Has only:"
      ls -la $d/
      git rm -fr $d
    fi
    img=$(/bin/ls $d/*.si[mf]* 2>/dev/null || echo '')
    if [ -z "$img" ]; then
        echo "Removing $d: absent image file"
        ls -lL $d/
        git rm -fr $d
    fi
done
# remove empty dirs git does not care about
rmdir */*/*/* */*/* */* 2>/dev/null || :
