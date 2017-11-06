#!/usr/bin/python

# Author: Baruch Sterin <sterin@berkeley.edu>
# Simple Python AIG package

from past.builtins import xrange
from future.utils import iteritems

import itertools

class _Node(object):
    
    # Node types
    
    CONST0 = 0
    PI = 1
    LATCH = 2
    AND = 3
    BUFFER = 4
    
    # Latch initialization
    
    INIT_ZERO = 0
    INIT_ONE = 1
    INIT_NONDET = 2
    
    def __init__(self, node_type, left=0, right=0):
        self._type = node_type
        self._left = left
        self._right = right
    
    # creation
    
    @staticmethod
    def make_const0():
        return _Node(_Node.CONST0)
        
    @staticmethod
    def make_pi(pi_id):
        return _Node( _Node.PI, pi_id, 0)
    
    @staticmethod
    def make_latch(l_id, init, next=None):
        return _Node( _Node.LATCH, l_id, (init, next))
    
    @staticmethod
    def make_and(left, right):
        return _Node(_Node.AND, left, right)

    @staticmethod
    def make_buffer(buf_id, buf_in):
        return _Node(_Node.BUFFER, buf_id, buf_in)

    # query type
    
    def is_const0(self):
        return self._type == _Node.CONST0
    
    def is_pi(self):
        return self._type == _Node.PI
    
    def is_and(self):
        return self._type == _Node.AND
    
    def is_buffer(self):
        return self._type == _Node.BUFFER
    
    def is_latch(self):
        return self._type == _Node.LATCH
        
    def is_nonterminal(self):
        return self._type in (_Node.AND,_Node.BUFFER)
    
    def get_fanins(self):
        if self._type == _Node.AND:
            return [self._left, self._right]
        elif self._type == _Node.BUFFER:
            return [self._right]
        else:
            return []
    
    def get_seq_fanins(self):
        if self._type == _Node.AND:
            return [self._left, self._right]
        elif self._type == _Node.BUFFER:
            return [self._right]
        elif self._type == _Node.LATCH:
            return [self._right[1]]
        else:
            return []
    
    # AND gates
    
    def get_left(self):
        assert self.is_and()
        return self._left
    
    def get_right(self):
        assert self.is_and()
        return self._right
    
    # Buffer
    
    def get_buf_id(self):
        return self._left
        
    def get_buf_in(self):
        assert self.is_buffer()
        return self._right
        
    def set_buf_in(self, f):
        assert self.is_buffer()
        self._right = f
    
    def convert_buf_to_pi(self, pi_id):
        assert self.is_buffer()
        self._type = _Node.PI
        self._left = pi_id
        self._right = 0
    
    # PIs
    
    def get_pi_id(self):
        assert self.is_pi()
        return self._left
    
    def get_latch_id(self):
        assert self.is_latch()
        return self._left
    
    # Latches
    
    def get_init(self):
        assert self.is_latch()
        return self._right[0]
    
    def get_next(self):
        assert self.is_latch()
        return self._right[1]
    
    def set_init(self, init):
        assert self.is_latch()
        self._right = (init, self._right[1])
        
    def set_next(self, f):
        assert self.is_latch()
        self._right = (self._right[0], f)

    def __repr__(self):
        type = "ERROR"
        if self._type==_Node.AND:
            type = "AND"
        elif self._type==_Node.BUFFER:
            type = "BUFFER"
        elif self._type==_Node.CONST0:
            type = "CONST0"
        elif self._type==_Node.LATCH:
            type = "LATCH"
        elif self._type==_Node.PI:
            type = "PI"
        return "<pyaig.aig._Node _type=%s, _left=%s, _right=%s>"%(type, str(self._left), str(self._right))

