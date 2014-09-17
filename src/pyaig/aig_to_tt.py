from aig import AIG
from aig_io import read_aiger, write_aiger
from truthtables import truth_tables


class aig_to_tt_map(AIG.fmap):
    def __init__(self, m, fs):
        super(aig_to_tt_map, self).__init__(fs=fs, negate_if_negated=lambda tt,f: tt.negate_if(AIG.is_negated(f)), zero=m.const(0) )


def aig_to_tt(aig):

    m = truth_tables(aig.n_pis())
    M = aig_to_tt_map( m, ((aig.get_pi_by_id(i), m.var(i)) for i in xrange(aig.n_pis())) )

    for f, n in aig.construction_order_deref():

        if f in M:
            continue

        assert n.is_and(), 'tt_from_aig: only works on a combinational AIG'
        M[f] = M[n.get_left()] & M[n.get_right()]

    assert (aig.n_pos()%2) == 0
    return m, [ (M[aig.get_po_fanin(i*2)], M[aig.get_po_fanin(i*2+1)]) for i in xrange(aig.n_pos()/2) ]


def aig_to_tt_fname(fname):

    with open(fname, 'r') as f:
        aig = read_aiger(f)

    return aig_to_tt(aig)

if __name__=="__main__":

    N = 4

    aig = AIG()

    pis = [ aig.create_pi() for i in xrange(N) ]
    aig.create_po( aig.conjunction(pis) )
    aig.create_po( aig.create_and( aig.disjunction(pis), AIG.negate(aig.conjunction(pis)) ) )

    m, res = aig_to_tt(aig)

    for f,r in res:
        print 'f=', f, ' r=', r
