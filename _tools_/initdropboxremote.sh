#!/bin/bash

set -eu
export PS4='> '
set -x

# rclone configured separately to have dropbox-yoh remote

r=dropbox-yoh-shub
# enabling encryption to possibly take advantage from compression which is then done
git annex initremote $r \
     type=external externaltype=rclone chunk=1GB encryption=shared target=dropbox-yoh prefix=datalad-stores/shub embedcreds=no
# no need/reason to hardcode UUID for this case AFAIK
# uuid=727f466f-60c3-4778-90b2-??????
git annex untrust $r
git annex wanted $r "(not metadata=distribution-restrictions=*)"
git config remote.github.datalad-publish-depends $r
# by default do push to github
git config branch.master.remote github

