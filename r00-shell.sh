#!/bin/bash

DDIR=$PWD/tmp
[ -d "$DDIR" ] || mkdir -p "$DDIR"
docker run -it --rm \
    --name tl_shell \
    -v $PWD:/data/ro:ro -v "$DDIR:/data/rw" \
    --entrypoint /bin/bash \
    tar_like
