#!/bin/bash

set -x
set -e

DDIR=$PWD/tmp
[ -d "$DDIR" ] || mkdir -p "$DDIR"
docker run -it --rm \
    --name tl_proxy \
    -v $PWD:/data/ro:ro \
    -v "$DDIR:/data/rw" \
    -p 8000:8000 \
    tar_like \
    python3 -mtar_like.proxy -b /data/rw/recv-test