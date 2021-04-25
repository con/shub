#!/bin/bash

set -eu

for d in singularityhub-legacy/github.com/*/*/*; do
    echo "I: $d"
    img=$(/bin/ls $d/*.img.gz)
    if [ -z "$img" ]; then
        echo "absent image under $d"
        exit 1
    fi
    imgfile=$(basename $img)
    imgname=${imgfile//.img.gz}  # md5sum of gunzip'ed content
    commit=$(dirname $img|xargs basename)
    repo=$(dirname $img|xargs dirname | xargs basename)
    org=$(dirname $img|xargs dirname | xargs dirname | xargs basename)
    commitdir=$org/$repo/$commit
    imgdir=$org/$repo/$commit/$imgname
    if [ -e $imgdir ]; then
        echo "$imgdir exists"
        exit 1
    fi
    emd5=$(md5sum <(zcat $img ) | awk '{print $1;}')
    if [ "$emd5" != "$imgname" ]; then
      echo "$emd5 != $imgname"
      exit 1
    fi
    mkdir -p $commitdir
    mv $(dirname $img) $imgdir
done
