#!/bin/bash

set -x
set -e

: ${SDIR:=$PWD}
[ -d "$SDIR" ] || exit -1
: ${DDIR:=$PWD/tmp}
[ -d "$DDIR" ] || mkdir -p "$DDIR"

docker run -it --rm \
    --name tl_index \
    -e TARLIKE_S3_BUCKET \
    -e TARLIKE_S3_ENDPOINT \
    -e TARLIKE_S3_TLS_VERIFY \
    -e AWS_ACCESS_KEY_ID \
    -e AWS_SECRET_ACCESS_KEY \
    -e AWS_CA_BUNDLE \
    -v "$SDIR:/data/ro:ro" \
    -v "$DDIR:/data/rw" \
    tar_like \
    python3 -mtar_like.index -b /data/ro -x .git -x tmp -x __pycache__ -c "$@"

# EOF
