from aig import AIG
from aig_io import read_aiger

def read_cex(f):
    
    f.readline()
    f.readline()
    
    latch_values = [int(c) for c in f.readline().strip()]
    pi_values = []
    
    for line in f:
        
        line = line.strip()
        
        if line=='.':
            break
            
        pi_values.append([int(c) for c in line])
    
    return latch_values, pi_values

class pyaig_values(object):

    def __init__(self, aig):
        self.m = {aig.get_const0(): 0}

    def __getitem__(self, f):
        return self.m[AIG.get_positive(f)] ^ AIG.is_negated(f)

    def __setitem__(self, f, v):
        self.m[AIG.get_positive(f)] = v ^ AIG.is_negated(f)

    def iteritems(self):
        return self.m.iteritems()

def simulate(aig, latch_values, pi_values):

    simulation = []

    values = pyaig_values(aig)

    for l, v in zip(aig.get_latches(), latch_values):
        values[l] = v
        
    for k in xrange(len(pi_values)):

        for f, v in zip(aig.get_pis(), pi_values[k]):
            values[f] = v

        for f in aig.get_and_gates():
            values[f] = values[aig.get_and_left(f)] & values[aig.get_and_right(f)]

        simulation.append( values )

        new_values = pyaig_values(aig)

        for l in aig.get_latches():
            new_values[l] = values[aig.get_next(l)]

        values = new_values
        
    return simulation

def print_cex( aig, simulation, symbols):

    V = ["0", "1", '?']
    
    maxlen = +max( len(sym) for sym in symbols.iterkeys() )
    
    for n, f in sorted(symbols.iteritems()):
        
        print "%-*s:"%(maxlen, n),

        for i in xrange(len(simulation)):
            v = simulation[i][f]
            v = str(v) if 0 <= v <= 1 else '?'
            print v,

        print

if __name__=="__main__":
    
    latch_values, pi_values = read_cex(open('/home/sterin/workspaces/dev/ltl_benchmarks/cex','r'))
    aig = read_aiger(open('/home/sterin/workspaces/dev/ltl_benchmarks/bc57-sensors__p0.ltl2smv.aig','r'))
    simulation = simulate(aig, latch_values, pi_values)
    
    symbols = { n:f for f, n in aig.iter_names() }
    symbols.update( (n,f) for _, f, n in aig.iter_po_names() )

    print_cex(aig, simulation, symbols)
    
    
    
    