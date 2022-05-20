#!/bin/bash

NAME=haproxy

# Note: to create cert you can use demo-cfssl/mkCert.sh
# and then run `cp_cert_n_key.sh`
docker kill $NAME
docker rm $NAME
docker run -d \
    --name $NAME \
    --network container:tl_proxy \
    -v $PWD/etc-haproxy:/usr/local/etc/haproxy:ro \
    haproxy:lts-alpine
