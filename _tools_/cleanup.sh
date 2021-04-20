#!/bin/bash

set -eu

for d in */*/*/*; do
    echo "Looking at $d"
    if ! /bin/ls $d/ | grep -q . ; then
      echo "Removing $d since no files of interest. Has only:"
      ls -laL $d/
      git rm -fr $d || :
      continue
    fi
    img=$(/bin/ls $d/*.si[mf]* 2>/dev/null || /bin/ls $d/*.img.gz 2>/dev/null || echo '')
    if [ -z "$img" ]; then
        echo "Removing $d: absent image file"
        ls -laL $d/
        git rm -fr $d || echo "must have had no files"
    fi
done
# remove empty dirs git does not care about
rmdir */*/*/* */*/* */* 2>/dev/null || :
