"""Custom topology example
s1---s2
|   /
|  /
| /
s3

Consist of three fixed core switches, and each core switches will connect to m hosts through n switches.

"""

import sys
from mininet.topo import Topo

CORE_NUMBER = 3

class TriangleStarTopo( Topo ):
    "Simple topology example."

    def build( self, m=1, n=1 ):
        """
        m: number of branches in each core switch.
        n: hop count between host and nearby core switche.
        """

        switch_count = 0
        host_count = 0
        core = []
        switch = []
        host = []

        for core in range(CORE_NUMBER):
            core.append( self.addSwitch( 'core%d' % (core+1) ) )
            switch_count += 1
        for core in range(CORE_NUMBER):
            self.addLink( switch[core], switch[(core+1) % CORE_NUMBER] )

            switch.append([])
            host.append([])
            for branch in range(m):
                switch[core].append([])
                for hop in range(n):
                    switch[core][branch].append( self.addSwitch( 'core%db%ds%d' % (core, branch, hop) ) )
                    switch_count += 1
                    if hop:
                        self.addLink( switch[core][branch][hop-1],
                                      switch[core][branch][hop] )
                    else:
                        self.addLink( switch[core][branch][hop],
                                      core[core] )
                host[core].append(self.addHost( 'core%dh%d' % (core, branch) ) )
                host_count += 1
                self.addLink( host[core][branch], switch[core][branch][hop] )
        sys.stdout.write("***** total_switches=%u *****" % (switch_count))
        sys.stdout.write("***** total_hosts=%u *****" % (host_count))
        sys.stdout.write("***** total_nodes=%u *****" % (switch_count + host_count))

topos = { 'tristar': ( lambda m,n: TriangleStarTopo(m, n) ) }
