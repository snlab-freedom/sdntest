#!/bin/bash

docker run -ti --rm --cap-add NET_ADMIN --cap-add SYS_MODULE -v /lib/modules:/lib/modules -v $(pwd)/sdntest/examples/customtopo:/data --privileged ciena/mininet --custom /data/triangle.py --topo tristar,m=1,n=1 --controller=remote,ip=$1 --mac