class AIG(object):

    # map AIG nodes to AIG nodes, take negation into account

    class fmap(object):
        
        def __init__(self, fs=[], negate_if_negated=None, zero=None):

            self.negate_if_negated = negate_if_negated if negate_if_negated else AIG.negate_if_negated
            zero = AIG.get_const0() if zero is None else zero
            self.m = { AIG.get_const0():zero }
            if fs:
                self.update(fs)
            
        def __getitem__(self, f):
            return self.negate_if_negated( self.m[AIG.get_positive(f)], f )
            
        def __setitem__(self, f, g):
            self.m[ AIG.get_positive(f) ] = self.negate_if_negated(g, f)
            
        def __contains__(self, f):
            return AIG.get_positive(f) in self.m
            
        def __delitem__(self, f):
            del self.m[ AIG.get_positive(f) ]
        
        def iteritems(self):
            return iteritems(self.m)

        def update(self, fs):
            self.m.update( (AIG.get_positive(f), self.negate_if_negated(g, f)) for f,g in fs )
            
    class fset(object):
        
        def __init__(self, fs=[]):
            self.s = set( AIG.get_positive(f) for f in fs )
        
        def __contains__(self, f):
            return AIG.get_positive(f) in self.s
            
        def __len__(self):
            return len(self.s)
            
        def __iter__(self):
            return self.s.__iter__()
            
        def add(self, f):
            f = AIG.get_positive(f)
            res = f in self.s
            self.s.add(f)
            return res
            
        def remove(self, f):
            return self.s.remove( AIG.get_positive(f) )
                
    # PO types
    
    OUTPUT = 0
    BAD_STATES = 1
    CONSTRAINT = 2
    JUSTICE = 3
    FAIRNESS = 4

    # Latch initialization
    
    INIT_ZERO = _Node.INIT_ZERO
    INIT_ONE = _Node.INIT_ONE
    INIT_NONDET = _Node.INIT_NONDET

    def __init__(self, name=None, flat_name = (lambda n: n) ):
        self._name = name
        self._strash = {}
        self._pis = []
        self._latches = []
        self._buffers = []
        self._pos = []
        self._justice = []
        self._nodes = []
        self._name_to_id = {}
        self._id_to_name = {}
        self._name_to_po = {}
        self._po_to_name = {}
        self._flat_name = flat_name
        self._fanouts = {}
        
        self._nodes.append( _Node.make_const0() )

    def deref(self, f):
        return self._nodes[ f>>1 ]
    
    def name(self):
        return self._name
    
    # Create basic objects
    
    @staticmethod
    def get_const(c):
        if c:
            return AIG.get_const1()
        return AIG.get_const0()
        
    @staticmethod
    def get_const0():
        return 0
    
    @staticmethod
    def get_const1():
        return 1    
    
    def create_pi(self, name=None):
        pi_id = len(self._pis)
        n = _Node.make_pi(pi_id)
        fn = len(self._nodes)<<1
        
        self._nodes.append(n)
        self._pis.append( fn )
        
        if name is not None:
            self.set_name(fn, name)

        return fn
    
    def create_latch(self, name=None, init=INIT_ZERO, next=None):
        l_id = len(self._latches)
        n = _Node.make_latch(l_id, init, next)
        fn = len(self._nodes)<<1
        
        self._nodes.append(n)
        self._latches.append( fn )

        if name is not None:
            self.set_name(fn, name)
        
        return fn

    def create_and(self, left, right):
        if left<right:
            left, right = right, left
        
        if right==0:
            return 0
        
        if right==1:
            return left
        
        if left == right:
            return right
        
        if left == (right ^ 1):
            return 0
        
        key = (_Node.AND, left, right)
        
        if key in self._strash:
            return self._strash[key]
        
        f = len(self._nodes)<<1
        self._nodes.append( _Node.make_and(left, right) )
        
        self._strash[key] = f

        return f
        
    def create_buffer(self, buf_in=0, name=None):
        b_id = len(self._buffers)
        f = len(self._nodes)<<1
        
        self._nodes.append( _Node.make_buffer(b_id, buf_in) )
        self._buffers.append( f )
        
        if name is not None:
            self.set_name(f, name)
            
        return f
        
    def convert_buf_to_pi(self, buf):
        assert self.is_buffer(buf)
        assert self.get_buf_in(buf) >= 0
        
        n = self.deref(buf)
        self._buffers[n.get_buf_id()] = -1
        n.convert_buf_to_pi(len(self._pis))
        self._pis.append(buf)

    def create_po(self, f=0, name=None, po_type=OUTPUT ):
        po_id = len(self._pos)
        self._pos.append( (f, po_type) )
        
        if name is not None:
            self.set_po_name(po_id, name)
        
        return po_id
        
    def create_justice(self, po_ids):
        po_ids = list(po_ids)

        j_id = len(self._justice)

        for po_id in po_ids:
            assert self.get_po_type(po_id) == AIG.JUSTICE

        self._justice.append( po_ids )

        return j_id

    def remove_justice(self):
        
        for po_ids in self._justice:
            for po_id in po_ids:
                self.set_po_type(po_id, AIG.OUTPUT)
        
        self._justice = []
    
    # Names
    
    def set_name(self, f, name):
        assert not self.is_negated(f)
        assert name not in self._name_to_id
        assert f not in self._id_to_name

        self._name_to_id[name] = f
        self._id_to_name[f] = name
        
    def get_id_by_name(self, name):
        return self._name_to_id[name]
    
    def has_name(self, f):
        return f in self._id_to_name
    
    def name_exists(self, n):
        return n in self._name_to_id
    
    def get_name_by_id(self, f):
        return self._id_to_name[f]

    def remove_name(self, f):
        assert self.has_name(f)
        name = self.get_name_by_id(f)

        del self._id_to_name[f]
        del self._name_to_id[name]

    def iter_names(self):
        return iteritems(self._id_to_name)

    def fill_pi_names(self, replace=False, template="I_{}"):

        if replace:
            for pi in self.get_pis():
                if self.has_name(pi):
                    self.remove_name(pi)

        uid = 0

        for pi in self.get_pis():
            if not self.has_name(pi):
                while True:
                    name = template.format(uid)
                    uid += 1
                    if not self.name_exists(name):
                        break
                self.set_name(pi, name)

    # PO names
    
    def set_po_name(self, po, name):
        assert 0 <= po < len(self._pos)
        assert name not in self._name_to_po
        assert po not in self._po_to_name
        
        self._name_to_po[name] = po
        self._po_to_name[po] = name
        
    def get_po_by_name(self, name):
        return self._name_to_po[name]
    
    def po_has_name(self, po):
        return po in self._po_to_name

    def remove_po_name(self, po):
        assert self.po_has_name(po)
        name = self.get_name_by_po(po)
        del self._name_to_po[name]
        del self._po_to_name[po]
    
    def get_name_by_po(self, po):
        return self._po_to_name[po]

    def iter_po_names(self):
        return ( (po_id, self.get_po_fanin(po_id), po_name) for po_id, po_name in iteritems(self._po_to_name) )

    def fill_po_names(self, replace=False, template="O_{}"):

        if replace:
            self._name_to_po.clear()
            self._po_to_name.clear()

        po_names = set(name for _, _, name in self.iter_po_names())

        uid = 0
        for po_id, _, _ in self.get_pos():
            if not self.po_has_name(po_id):
                while True:
                    name = template.format(uid)
                    uid += 1
                    if name not in po_names:
                        break
                self.set_po_name(po_id, name)

    # Query IDs
        
    @staticmethod
    def get_id(f):
        return f >> 1
    
    def is_const0(self, f):
        n = self.deref(f)
        return n.is_const0()
    
    def is_pi(self, f):
        n = self.deref(f)
        return n.is_pi()
    
    def is_latch(self, f):
        n = self.deref(f)
        return n.is_latch()
    
    def is_and(self, f):
        n = self.deref(f)
        return n.is_and()

    def is_buffer(self, f):
        n = self.deref(f)
        return n.is_buffer()

    # PIs

    def get_pi_by_id(self, pi_id):
        return self._pis[ pi_id ]

    # Get/Set next for latches
    
    def set_init(self, l, init):
        assert not self.is_negated(l)
        assert self.is_latch(l)
        n = self.deref(l)
        n.set_init(init)
    
    def set_next(self, l, f):
        assert not self.is_negated(l)
        assert self.is_latch(l)
        n = self.deref(l)
        n.set_next(f)
    
    def get_init(self, l):
        assert not self.is_negated(l)
        assert self.is_latch(l)
        n = self.deref(l)
        return n.get_init()

    def get_next(self, l):
        assert not self.is_negated(l)
        assert self.is_latch(l)
        n = self.deref(l)
        return n.get_next()

    # And gate
    
    def get_and_fanins(self, f):
        assert self.is_and(f)
        n = self.deref(f)
        return (n.get_left(), n.get_right())

    def get_and_left(self, f):
        assert self.is_and(f)
        return self.deref(f).get_left()

    def get_and_right(self, f):
        assert self.is_and(f)
        return self.deref(f).get_right()

    # Buffer
    
    def get_buf_in(self, b):
        n = self.deref(b)
        return n.get_buf_in()
    
    def set_buf_in(self, b, f):
        assert b>f
        n = self.deref(b)
        return n.set_buf_in(f)

    def get_buf_id(self, b):
        n = self.deref(b)
        return n.get_buf_id()
        
    def skip_buf(self, b):
        while self.is_buffer(b):
            b = AIG.negate_if_negated( self.get_buf_in(b), b )
        return b

    # Fanins
    
    def get_fanins(self,f):
        n = self.deref(f)
        return n.get_fanins()
    
    def get_positive_fanins(self,f):
        n = self.deref(f)
        return (self.get_positive(fi) for fi in n.get_fanins())
    
    def get_positive_seq_fanins(self,f):
        n = self.deref(f)
        return (self.get_positive(fi) for fi in n.get_seq_fanins())
    
    # PO fanins

    def get_po_type(self, po):
        assert 0 <= po < len(self._pos)
        return self._pos[po][1]
    
    def get_po_fanin(self, po):
        assert 0 <= po < len(self._pos)
        return self._pos[po][0]
    
    def set_po_fanin(self, po, f):
        assert 0 <= po < len(self._pos)
        self._pos[po] = ( f, self._pos[po][1] )
    
    def set_po_type(self, po, po_type):
        assert 0 <= po < len(self._pos)
        self._pos[po] = ( self._pos[po][0], po_type )
    
    # Justice
    
    def get_justice_pos(self, j_id):
        assert 0 <= j_id < len(self._justice)
        return ( po for po in self._justice[j_id] )

    def set_justice_pos(self, j_id, po_ids):
        assert 0 <= j_id < len(self._justice)
        for po_id in po_ids:
            assert self.get_po_type(po_id) == AIG.JUSTICE
        self._justice[j_id] = pos
    
    # Negation
    
    @staticmethod
    def is_negated(f):
        return (f&1) != 0

    @staticmethod
    def get_positive(f):
        return (f & ~1)

    @staticmethod
    def negate(f):
        return f ^ 1
    
    @staticmethod
    def negate_if(f, c):
        if c:
            return f^1
        else:
            return f
    
    @staticmethod
    def positive_if(f, c):
        if c:
            return f
        else:
            return f^1
    
    @staticmethod
    def negate_if_negated(f, c):
        return f ^ ( c & 1 )
    
    # Higher-level boolean operations
    
    def create_nand(self, left, right):
        return self.negate( self.create_and(left,right) )
    
    def create_or(self, left, right):
        return self.negate( self.create_and(self.negate(left), self.negate(right)))

    def create_nor(self, left, right):
        return self.negate( self.create_or(left, right))

    def create_xor(self, left, right):
        return self.create_or( 
                self.create_and( left, self.negate(right) ),
                self.create_and( self.negate(left), right )
            )
        
    def create_iff(self, left, right):
        return self.negate( self.create_xor(left, right) )
        
    def create_implies(self, left, right):
        return self.create_or(self.negate(left), right)
    
    def create_ite(self, f_if, f_then, f_else):
        return self.create_or( 
            self.create_and( f_if, f_then), 
            self.create_and( self.negate(f_if), f_else) 
            )

    # Object numbers
    
    def n_pis(self):
        return len(self._pis)
    
    def n_latches(self):
        return len(self._latches)
    
    def n_ands(self):
        return self.n_nonterminals() - self.n_buffers()
        
    def n_nonterminals(self):
        return len(self._nodes) - 1 - self.n_latches() - self.n_pis()
        
    def n_pos(self):
        return len( self._pos )
        
    def n_pos_by_type(self, type):
        res = 0
        for _ in self.get_pos_by_type(type):
            res += 1
        return res
        
    def n_justice(self):
        return len( self._justice )

    def n_buffers(self):
        return len( self._buffers )

    # Object access as iterators (use list() to get a copy)
    
    def construction_order(self):
        return ( i<<1 for i in xrange(1, len(self._nodes) ) )
        
    def construction_order_deref(self):
        return ( (f, self.deref(f)) for f in self.construction_order() )
    
    def get_pis(self):
        return  ( i<<1 for i, n in enumerate(self._nodes) if n.is_pi() )

    def get_latches(self):
        return ( l for l in self._latches )
    
    def get_buffers(self):
        return ( b for b in self._buffers if b>=0 )
    
    def get_and_gates(self):
        return  ( i<<1 for i, n in enumerate(self._nodes) if n.is_and() )
    
    def get_pos(self):
        return ( (po_id, po_fanin, po_type) for po_id, (po_fanin, po_type) in enumerate(self._pos) )

    def get_pos_by_type(self, type):
        return ( (po_id, po_fanin, po_type) for po_id, po_fanin, po_type in self.get_pos() if po_type==type )
        
    def get_po_fanins(self):
        return ( po for _,po,_ in self.get_pos() )
        
    def get_po_fanins_by_type(self, type):
        return ( po for _,po,po_type in self.get_pos() if po_type==type)
        
    def get_justice_properties(self):
        return ( (i,po_ids) for i, po_ids in enumerate( self._justice ) )
            
    def get_nonterminals(self):
        return ( i<<1 for i,n in enumerate(self._nodes) if n.is_nonterminal() )
            
    # Python special methods
    
    def __len__(self):
        return len(self._nodes)        

    # return the sequential cone of 'roots', stop at 'stop'

    def get_cone(self, roots, stop=[], fanins=get_positive_fanins):

        visited = set()
        
        dfs_stack = list(roots)
        
        while dfs_stack:

            cur = self.get_positive(dfs_stack.pop())

            if cur in visited or cur in stop:
                continue
            
            visited.add(cur)
            
            for fi in fanins(self, cur):
                if fi not in visited:
                    dfs_stack.append(fi)
        
        return sorted(visited)

    # return the sequential cone of roots

    def get_seq_cone(self, roots, stop=[]):
        return self.get_cone(roots, stop, fanins=AIG.get_positive_seq_fanins)

    def topological_sort(self, roots, stop=()):
        """ topologically sort the combinatorial cone of 'roots', stop at 'stop' """

        def fanins(f):
            if f in stop:
                return []
            return [ fi for fi in self.get_positive_fanins(f) ]

        visited = AIG.fset()
        dfs_stack = []
    
        for root in roots:
            
            if visited.add(root):
                continue
                
            dfs_stack.append( (root, fanins(root)) ) 

            while dfs_stack:

                cur, ds = dfs_stack[-1]

                if not ds:
                    
                    dfs_stack.pop()
                    
                    if cur is not None:
                        yield cur
                    
                    continue
                    
                d = ds.pop()

                if visited.add(d):
                    continue

                dfs_stack.append( (d,[fi for fi in fanins(d) if fi not in visited]) )

    def clean(self, pos=None):
        """ return a new AIG, containing only the cone of the POs, removing buffers while attempting to preserve names """

        aig = AIG()
        M = AIG.fmap()
            
        def visit(f, af):
            if self.has_name(f):
                if AIG.is_negated(af):
                    aig.set_name( AIG.get_positive(af), "~%s"%self.get_name_by_id(f) )
                else:
                    aig.set_name( af, self.get_name_by_id(f) )
            M[f] = af

        pos = range(len(self._pos)) if pos is None else pos

        cone = self.get_seq_cone( self.get_po_fanin(po_id) for po_id in pos )

        for f in self.topological_sort(cone):
            
            n = self.deref(f)
                
            if n.is_pi():
                visit( f, aig.create_pi() )
                
            elif n.is_and():
                visit( f, aig.create_and( M[n.get_left()], M[n.get_right()] ) )
                
            elif n.is_latch():
                l = aig.create_latch(init=n.get_init())
                visit( f, l )
                
            elif n.is_buffer():
                assert False
                visit( f, M( n.get_buf_in()) )
                
        for l in self.get_latches():

            if l in cone:
                aig.set_next(M[l], M[self.get_next(l)])                
                
        for po_id in pos:

            po_f = self.get_po_fanin(po_id)

            po = aig.create_po( M[po_f], self.get_name_by_po(po_id) if self.po_has_name(po_id) else None, po_type=self.get_po_type(po_id) )
                
        return aig

    def compose(self, src, M, copy_pos=True):
        """ rebuild the AIG 'src' inside 'self', connecting the two AIGs using 'M' """        
        
        for f in src.construction_order():
            
            if f in M:
                continue
                
            n = src.deref(f)
                
            if n.is_pi():
                M[f] = self.create_pi()
                
            elif n.is_and():
                M[f] = self.create_and( M[n.get_left()], M[n.get_right()] )
                
            elif n.is_latch():
                M[f] = self.create_latch(init=n.get_init())
                
            elif n.is_buffer():
                M[f] = self.create_buffer()

        for b in src.get_buffers():
            self.set_buf_in(M[b], M[src.get_buf_in(b)])

        for l in src.get_latches():
            self.set_next(M[l], M[src.get_next(l)])

        if copy_pos:
            for po_id, po_fanin, po_type in src.get_pos():
                self.create_po( M[po_fanin], po_type=po_type )

    def cutpoint(self, f):
        
        assert self.is_buffer(f)
        assert self.has_name(f)
        
        self.convert_buf_to_pi(f)

    def build_fanouts(self):
        
        for f in self.construction_order():

            for g in self.get_positive_fanins(f):
                
                self._fanouts.setdefault(g, set()).add(f)
    
    def get_fanouts(self, fs):
        
        res = set()
        
        for f in fs:
            for fo in self._fanouts[f]:
                res.add(fo)
              
        return res

    def conjunction( self, fs ):
        
        res = self.get_const1()
        
        for f in fs:
            res = self.create_and( res, f )
        
        return res
        
    def balanced_conjunction( self, fs ):
        
        N = len(fs)
        
        if N < 2:
            return self.conjunction(fs)
        
        return self.create_and( self.balanced_conjunction(fs[:N/2]), self.balanced_conjunction(fs[N/2:]) )
        
    def disjunction (self, fs):
        
        res = self.get_const0()
        
        for f in fs:
            res = self.create_or( res, f )
        
        return res
        
    def balanced_disjunction( self, fs ):
        
        N = len(fs)
        
        if N < 2:
            return self.disjunction(fs)
        
        return self.create_or( self.balanced_disjunction(fs[:N/2]), self.balanced_disjunction(fs[N/2:]) )

    def large_xor(self, fs):

        res = self.get_const0()

        for f in fs:
            res = self.create_xor(res, f)

        return res

    def mux(self, select, args):
        
        res = []
        
        for col in zip(*args):
            
            f = self.disjunction( self.create_and(s,c) for s,c in zip(select,col) )
            res.append( f )
            
        return res

    def create_constraint(aig, f, name=None):
        return aig.create_po(aig, f, name=name, po_type=AIG.CONSTRAINT)

    def create_property(aig, f, name=None):
        return aig.create_po(aig, AIG.negate(f), name=name, po_type=AIG.BAD_STATES)

    def create_bad_states(aig, f, name=None):
        return aig.create_po(aig, f, name=name, po_type=AIG.BAD_STATES)
