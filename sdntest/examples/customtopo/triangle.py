"""Custom topology example
s1---s2
|   /
|  /
| /
s3

Consist of three fixed core switches, and each core switches will connect to m hosts through n switches. 

"""

from mininet.topo import Topo
from optparse import OptionParser

class MyTopo( Topo ):
    "Simple topology example."

#    def __init__( self ):
    def build( self, m=1, n=1 ):
        "Create custom topo."

        # Initialize topology
        #Topo.__init__( self )

        switch_index = 1
        host_index = 1
#        core = ['space']
        switch = ['space']
        host = ['space']

#        parser = OptionParser()
#        parser.add_option("-m", action="store", type="int", dest="m")
#        parser.add_option("-n", action="store", type="int", dest="n")
#        (options, args) = parser,parse_args()
#        print options.m
#        print options.n
        #m = 2
        #n = 2
        CORE_NUMBER = 3

        for i in range(1, CORE_NUMBER+1):
            switch.append(self.addSwitch( 's'+str(switch_index) ))
            switch_index = switch_index + 1
        for k in range(1, CORE_NUMBER+1):
            if (k==CORE_NUMBER):
                self.addLink( switch[k], switch[1] )
            else:
                self.addLink( switch[k], switch[k+1] )
            
            for i in range(1,m+1):
                for j in range(1,n+1):
                    switch.append(self.addSwitch( 's'+str(switch_index) ))
                    if (j==1):
                        self.addLink( switch[k],switch[switch_index] )
                    else:
                        self.addLink( switch[switch_index-1],switch[switch_index])
                    switch_index = switch_index + 1
                host.append(self.addHost( 'h'+str(host_index)))
                self.addLink( host[host_index], switch[switch_index-1])
                host_index = host_index + 1
        print "total_switches=%u"%(switch_index-1+3)
        print "total_hosts=%u"%(host_index-1)
        print "total_nodes=%u"%(switch_index-1+3+host_index-1)

topos = { 'mytopo': ( lambda m,n:MyTopo(m, n) ) }
