#!/bin/bash

set -x
set -e

: ${SDIR:=$PWD}
[ -d "$SDIR" ] || exit -1

: ${DDIR:=$PWD/tmp}
[ -d "$DDIR" ] || mkdir -p "$DDIR"

: ${UDIR:=/data/rw/recv-test}

docker run -it --rm \
    --name tl_upload \
    -v "$SDIR:/data/ro:ro" \
    -v "$DDIR:/data/rw" \
    tar_like \
    python3 -mtar_like.check -b "$UDIR"