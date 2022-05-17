#!/bin/bash

TLS_HOST="${TARLIKE_S3_BUCKET}.${TARLIKE_S3_ENDPOINT#*//}"
openssl s_client -proxy 127.0.0.1:3128 -servername ${TLS_HOST} -connect ${TLS_HOST}:443 -showcerts -crlf </dev/null
echo "---"
