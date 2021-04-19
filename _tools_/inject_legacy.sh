#!/bin/bash

set -eu

for d in singularityhub-legacy/github.com/*/*/*; do
    img=$(/bin/ls $d/*.img.gz)
    if [ -z "$img" ]; then
        echo "absent image under $d"
        exit 1
    fi
    imgname=$(basename $img)
    commit=$(dirname $img|xargs basename)
    repo=$(dirname $img|xargs dirname | xargs basename)
    org=$(dirname $img|xargs dirname | xargs dirname | xargs basename)
done
