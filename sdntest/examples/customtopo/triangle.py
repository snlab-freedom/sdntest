"""Custom topology example
s1---s2
|   /
|  /
| /
s3

Consist of three fixed core switches, and each core switches will connect to m hosts through n switches.

"""

from mininet.topo import Topo

CORE_NUMBER = 3

class TriangleStarTopo( Topo ):
    "Simple topology example."

    def build( self, m=1, n=1 ):
        """
        m: number of branches in each core switch.
        n: hop count between host and nearby core switche.
        """

        self.hostNum = 0
        self.switchNum = 0
        core = []
        switch = []
        host = []

        for c in range(CORE_NUMBER):
            self.switchNum += 1
            core.append( self.addSwitch( 's%d' % self.switchNum ) )
        for c in range(CORE_NUMBER):
            self.addLink( core[c], core[(c+1) % CORE_NUMBER] )

            switch.append( [] )
            host.append( [] )
            for b in range(m):
                switch[c].append( [] )
                for h in range(n):
                    self.switchNum += 1
                    switch[c][b].append( self.addSwitch( 's%d' % self.switchNum ) )
                    if h > 0:
                        self.addLink( switch[c][b][h-1],
                                      switch[c][b][h] )
                    else:
                        self.addLink( switch[c][b][h],
                                      core[c] )
                self.hostNum += 1
                host[c].append( self.addHost( 'h%d' % self.hostNum ) )
                if n > 0:
                    self.addLink( host[c][b], switch[c][b][h] )
                else:
                    self.addLink( host[c][b], core[c] )

topos = { 'tristar': TriangleStarTopo }
