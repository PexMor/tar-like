#!/bin/bash

VIRT_URL="${TARLIKE_S3_ENDPOINT%//*}//${TARLIKE_S3_BUCKET}.${TARLIKE_S3_ENDPOINT#*//}"
# export CURL_CA_BUNDLE=$HOME/.python-cacert.pem
curl --cacert $HOME/.python-cacert.pem -v $VIRT_URL

echo "---"
