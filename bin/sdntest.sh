#!/bin/bash

DOCKER_NAME=test-controller

echoerr() {
    echo "$@" 1>&2;
}

bootstrap_odl() {
    if [[ $RELEASE_TAG ]]; then
        RELEASE_TAG=4.4.0
    fi
    docker run -ti -d \
           --name $DOCKER_NAME \
           opendaylight/odl:$RELEASE_TAG /opt/opendaylight/bin/karaf
    ODL_FEATURES=$APPS
    docker exec -ti $DOCKER_NAME /opt/opendaylight/bin/client -u karaf "feature:install $ODL_FEATURES"
}

bootstrap_onos() {
    if [[ $RELEASE_TAG ]]; then
        RELEASE_TAG=latest
    fi
    ONOS_APPS=openflow
    ONOS_APPS=${APPS:-$ONOS_APPS}
    docker run -ti -d \
           -e "ONOS_APPS=$ONOS_APPS" \
           --name $DOCKER_NAME \
           onosproject/onos:$RELEASE_TAG
}

bootstrap_platform() {
    case $PLATFORM in
        odl)
            bootstrap_odl $RELEASE_TAG
            ;;
        onos)
            bootstrap_onos $RELEASE_TAG
            ;;
        *)
            echoerr "ERROR: Unknown or unsupported SDN controller platform: $PLATFORM"
            ;;
    esac
}

bootstrap_mininet() {
    MN_SCRIPT=$1
    CONTROLLER_IP=$(docker inspect onos | jq '.[] | .NetworkSettings | .IPAddress' | sed 's/"//g')
    docker run -ti \
           --privileged=true \
           --cap-add NET_ADMIN \
           --cap-add SYS_MODULE \
           -v /lib/modules:/lib/modules \
           --name $DOCKER_MININET \
           ciena/mininet $MN_SCRIPT $CONTROLLER_IP
}

kill_platform() {
    docker stop $DOCKER_NAME
    docker rm $DOCKER_NAME
}

usage() {
    echo "Usage: nettest [OPTION] <testcase_dir>"
}

TEST_CASE=$1

if [[ ! -d $TEST_CASE ]]; then
    usage
    exit 0
fi

# Switch current workspace
cd $TEST_CASE

TEST_CONFIG="config.json"

if [ ! -f $TEST_CONFIG ]; then
    echoerr "ERROR: $TEST_CONFIG not found!"
    exit 127
fi

REPEAT=$(jq '.repeat' $TEST_CONFIG)
PLATFORM=$(jq '.platform' $TEST_CONFIG)
RELEASE_TAG=$(jq '.release' $TEST_CONFIG)

APPS=$(jq '.apps' $TEST_CONFIG | sed 's/"//g')

WAITING_TIME=$(jq '.waiting' $TEST_CONFIG | sed 's/null//')
WAITING_TIME=${WAITING_TIME:-15}

NET_WORKFLOW=$(jq '.workflow' $TEST_CONFIG)

for i in `seq 1 $REPEAT`; do
    bootstrap_platform
    sleep $WAITING_TIME
    bootstrap_mininet $NET_WORKFLOW
    kill_platform
done
