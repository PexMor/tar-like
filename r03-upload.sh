#!/bin/bash

set -x
set -e

: ${UPLOAD_URL:=http://172.17.0.1:8000/tar}

DDIR=$PWD/tmp
[ -d "$DDIR" ] || mkdir -p "$DDIR"
docker run -it --rm \
    --name tl_upload \
    -v $PWD:/data/ro:ro \
    -v "$DDIR:/data/rw" \
    tar_like \
    python3 -mtar_like.upload -u "${UPLOAD_URL}" -b /data/ro "$@"