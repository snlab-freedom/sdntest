#!/bin/bash

INTENT=$(sed 's/\$1/'$2'/;s/\$2/'$3'/' onos_intent.json)

curl -v -u onos:rocks -X POST -H 'Content-type: application/json' -d "$(echo $INTENT)" http://$1:8181/onos/v1/intents
