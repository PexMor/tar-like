#!/bin/bash

set -x
set -e

: ${UPLOAD_URL:=http://172.17.0.1:8000/tar}

: ${SDIR:=$PWD}
[ -d "$SDIR" ] || exit -1

: ${DDIR:=$PWD/tmp}
[ -d "$DDIR" ] || mkdir -p "$DDIR"

python3 -mtar_like.upload -u "${UPLOAD_URL}" -b $TARLIKE_S3_PFX --use-s3 "$@"

# EOF
