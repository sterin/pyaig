from . aig import AIG
from . aig_io import read_aiger, write_aiger
from . truthtables import truth_tables


class aig_to_tt_map(AIG.fmap):
    def __init__(self, m, fs=()):
        super(aig_to_tt_map, self).__init__(fs=fs, negate_if_negated=lambda tt,f: tt.negate_if(AIG.is_negated(f)), zero=m.const(0) )


def aig_cut_to_tt(m, aig, f, cut):
    """ Build a truth table for a node 'f' and a cut 'cut'.
    >>> aig = AIG()
    >>> f = aig.conjunction([ aig.create_pi() for _ in xrange(6) ])
    >>> m = truth_tables(4)
    >>> print aig_cut_to_tt(m, aig, AIG.negate(f), [3, 5, 6, 9, 10, 12])
    !x0 + x1 + !x2 + !x3
    """

    M = aig_to_tt_map(m)

    for c in cut[:-m.N]:
        M[c] = m.const(0)

    for i, c in enumerate(cut[-m.N:]):
        M[c] = m.var(i)

    def rec(f):

        if f in M:
            return M[f]

        if AIG.is_negated(f):
            return ~rec(AIG.negate(f))

        assert not AIG.is_negated(f)
        assert aig.is_and(f)

        return rec( aig.get_and_left(f) ) & rec( aig.get_and_right(f) )

    return rec(f)


def aig_to_tt(aig):
    """
    >>> aig = AIG()
    >>> pis = [ aig.create_pi() for _ in xrange(4) ]
    >>> po0 = aig.create_po( aig.conjunction(pis) )
    >>> po1 = aig.create_po( aig.disjunction(pis) )
    >>> m, tts = aig_to_tt(aig)
    >>> for f, r in tts:
    ...     print f, '  -  ' ,r
    x0&x1&x2&x3   -   x0 + x1 + x2 + x3
    """
    assert aig.n_latches() == 0, 'aig_to_tt: combinational AIG expected'
    assert aig.n_buffers() == 0, 'aig_to_tt: AIG contains unexpected buffers'

    m = truth_tables(aig.n_pis())
    M = aig_to_tt_map( m, ((aig.get_pi_by_id(i), m.var(i)) for i in xrange(aig.n_pis())) )

    for f, n in aig.construction_order_deref():

        if f in M:
            continue

        M[f] = M[n.get_left()] & M[n.get_right()]

    assert (aig.n_pos()%2) == 0
    return m, [ (M[aig.get_po_fanin(i*2)], M[aig.get_po_fanin(i*2+1)]) for i in xrange(aig.n_pos()/2) ]


def aig_to_tt_fname(fname):

    with open(fname, 'r') as f:
        aig = read_aiger(f)

    return aig_to_tt(aig)


if __name__=="__main__":

    import doctest
    doctest.testmod()
