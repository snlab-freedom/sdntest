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

        for c in range(CORE_NUMBER):
            core.append( self.addSwitch( 'core%d' % (c+1) ) )
            switch_count += 1
        for c in range(CORE_NUMBER):
            self.addLink( core[c], core[(c+1) % CORE_NUMBER] )

            switch.append([])
            host.append([])
            for b in range(m):
                switch[c].append([])
                for h in range(n):
                    switch[c][b].append( self.addSwitch( 'core%db%ds%d' % (c+1, b+1, h+1) ) )
                    switch_count += 1
                    if h:
                        self.addLink( switch[c][b][h-1],
                                      switch[c][b][h] )
                    else:
                        self.addLink( switch[c][b][h],
                                      core[c] )
                host[c].append(self.addHost( 'core%dh%d' % (c+1, b+1) ) )
                host_count += 1
                self.addLink( host[c][b], switch[c][b][h] )
        sys.stdout.write("***** total_switches=%u *****\n" % (switch_count))
        sys.stdout.write("***** total_hosts=%u *****\n" % (host_count))
        sys.stdout.write("***** total_nodes=%u *****\n" % (switch_count + host_count))

topos = { 'tristar': ( lambda m,n: TriangleStarTopo(m, n) ) }
