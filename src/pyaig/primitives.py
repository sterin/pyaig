from aig import AIG
from aig_io import write_aiger

def counter(aig, width, en=AIG.get_const1(), rst=AIG.get_const0()):

    latches = [ aig.create_latch() for _ in xrange(width) ]

    prev_all_ones = aig.get_const1()

    for ll in latches:

        next = aig.create_xor( ll, aig.create_and(en, prev_all_ones) )
        next = aig.create_ite( rst, AIG.get_const0(), next )

        aig.set_next(ll, next)

        prev_all_ones = aig.create_and(prev_all_ones, ll)

    return latches

def equals(aig, X, Y):
    assert len(X) == len(Y)
    return aig.conjunction( aig.create_iff(x, y) for x,y in zip(X,Y) )

def less_than(aig, X, Y):

    assert len(X) == len(Y)

    if len(X)==0:
        return AIG.get_const0()

    return aig.create_or(
        aig.create_and( AIG.negate(X[0]), Y[0] ),
        aig.create_and( aig.create_iff(X[0],Y[0]), less_than(aig, X[1:], Y[1:]))
    )

def less_than_equal(aig, X, Y):

    assert len(X) == len(Y)

    if len(X)==0:
        return AIG.get_const1()

    return aig.create_or(
        aig.create_and( AIG.negate(X[0]), Y[0] ),
        aig.create_and( aig.create_iff(X[0],Y[0]), less_than_equal(aig, X[1:], Y[1:]))
    )

_lfsr_taps = {
    2:[1, 2],
    4:[3, 4],
    8:[4, 5, 6, 8],
    16:[11, 13, 14, 16],
    32:[25, 26, 30, 32],
    64:[60, 61, 63, 64],
}

def lfsr(aig, width, init=None):

    init = [ AIG.INIT_NONDET ] * width if init is None else init

    L = [aig.create_latch(init=init[i]) for i in xrange(width) ]

    for i in xrange(1, width):
        aig.set_next(L[i], L[i-1])

    aig.set_next( L[0], aig.large_xor( L[i-1] for i in _lfsr_taps[width] ) )

    return L

if __name__=='__main__':

    for n in _lfsr_taps.iterkeys():

        fname = 'lfsr_%02d.aig'%n

        aig = AIG()

        L = lfsr(aig, n)

        # j_po = aig.create_po(L[0], po_type=AIG.JUSTICE)
        # aig.create_justice([j_po])

        aig.create_pi()

        aig.create_po(L[0], po_type=AIG.BAD_STATES)
        # for i in xrange(n):
        #     aig.create_po(L[i], po_type=AIG.BAD_STATES)

        with open(fname, 'w') as f:
            print fname
            write_aiger(aig, f)
