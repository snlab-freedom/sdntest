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

def startiperf( server, client, timeout ):
    "Start iperf server and client"

    cmd1 = ['iperf', '-s', '-u']

    output( '*** Host %s (%s) will start an iperf server in udp mode\n' %
            ( server.name, server.IP() ) )

    server_proc = server.popen( cmd1, stdout=PIPE, stderr=PIPE )

    cmd2 = ['iperf', '-c', server.IP(), '-u', '-i1', '-t%s' % timeout]

    output( '*** Host %s (%s) will start an iperf client to connect %s\n' %
            ( client.name, client.IP(), server.IP() ) )

    client_proc = server.popen( cmd2, stdout=PIPE, stderr=PIPE )

    return server_proc, client_proc

def h2hintent( controller, host1, host2, platform="odl" ):
    "Add host-to-host intent."

    intent = ""
    cmd = ""

    if "odl" == platform:
        uuid = 'b9a13232-525e-4d8c-be21-cd65e3436034'

        intent = json.dumps({
            'intent:intent': {
                'intent:id': uuid,
                'intent:actions': [{'order': 2, 'allow': {}}],
                'intent:subjects': [
                    {'order': 1, 'end-point-group': {'name': host1.IP()}},
                    {'order': 2, 'end-point-group': {'name': host2.IP()}}
                ]
            }
        })
        cmd = ( 'curl -v -u admin:admin -X PUT '
                '-H "Content-type: application/json" '
                '-d \'%s\' ' % intent.strip() +
                'http://%s:8181/restconf/config/intent:intents/intent/%s' % (controller, uuid) )
    elif "onos" == platform:
        intent = json.dumps({
            'type': 'HostToHostIntent',
            'id': '0x0',
            'appId': 'org.onosproject.cli',
            'one': host1.MAC() + '/-1',
            'two': host2.MAC() + '/-1'
        })
        cmd = ( 'curl -v -u onos:rocks -X POST '
                '-H "Content-type: application/json" '
                '-d \'%s\' ' % intent.strip() +
                'http://%s:8181/onos/v1/intents' % controller )
    else:
        return False

    output( '*** Create intent: %s\n' % intent.strip() )

    os.system( cmd )
    return True

def test( controller, branch, hop, seconds, method='ping', platform='odl' ):
    "Add host-to-host intent from controller and keep ping hosts."

    # Create network
    topo = TriangleStarTopo( branch, hop )
    net = Mininet( topo=topo,
                   controller=RemoteController,
                   build=False )
    net.addController( ip=controller )
    net.start()

    # choose hosts in different core switches
    host1 = net.get('h1')
    host2 = net.get('h%d' % (branch+1))
    # choose 2 core switches
    core1 = net.get('s1')
    core2 = net.get('s2')

    # Add host-to-host intent
    success = h2hintent( controller, host1, host2, platform )
    if not success:
        output( '*** Unknown test platform. End up the test...\n')
        net.stop()
        return

    # TODO: This is just a temporal solution. Need to be refined.
    # Waiting for feature loaded
    sleep( 3 )

    # Start ping
    if 'ping' == method:
        proc = startping( host1, host2.IP(), seconds )
    elif 'iperf' == method:
        server_proc, proc = startiperf( host1, host2, seconds )
    else:
        output( '*** Unknown test method. End up the test...\n' )
        net.stop()
        return

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
    assert len(sys.argv) > 1
    controller = sys.argv[1]

    test( sys.argv[1], 3, 4, 10, *sys.argv[2:] )
