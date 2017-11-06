from __future__ import print_function
from future.utils import iteritems
from past.builtins import xrange

from .aig import AIG
from .aig_io import read_aiger


def filter_lines(f):

    for line in f:

        line = line.strip()

        if not line:
            continue

        elif line.startswith(b'u'):
            continue

        elif line.startswith(b'c'):
            continue

        yield line


def read_cex(f):

    V = { b'0': 0, b'1':1, 0:0, 1:0, '0':0, '1':1, ord('0'):0, ord('1'):1 }

    result = None
    prop = None

    latch_values = None
    pi_values = []

    for line in filter_lines(f):

        if result is None:
            result = line

        elif prop is None:
            prop = line

        elif line=='.':
            break

        elif latch_values is None:
            latch_values = [V[c] for c in line]

        else:
            pi_values.append([V[c] for c in line])

    return latch_values, pi_values


class pyaig_values(object):

    def __init__(self, aig):
        self.m = {aig.get_const0(): 0}

    def __getitem__(self, f):
        return self.m[AIG.get_positive(f)] ^ AIG.is_negated(f)

    def __setitem__(self, f, v):
        self.m[AIG.get_positive(f)] = v ^ AIG.is_negated(f)

    def iteritems(self):
        return iteritems(self.m)


def simulate(aig, latch_values, pi_values):

    simulation = []

    values = pyaig_values(aig)

    assert len(latch_values) == aig.n_latches()

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

    maxlen = +max( len(sym) for sym in symbols )
    
    for n, f in sorted(iteritems(symbols)):
        
        print("%-*s:"%(maxlen, n), end='')

        for i in xrange(len(simulation)):
            v = simulation[i][f]
            v = str(v) if 0 <= v <= 1 else '?'
            print(v, end='')

        print()


if __name__=="__main__":

    from . import primitives

    # create counter AIG

    aig = AIG()

    latches = primitives.counter(aig, 3, aig.create_pi("enable"))

    for l in latches:
        aig.create_po(l)

    # counter example

    CEX = b"""
        b0
        1
        000
        0
        1
        0
        1
        1
        1
        1
        1
        1
        1
        1
        1
    """

    import io
    latch_values, pi_values = read_cex(io.BytesIO(CEX))

    print(latch_values, pi_values)

    # set names

    for po_id, po_fanin, po_type in aig.get_pos():
        aig.set_name(aig.get_po_fanin(po_id), 'L%d'%po_id)

    # simulate

    simulation = simulate(aig, latch_values, pi_values)
    
    symbols = { n:f for f, n in aig.iter_names() }
    symbols.update( (n,f) for _, f, n in aig.iter_po_names() )

    # print CEX

    print_cex(aig, simulation, symbols)
