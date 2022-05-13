#!/bin/bash

set -x
set -e

DDIR=$PWD/tmp
[ -d "$DDIR" ] || mkdir -p "$DDIR"
docker run -it --rm \
    --name tl_upload \
    -v $PWD:/data/ro:ro \
    -v "$DDIR:/data/rw" \
    tar_like \
    python3 -mtar_like.upload -u http://172.17.0.1:8000/tar -b /data/ro "$@"