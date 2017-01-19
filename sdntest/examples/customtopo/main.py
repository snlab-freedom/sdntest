#!/usr/bin/env python

"""
Test host-to-host intent and link failure recovery.
"""

import os
import sys
import json

from mininet.net import Mininet
from mininet.node import Node, RemoteController
from triangle import TriangleStarTopo
from mininet.log import info, setLogLevel

from select import poll, POLLIN
from time import time, sleep
from threading import Thread

class linkconfig(Thread):
    def __init__(self, net, src, dst, action, timeout):
        Thread.__init__(self)
        self.net = net
        self.src = src
        self.dst = dst
        self.action = action
        self.timeout = timeout

    def run(self):
        sleep(self.timeout)
        self.net.configLinkStatus(self.src, self.dst, self.action)

def startpings( host, targetips ):
    "Tell host to repeatedly ping targets"

    targetips = ' '.join( targetips )

    # Simple ping loop
    cmd = ( 'while true; do '
            ' for ip in %s; do ' % targetips +
            '  echo -n %s "->" $ip ' % host.IP() +
            '   `ping -c1 -w 1 $ip` ;'
            '  sleep 1;'
            ' done; '
            'done &' )

    info( '*** Host %s (%s) will be pinging ips: %s\n' %
          ( host.name, host.IP(), targetips ) )

    host.cmd( cmd )

def h2hintent( controller, host1, host2 ):
    "Add host-to-host intent."

    uuid = 'b9a13232-525e-4d8c-be21-cd65e3436034'

    intent = json.dumps({
        'intent:intent': {
            'intent:id': uuid,
            'intent:actions': [{'order': 2, 'allow': {}}],
            'intent:subjects': [
                {'order': 1, 'end-point-group': {'name': host1}},
                {'order': 2, 'end-point-group': {'name': host2}}
            ]
        }
    })
    cmd = ( 'curl -v -u admin:admin -X PUT '
            '-H "Content-type: application/json" '
            '-d \'%s\' ' % intent.strip() +
            'http://%s:8181/restconf/config/intent:intents/intent/%s' % (controller, uuid) )

    info( '*** Create intent: %s\n' % intent.strip() )

    os.system( cmd )

def test( controller, branch, hop, seconds):
    "Add host-to-host intent from controller and keep ping hosts."

    # Create network
    topo = TriangleStarTopo( branch, hop )
    net = Mininet( topo=topo,
                   controller=RemoteController,
                   build=False )
    net.addController( ip=controller )
    net.start()

    host1 = net.get('core1h1')
    host2 = net.get('core2h2')
    core1 = net.get('core1')
    core2 = net.get('core2')

    # Add host-to-host intent
    h2hintent( controller, host1.IP(), host2.IP() )

    # Create polling object
    fds = [ host.stdout.fileno() for host in [host1, host2] ]
    poller = poll()
    for fd in fds:
        poller.register( fd, POLLIN )

    # Start ping
    startpings( host1, [host2.IP()])
    endTime = time() + seconds

    # Emulate link failure
    linkconfig(net, core1.name, core2.name, 'down', seconds/3.).start()

    # Recover link
    linkconfig(net, core1.name, core2.name, 'up', 2*seconds/3.).start()

    # Monitor output
    while time() < endTime:
        readable = poller.poll(1000)
        for fd, _mask in readable:
            node = Node.outToNode[ fd ]
            info( '%s:' % node.name, node.monitor().strip(), '\n' )

    # Stop pings
    for host in net.hosts:
        host.cmd( 'kill %while' )

    net.stop()


if __name__ == '__main__':
    setLogLevel( 'info' )
    assert len(sys.argv) == 2
    test( sys.argv[1], branch=3, hop=4, seconds=10 )
