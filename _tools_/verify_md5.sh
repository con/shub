#!/bin/bash

set -eu

for d in */*/*/*; do
    img=$(/bin/ls $d/*.si[mf]* 2>/dev/null)
    if [ -z "$img" ]; then
        echo "absent sif or simg image under $d - skipping"
        continue
    fi
    imgname=$(basename $img)
    checksum=$(dirname $img|xargs basename)
    #repo=$(dirname $img|xargs dirname | xargs basename)
    #org=$(dirname $img|xargs dirname | xargs dirname | xargs basename)
    if [ "${#checksum}" -ge 48 ]; then
        # sha256 - needs to be computed
        sha256=$(sha256sum $img|awk '{print $1;}')
        if [ "$sha256" != "$checksum" ]; then
            echo "ERROR: $img $checksum. Computed sha256=$sha256";
            exit 1
        else
            echo "$img sha256 $checksum ok"
        fi
    else
        # md5
        if readlink -f "$img" | grep -e "--$checksum" -q ; then
            echo "$img md5 ok"
        else
            echo "ERROR: $img $checksum "; readlink -f $img; exit 1;
        fi
    fi
done
