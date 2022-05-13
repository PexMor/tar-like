#!/bin/bash

set -x
set -e

: ${SDIR:=$PWD}
[ -d "$SDIR" ] || exit -1
: ${DDIR:=$PWD/tmp}
[ -d "$DDIR" ] || mkdir -p "$DDIR"

docker run -it --rm \
    --name tl_index \
    -v "$SDIR:/data/ro:ro" \
    -v "$DDIR:/data/rw" \
    tar_like \
    python3 -mtar_like.index -b /data/ro -x .git -x tmp -x __pycache__ -c