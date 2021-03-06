#!/bin/bash

set -x
set -e

: ${UPLOAD_URL:=http://172.17.0.1:8000/tar}

: ${SDIR:=$PWD}
[ -d "$SDIR" ] || exit -1

: ${DDIR:=$PWD/tmp}
[ -d "$DDIR" ] || mkdir -p "$DDIR"

# CNET="--network proxy"

: ${EX_PYCACERT:=~/.python-cacert.pem}
: ${IN_PYCACERT:=/ca-cert.pem}

if [ -f "$EX_PYCACERT" ]; then
    PYCERT_PARAM="-e SSL_CERT_FILE=$IN_PYCACERT -v $EX_PYCACERT:/ca-cert.pem:ro"
fi

docker run -it --rm \
    --name tl_upload \
    -e TARLIKE_S3_BUCKET \
    -e TARLIKE_S3_ENDPOINT \
    -e TARLIKE_S3_TLS_VERIFY \
    -e AWS_ACCESS_KEY_ID \
    -e AWS_SECRET_ACCESS_KEY \
    -e AWS_CA_BUNDLE \
    -e http_proxy \
    -e https_proxy \
    $PYCERT_PARAM \
    $CNET \
    -v "$SDIR:/data/ro:ro" \
    -v "$DDIR:/data/rw" \
    tar_like \
    python3 -mtar_like.upload -u "${UPLOAD_URL}" -b $TARLIKE_S3_PFX --use-s3 "$@"

# EOF
