#!/bin/bash

set -x
set -e

# for haproxied setup use for example
#### haproxy.cfg
# frontend  https
#    bind <YourIp>:<YourPort> ssl crt /etc/haproxy/<yourCertBundleWithKey>.pem
#    option forwardfor
#    acl PATH_tar path_beg -i /tar/
#    use_backend tar_like if PATH_tar
# backend tar_like
#    balance     roundrobin
#    server      tar_like 127.0.0.1:8001 check
####
# export LOCAL_BIND:=127.0.0.1:8001
#
# the default binds 0.0.0.0:8000
# this works with docker upload on the same host
# in general the 0.0.0.0 is unsafe !!!
: ${LOCAL_BIND:=8000}

: ${SDIR:=$PWD}
[ -d "$SDIR" ] || exit -1

: ${DDIR:=$PWD/tmp}
[ -d "$DDIR" ] || mkdir -p "$DDIR"

: ${UDIR:=/data/rw/recv-test}

docker run -it --rm \
    --name tl_proxy \
    -v "$SDIR:/data/ro:ro" \
    -v "$DDIR:/data/rw" \
    -p ${LOCAL_BIND}:8000 \
    tar_like \
    python3 -mtar_like.proxy -b "$UDIR"