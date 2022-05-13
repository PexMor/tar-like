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
    python3 -mtar_like.check -b /data/rw/recv-test