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
from mininet.log import info, output, setLogLevel

from select import poll, POLLIN
from time import time, sleep
from subprocess import Popen, PIPE
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
        output( '*** Create a future task: config link between %s and %s %s after %.2f sec\n' % (self.src, self.dst, self.action, self.timeout) )
        sleep(self.timeout)
        output( '*** Link (%s, %s) %s\n' % (self.src, self.dst, self.action.upper()) )
        output( '***** DEBUG: \n')
        output(self.src)
        output( '***** DEBUG: \n')
        output(self.dst)
        output( '***** END of DEBUG \n')
        self.net.configLinkStatus( self.src, self.dst, self.action )

def startping( host, targetip, timeout ):
    "Tell host to repeatedly ping targets"

    # Simple ping loop
    cmd = ['ping', '-n', '-i0.001', '-w%d' % timeout, targetip]

    output( '*** Host %s (%s) will be pinging ips: %s\n' %
          ( host.name, host.IP(), targetip ) )

    return host.popen( cmd, stdout=PIPE, stderr=PIPE )

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

    output( '*** Create intent: %s\n' % intent.strip() )

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

    host1 = net.get('h1')
    host2 = net.get('h2')
    core1 = net.get('s1')
    core2 = net.get('s1')

    # Add host-to-host intent
    h2hintent( controller, host1.IP(), host2.IP() )

    sleep( 3 )
    # Start ping
    proc = startping( host1, host2.IP(), seconds)

    timeout = seconds / 3.
    # Emulate link failure
    # linkconfig( net, core1.name, core2.name, 'down', seconds/3. ).start()
    output( '*** Create a future task: config link between %s and %s %s after %.2f sec\n' % (core1.name, core2.name, 'down', timeout) )
    sleep( timeout )
    net.configLinkStatus( core1.name, core2.name, 'down' )

    # Recover link
    # linkconfig( net, core1.name, core2.name, 'up', 2*seconds/3. ).start()
    output( '*** Create a future task: config link between %s and %s %s after %.2f sec\n' % (core1.name, core2.name, 'up', timeout) )
    sleep( timeout )
    net.configLinkStatus( core1.name, core2.name, 'up' )

    # Monitor output
    output( proc.stdout.read() )
    output( proc.stderr.read() )

    # Stop pings
    proc.kill()

    net.stop()


if __name__ == '__main__':
    setLogLevel( 'output' )
    assert len(sys.argv) == 2
    test( sys.argv[1], branch=3, hop=4, seconds=10 )
