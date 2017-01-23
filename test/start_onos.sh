#!/bin/bash

VERSION=$1
if [[ $VERSION ]]; then
  VERSION=:$VERSION
fi

docker run -ti -d -e 'ONOS_APPS=openflow,proxyarp' --name onos onosproject/onos$VERSION
