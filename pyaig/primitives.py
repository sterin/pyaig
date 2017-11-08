from __future__ import print_function

import itertools
from past.builtins import xrange
from future.moves.itertools import zip_longest

from .aig import AIG
from .aig_io import write_aiger


def _bin(x):
    """
    >>> _bin(0)
    []
    >>> _bin(1)
    [1]
    >>> _bin(5)
    [1, 0, 1]
    """
    def f(x):
        while x>0:
            yield x % 2
            x = x // 2
    return list(f(x))


def _dec(A):
    """
    >>> _dec([])
    0
    >>> _dec([1])
    1
    >>> _dec([1, 0, 1])
    5
    """
    sum = 0
    for i, a in enumerate(A):
        sum += a*(1 << i)
    return sum
    

def group(iterable, N, fillvalue=None):
    """
    >>> list(group((), 3, fillvalue=-1))
    []
    >>> list(group(xrange(6), 3, fillvalue=-1))
    [(0, 1, 2), (3, 4, 5)]
    >>> list(group(xrange(7), 3, fillvalue=-1))
    [(0, 1, 2), (3, 4, 5), (6, -1, -1)]
    """
    iterable = iter(iterable)
    try:
        while True:
            cur = []
            for i in xrange(N):
                cur.append( next(iterable) )
            yield tuple(cur)
    except StopIteration:
        if cur:
            yield tuple(cur + [fillvalue]*(N-len(cur)))
    

def full_adder(aig, a, b, c_in):
    """
    >>> for a, b, c in itertools.product((0, 1), repeat=3):
    ...     print( (a, b, c), full_adder(AIG(), a, b, c) )
    (0, 0, 0) (0, 0)
    (0, 0, 1) (1, 0)
    (0, 1, 0) (1, 0)
    (0, 1, 1) (0, 1)
    (1, 0, 0) (1, 0)
    (1, 0, 1) (0, 1)
    (1, 1, 0) (0, 1)
    (1, 1, 1) (1, 1)
    """
    s = aig.large_xor( (a, b, c_in) )
    c = aig.disjunction( (aig.create_and(c_in, a), aig.create_and(c_in, b), aig.create_and(a, b)) )

    return s, c


def carry_chain_adder(aig, A, B, c_in=AIG.get_const0()):
    """
    >>> list(carry_chain_adder(AIG(), _bin(0), _bin(7), 1))
    [0, 0, 0, 1]
    >>> list(carry_chain_adder(AIG(), _bin(6), _bin(7), 1))
    [0, 1, 1, 1]
    """
    for a, b in zip_longest(A, B, fillvalue=AIG.get_const0()):
        s, c_in = full_adder(aig, a, b, c_in)
        yield s

    yield c_in


def carry_lookahead_adder(aig, A, B, c=AIG.get_const0()):
    """
    >>> _dec(carry_lookahead_adder(AIG(), _bin(0), _bin(7), 1))
    8
    >>> _dec(carry_lookahead_adder(AIG(), _bin(6), _bin(7), 1))
    14
    """
    for a, b in zip_longest(A, B, fillvalue=AIG.get_const0()):

        s = aig.large_xor((a, b, c))
        g = aig.create_and(a, b)
        p = aig.create_or(a, b)
        c = aig.create_or(g, aig.create_and(p, c))

        yield s

    yield c


def carry_save_adder(aig, A, B, C):
    """
    >>> list(carry_save_adder(AIG(), _bin(6), _bin(7), _bin(5)))
    [[0, 0, 1], [0, 1, 1, 1]]
    """
    X = _bin(0)
    Y = [ AIG.get_const0() ]

    for a, b, c in zip_longest(A, B, C, fillvalue=AIG.get_const0()):
        s, c_out = full_adder(aig, a, b, c)
        X.append(s)
        Y.append(c_out)
    
    return X, Y


def carry_save_adder_tree(aig, operands):
    """
    >>> _dec(carry_save_adder_tree(AIG(), (_bin(6), _bin(7), _bin(5))))
    18
    """
    def iteration(ops):
        for A in group(operands, 3, fillvalue=[]):
            A = [ a for a in A if a ]
            if len(A) == 1:
                yield A[0]
            elif len(A) == 2:
                yield A[0]
                yield A[1]
            elif len(A) == 3:
                X, Y = carry_save_adder(aig, *A)
                yield X
                yield Y

    operands = list(operands)

    while len(operands) > 2:
        operands = list(iteration(operands))

    return carry_lookahead_adder(aig, *operands)


def simple_multiplier(aig, A, B):
    """
    >>> _dec(simple_multiplier(AIG(), _bin(7), _bin(0)))
    0
    >>> _dec(simple_multiplier(AIG(), _bin(7), _bin(8)))
    56
    """
    def products():
        for i, a in enumerate(A):
            yield [ AIG.get_const0() ] * i + [ aig.create_and(a, b) for b in B ]

    return carry_save_adder_tree(aig, products())


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

    import string
    import click

    def make_inputs(aig, widths, names=string.ascii_lowercase):
        X = [ [] for _ in widths ]
        for w in xrange(max(widths)):
            for i in xrange(len(widths)):
                if w<widths[i]:
                    X[i].append( aig.create_pi('%s[%d]'%(names[i], w)) )
        return [ list(reversed(x)) for x in X ]

    def make_output(aig, outputs, name):
        for i, s in enumerate( reversed(list(outputs)) ):
            aig.create_po(s, '%s[%d]'%(name, i))

    @click.group()
    def cli():
        pass

    @cli.command()
    def doctest():
        import doctest
        doctest.testmod()


    @cli.command()
    @click.argument('aiger', type=click.File('wb'))
    @click.option('--carry/--no-carry')
    @click.argument('width', required=True, nargs=-1, type=int)
    def adder(aiger, width, carry):

        aig = AIG()

        c_in = AIG.create_pi('c_in') if carry else AIG.get_const0()

        X = make_inputs(aig, width)
        make_output(aig, carry_save_adder_tree(aig, X + ( [[c_in]] if carry else [] ) ), 's')

        write_aiger(aig, aiger)


    @cli.command()
    @click.argument('aiger', type=click.File('wb'))
    @click.argument('width', type=int)
    def multiplier(aiger, width):

        aig = AIG()

        X = make_inputs(aig, [width]*2)
        make_output(aig, simple_multiplier(aig, X[0], X[1]), 's')

        write_aiger(aig, aiger)


    @cli.command()
    @click.argument('width', type=int)
    @click.argument('aiger', type=click.File('wb'))
    def lfsr(width, aiger):

        aig = AIG()

        L = lfsr(aig, width)

        aig.create_pi()

        aig.create_po(L[0], po_type=AIG.BAD_STATES)
        # for i in xrange(n):
        #     aig.create_po(L[i], po_type=AIG.BAD_STATES)

        write_aiger(aig, aiger)


    cli()
