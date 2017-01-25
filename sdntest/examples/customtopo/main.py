#!/usr/bin/env python

"""
Test host-to-host intent and link failure recovery.
"""

import os
import sys
import json
import logging

from mininet.net import Mininet
from mininet.node import Node, RemoteController
from triangle import TriangleStarTopo
from mininet.log import info, output, setLogLevel, lg

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
        info( '*** Create a future task: config link between %s and %s %s after %.2f sec\n' % (self.src, self.dst, self.action, self.timeout) )
        sleep(self.timeout)
        info( '*** Config link (%s, %s) %s\n' % (self.src, self.dst, self.action.upper()) )
        self.net.configLinkStatus( self.src, self.dst, self.action )

def hostdiscovery( net ):
    "Start quick ping between pairs to make controller discover hosts"
    hosts = net.hosts
    hostNum = len(hosts)
    pings = []

    for i in range( (hostNum + 1)/2 ):
        ping_cmd = ['ping', '-n', '-i0.001', '-c4', hosts[(2*i+1)%hostNum].IP()]
        pings.append( hosts[2*i].popen( ping_cmd, stdout=PIPE, stderr=PIPE ) )
    for ping in pings:
        ping.wait()

def startping( host, targetip, timeout ):
    "Tell host to repeatedly ping targets"

    # Platform may need some time to discover hosts
    # time_for_hostprovider = 10
    # timeout += time_for_hostprovider

    # Simple ping loop
    cmd = ['ping', '-n', '-i0.001', '-w%d' % timeout, targetip]

    info( '*** Host %s (%s) will be pinging ips: %s\n' %
            ( host.name, host.IP(), targetip ) )

    # sleep(time_for_hostprovider)

    return host.popen( cmd, stdout=PIPE, stderr=PIPE,
                       universal_newlines=True )

def startiperf( server, client, timeout, rate ):
    "Start iperf server and client"

    # Platform may need some time to discover hosts
    # time_for_hostprovider = 10
    # cmd_pre = ['ping', '-n', '-i0.001', '-w%d' % time_for_hostprovider, client.IP()]
    # pre_proc = server.popen( cmd_pre, stdout=PIPE, stderr=PIPE )
    # pre_return = pre_proc.wait()
    # if pre_return:
    #     return None, None

    cmd1 = ['iperf', '-s', '-u']

    output( '*** Host %s (%s) will start an iperf server in udp mode\n' %
            ( server.name, server.IP() ) )

    server_proc = server.popen( cmd1, stdout=PIPE, stderr=PIPE,
                                universal_newlines=True )

    cmd2 = ['iperf', '-c', server.IP(), '-u', '-i1', '-b%dM' % rate, '-t%s' % timeout]

    info( '*** Host %s (%s) will start an iperf client to connect %s\n' %
            ( client.name, client.IP(), server.IP() ) )

    client_proc = server.popen( cmd2, stdout=PIPE, stderr=PIPE,
                                universal_newlines=True)

    return server_proc, client_proc

def h2hintent( controller, host1, host2, platform="odl" ):
    "Add host-to-host intent."
    # TODO: use urllib to replace popen curl

    intent = ""
    cmd = ""

    if "odl" == platform:
        mac1 = host1.MAC().split(':')
        mac2 = host2.MAC().split(':')
        uuid = ''.join(mac1[:4]) + '-' + ''.join(mac1[4:]) \
               + '-0000-0000-' + ''.join(mac2)

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
        return None

    info( '*** Create intent: %s\n' % intent.strip() )

    # os.system( cmd )
    return Popen( cmd.split(), stdout=PIPE, stderr=PIPE )

def h2hintents( controller, hostGroup1, hostGroup2, platform="odl" ):
    for host1 in hostGroup1:
        for host2 in hostGroup2:
            success = h2hintent( controller, host1, host2, platform )
            if not success:
                return success
    return True

def test( controller, branch=1, hop=1, seconds=10, intentNum=1, method='ping', platform='odl', rate=100 ):
    "Add host-to-host intent from controller and keep ping hosts."
    branch = int(branch)
    hop = int(hop)
    seconds = int(seconds)
    intentNum = int(intentNum)
    rate = int(rate)

    # Create network
    topo = TriangleStarTopo( branch, hop )
    net = Mininet( topo=topo,
                   controller=RemoteController,
                   build=False )
    net.addController( ip=controller )
    net.start()

    intentNum = min( branch, intentNum )

    # choose hosts in different core switches
    hostGroup1 = [ net.get('h%d' % (i+1)) for i in range(intentNum) ]
    hostGroup2 = [ net.get('h%d' % (branch+i+1)) for i in range(intentNum) ]
    host1 = hostGroup1[0]
    host2 = hostGroup2[0]
    # choose 2 core switches
    core1 = net.get('s1')
    core2 = net.get('s2')

    # Add host-to-host intent
    success = h2hintents( controller, hostGroup1, hostGroup2, platform )
    if not success:
        info( '*** Unknown test platform. End up the test...\n')
        net.stop()
        return

    # TODO: This is just a temporal solution. Need to be refined.
    # Waiting for feature loaded
    # sleep( 3 )

    hostdiscovery( net )
    # Platform may need some time to discover hosts
    sleep( 10 )

    # Start ping
    if 'ping' == method:
        proc = startping( host1, host2.IP(), seconds )
    elif 'iperf' == method:
        server_proc, proc = startiperf( host1, host2, seconds, rate )
    else:
        info( '*** Unknown test method. End up the test...\n' )
        net.stop()
        return

    if proc == None:
        info( '*** Fail to install intents :(\n' )
        net.stop()
        return

    timeout = seconds / 3.
    # Emulate link failure
    linkconfig( net, core1.name, core2.name, 'down', seconds/3. ).start()
    # output( '*** Create a future task: config link between %s and %s %s after %.2f sec\n' % (core1.name, core2.name, 'down', timeout) )
    # sleep( timeout )
    # net.configLinkStatus( core1.name, core2.name, 'down' )

    # Recover link
    linkconfig( net, core1.name, core2.name, 'up', 2*seconds/3. ).start()
    # output( '*** Create a future task: config link between %s and %s %s after %.2f sec\n' % (core1.name, core2.name, 'up', timeout) )
    # sleep( timeout )
    # net.configLinkStatus( core1.name, core2.name, 'up' )

    # Monitor output
    for line in iter(proc.stdout.readline, ""):
        output( line )
    # output( proc.stdout.read() )
    # output( proc.stderr.read() )

    # Stop pings
    proc.kill()

    net.stop()


if __name__ == '__main__':
    formatter = logging.Formatter('%(asctime)s | %(message)s')
    lg.handlers[-1].setFormatter( formatter )
    setLogLevel( 'output' )
    assert len(sys.argv) > 1
    controller = sys.argv[1]

    test( controller, *sys.argv[2:] )
