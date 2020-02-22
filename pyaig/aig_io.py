#!/usr/bin/python

# Author: Baruch Sterin <sterin@berkeley.edu>
# Simple Python AIG readers and writers

import io
import re
import subprocess

from past.builtins import xrange

from . aig import AIG

class _aiger_writer(object):

    def __init__(self, I, L, O, A, B, C, J, F):
        
        self._bytes = bytearray()

        M = I+L+A
        self._bytes.extend(b"aig %d %d %d %d %d"%(M,I,L,O,A))
        
        if B+C+J+F > 0:
            self._bytes.extend(b" %d"%B )
            
        if C+J+F > 0:
            self._bytes.extend(b" %d"%C )

        if J+F > 0:
            self._bytes.extend(b" %d"%J )
            
        if F > 0:
            self._bytes.extend(b" %d"%F )
        
        self._bytes.extend(b'\n')
        
        self._M = M
        self._I = I
        self._L = L
        self._O = O
        self._A = A
        self._B = B
        self._C = C
        self._J = J
        self._F = F
        
        self._next = (I+1)<<1
    
    def get_bytes(self):
        return self._bytes

    def write_inputs(self):
        pass
        
    def write_latch(self, next, init):
        if init==AIG.INIT_ZERO:
            self._bytes.extend(b"%d\n"%next)
        elif init==AIG.INIT_ONE:
            self._bytes.extend(b"%d 1\n"%next)
        else:
            self._bytes.extend(b"%d %d\n"%(next, self._next))
        
        self._next += 2
    
    def write_po(self, po):
        self._bytes.extend(b"%d\n"%po)
    
    def write_justice_header(self, pos):
        self._bytes.extend(b"%d\n"%len(pos))
    
    def write_and(self, left, right):
        if left < right:
            left, right = right, left

        self._encode( self._next - left )
        self._encode( left - right )

        self._next += 2
    
    def write_input_name(self, i, name):
        self._bytes.extend(b"i%d %s\n"%(i, self._encode_str(name)))
    
    def write_latch_name(self, i, name):
        self._bytes.extend(b"l%d %s\n"%(i, self._encode_str(name)))

    def write_po_name(self, po_type, i, name):
        self._bytes.extend(b"%s%d %s\n"%(po_type, i, self._encode_str(name)))

    def _encode(self, x):

        while (x & ~0x7f) > 0:
            self._bytes.append( ( x & 0x7f ) | 0x80 )
            x >>= 7
        
        self._bytes.append(x)

    def _encode_str(self, s):
        if isinstance(s, bytes):
            return s
        return s.encode('utf-8')

def write_aiger_file(aig, fout):
    
    map_aiger = {}
    
    aiger_i = 0

    map_aiger[0] = aiger_i
    aiger_i += 1
    
    for pi in aig.get_pis():
        map_aiger[ pi ] = (aiger_i<<1)
        aiger_i += 1
    
    for l in aig.get_latches():
        map_aiger[ l ] = (aiger_i<<1)
        aiger_i += 1

    for g in aig.get_nonterminals():
        map_aiger[ g ] = (aiger_i<<1)
        aiger_i += 1
        
    def aiger_lit(aig_lit):
        
        lit_pos = aig.get_positive(aig_lit)
        lit = map_aiger[lit_pos]
        
        if aig.is_negated(aig_lit):
            return lit+1
        else:
            return lit
    
    writer = _aiger_writer(
        aig.n_pis(), 
        aig.n_latches(), 
        aig.n_pos_by_type(AIG.OUTPUT), 
        aig.n_nonterminals(), 
        aig.n_pos_by_type(AIG.BAD_STATES), 
        aig.n_pos_by_type(AIG.CONSTRAINT), 
        aig.n_justice(),
        aig.n_pos_by_type(AIG.FAIRNESS), 
        )
        
    writer.write_inputs()

    for l in aig.get_latches():
        writer.write_latch(aiger_lit(aig.get_next(l)), aig.get_init(l))
                    
    for po in aig.get_po_fanins_by_type(AIG.OUTPUT):
        writer.write_po(aiger_lit(po))      
    
    for po in aig.get_po_fanins_by_type(AIG.BAD_STATES):
        writer.write_po(aiger_lit(po))      
    
    for po in aig.get_po_fanins_by_type(AIG.CONSTRAINT):
        writer.write_po(aiger_lit(po))      

    for _, j_pos in aig.get_justice_properties():
        writer.write_justice_header(j_pos)
    
    for _, j_pos in aig.get_justice_properties():
        for po_id in j_pos:
            writer.write_po( aiger_lit( aig.get_po_fanin(po_id) ) )

    for po in aig.get_po_fanins_by_type(AIG.FAIRNESS):
        writer.write_po(aiger_lit(po))      
    
    for g in aig.get_nonterminals():
        n = aig.deref(g)
        if n.is_buffer():
            al = ar = aiger_lit( n.get_buf_in() )
        else:
            al = aiger_lit(n.get_left())
            ar = aiger_lit(n.get_right())
        writer.write_and(al, ar)

    # Write symbol table

    for i, pi in enumerate(aig.get_pis()):
        if aig.has_name(pi):
            writer.write_input_name(i, aig.get_name_by_id(pi) )
        
    for i, l in enumerate(aig.get_latches()):
        if aig.has_name(l):
            writer.write_latch_name(i, aig.get_name_by_id(l) )
        
    for i, (po_id, _, _) in enumerate(aig.get_pos_by_type(AIG.OUTPUT)):
        if aig.po_has_name(po_id):
            writer.write_po_name(b'o', i, aig.get_name_by_po(po_id) )

    for i, (po_id, _, _) in enumerate(aig.get_pos_by_type(AIG.BAD_STATES)):
        if aig.po_has_name(po_id):
            writer.write_po_name(b'b', i, aig.get_name_by_po(po_id) )

    for i, (po_id, _, _) in enumerate(aig.get_pos_by_type(AIG.CONSTRAINT)):
        if aig.po_has_name(po_id):
            writer.write_po_name(b'c', i, aig.get_name_by_po(po_id) )

    for i, po_ids in aig.get_justice_properties():
        
        if not po_ids:
            continue
        
        po_id = po_ids[0]
        
        if aig.po_has_name(po_id):
            writer.write_po_name(b'j', i, aig.get_name_by_po(po_id) )

    for i, (po_id, _, _) in enumerate(aig.get_pos_by_type(AIG.FAIRNESS)):
        if aig.po_has_name(po_id):
            writer.write_po_name(b'f',i, aig.get_name_by_po(po_id) )

    fout.write( writer.get_bytes() )

    return map_aiger


def write_aiger(aig, f):
    if type(f) == str:
        with open(f, "wb") as fout:
            return write_aiger_file(aig, fout)
    else:
        return write_aiger_file(aig, f)


def flatten_aiger(aig):
    f = io.BytesIO()
    write_aiger_file(aig, f)
    return f.getvalue()


def write_cnf(aig, fout):
    map_cnf = {}
    
    # const 0
    
    cnf_i = 1
    
    map_cnf[0] = cnf_i
    cnf_i += 1
    
    for pi in aig.get_pis():
        map_cnf[ pi ] = cnf_i
        cnf_i += 1
    
    for l in aig.get_latches():
        map_cnf[ l ] = cnf_i
        cnf_i += 1

    for g in aig.get_and_gates():
        map_cnf[ g ] = cnf_i
        cnf_i += 1

    fout.write("p %d %d\n"%( cnf_i, aig.n_ands()*3 + 1 + aig.n_pos() ))

    fout.write("-1 0\n")

    def lit(aig_lit):
        lit_pos = aig.get_positive(aig_lit)
        lit_cnf = map_cnf[lit_pos]
        
        if aig.is_negated(aig_lit):
            return -lit_cnf
        else:
            return lit_cnf
    
    for po in aig.get_po_fanins():
        fout.write( "%d 0\n"%lit(po) )             

    for g in aig.get_and_gates():
        n = aig.deref(g)

        x = lit(g)
        y = lit(n.get_left())
        z = lit(n.get_right())
        
        fout.write("%d %d 0\n"%(-x, y))
        fout.write("%d %d 0\n"%(-x, z))
        fout.write("%d %d %d 0\n"%(x, -y, -z))

def write_tecla(aig, fout):
    
    def get_lit(f):
        if f == aig.get_const0():
            return 'FALSE'
        elif f == aig.get_const1():
            return 'TRUE'
        
        if aig.is_negated(f):
            neg = '~'
        else:
            neg = ''

        if aig.is_pi(f):
            c = 'I'
        elif aig.is_and(f):
            c = 'N'
        elif aig.is_latch(f):
            c = 'L'
        
        return '%s%s%d'%(neg,c,aig.get_id(f))
            
    fout.write('definitions:\n\n')
    
    for l in aig.get_latches():
        fout.write( '  I(%s) := FALSE ;\n'%get_lit(l))
    
    fout.write('\n')
    
    for a in aig.get_and_gates():
        
        n = aig.deref(a)
        
        fout.write( 
            '  %s := %s & %s ;\n' %(
                get_lit(a), 
                get_lit(n.get_left()),
                get_lit(n.get_right())
                )
            )
    
    fout.write('\n')
    
    for l in aig.get_latches():
        n = aig.deref(l)
        
        fout.write( 
            '  X(%s) := %s ;\n' %(
                get_lit(l), 
                get_lit(n.get_next()),
                )
            )
        
    fout.write('\nproof obligations:\n\n')
    
    for po in aig.get_pos():
        fout.write('  %s ;\n'%get_lit(po))

def is_sat(aig):
    p = subprocess.Popen("minisat", stdin=subprocess.PIPE, close_fds=True, shell=True)
    fout = p.stdin
    write_cnf(fout)
    fout.close()

def read_aiger_file(fin):
    
    aig = AIG()

    header = fin.readline().split()
    assert header[0] == b'aig'
    
    args = [ int(t) for t in header[1:] ]
    (M,I,L,O,A) = args[:5]
    
    B = args[5] if len(args)>5 else 0
    C = args[6] if len(args)>6 else 0
    J = args[7] if len(args)>7 else 0
    F = args[8] if len(args)>8 else 0
   
    vars = []
    nexts = []
    
    pos_output = []
    pos_bad_states = []
    pos_constraint = []
    pos_justice = []
    pos_fairness = []
    
    vars.append( aig.get_const0() )
    
    for i in xrange(I):
        vars.append( aig.create_pi() )
        
    def parse_latch(line):
        
        tokens = line.strip().split(b' ')
        
        next = int(tokens[0])
        init = 0
        
        if len(tokens)==2:
            
            if tokens[1] == '0':
                init = AIG.INIT_ZERO
            if tokens[1] == '1':
                init = AIG.INIT_ONE
            else:
                init = AIG.INIT_NONDET
                
        return (next, init)
        
    for i in xrange(L):
        vars.append( aig.create_latch() )
        nexts.append( parse_latch(fin.readline() ) )

    for i in xrange(O):
        pos_output.append( int( fin.readline() ) )

    for i in xrange(B):
        pos_bad_states.append( int( fin.readline() ) )

    for i in xrange(C):
        pos_constraint.append( int( fin.readline() ) )

    n_j_pos = []

    for i in xrange(J):
        n_j_pos.append( int(fin.readline()) )
        
    for n in n_j_pos:
        pos = []
        for i in xrange(n):
            pos.append( int( fin.readline() ) )
        pos_justice.append(pos)

    for i in xrange(F):
        pos_fairness.append( int( fin.readline() ) )

    def decode():

        i = 0
        res = 0

        while True:

            c = ord(fin.read(1))
            
            res |= ( (c&0x7F) << (7*i) )
            
            if (c&0x80)==0:
                break
            
            i += 1
    
        return res
    
    def lit(x):
        return aig.negate_if( vars[x>>1], x&0x1)
    
    for i in xrange(I+L+1, I+L+A+1):
        d1 = decode()
        d2 = decode()
        g = i<<1
        vars.append( aig.create_and( lit(g-d1), lit(g-d1-d2) ) )
                     
    for l, v in enumerate(xrange(I+1,I+L+1)):
        aig.set_init( vars[v], nexts[l][1] )
        aig.set_next( vars[v], lit(nexts[l][0]) )
        
    output_pos = []
        
    for po in pos_output:
        output_pos.append( aig.create_po( lit(po), po_type=AIG.OUTPUT ) )
    
    bad_states_pos = []
        
    for po in pos_bad_states:
        bad_states_pos.append( aig.create_po( lit(po), po_type=AIG.BAD_STATES ) )
        
    constraint_pos = []
        
    for po in pos_constraint:
        constraint_pos.append( aig.create_po( lit(po), po_type=AIG.CONSTRAINT ) )
        
    for pos in pos_justice:
        po_ids = [ aig.create_po( lit(po), po_type=AIG.JUSTICE ) for po in pos ]
        aig.create_justice( po_ids )

    fairness_pos = []
        
    for po in pos_fairness:
        fairness_pos.append( aig.create_po( lit(po), po_type=AIG.FAIRNESS ) )
        
    names = set()
    po_names = set()

    for line in fin:
        m = re.match( b'i(\\d+) (.*)', line )
        if m:
            if m.group(2) not in names:
                aig.set_name( vars[int(m.group(1))+1], m.group(2))
                names.add(m.group(2))
            continue
        
        m = re.match( b'l(\\d+) (.*)', line )
        if m:
            if m.group(2) not in names:
                aig.set_name( vars[I+int(m.group(1))+1], m.group(2))
                names.add(m.group(2))
            continue
        
        m = re.match( b'o(\\d+) (.*)', line )
        if m:
            if m.group(2) not in po_names:
                aig.set_po_name( output_pos[int(m.group(1))], m.group(2))
                po_names.add(m.group(2))
            continue
        
        m = re.match( b'b(\\d+) (.*)', line )
        if m:
            if m.group(2) not in po_names:
                aig.set_po_name( bad_states_pos[int(m.group(1))], m.group(2))
                po_names.add(m.group(2))
            continue
        
        m = re.match( b'c(\\d+) (.*)', line )
        if m:
            if m.group(2) not in po_names:
                aig.set_po_name( constraint_pos[int(m.group(1))], m.group(2))
                po_names.add(m.group(2))
            continue
        
        m = re.match( b'f(\\d+) (.*)', line )
        if m:
            if m.group(2) not in po_names:
                aig.set_po_name( fairness_pos[int(m.group(1))], m.group(2))
                po_names.add(m.group(2))
            continue
        
    return aig


def read_aiger(f):
    if type(f) == str:
        with open(f, "rb") as fin:
            return read_aiger_file(fin)
    else:
        return read_aiger_file(f)


def unflatten_aiger(buf):
    return read_aiger_file(io.BytesIO(buf))


def marshal_aiger(aig):

    data = bytearray()

    def putu(x):
        while x >= 0x80:
            data.append( x&0x7F | 0x80 )
            x >>= 7
        data.append(x)

    M = AIG.fmap(negate_if_negated=lambda f, c: f^c)

    # Constants

    n_const = 2
    M[ AIG.get_const1() ] = 2

    # PIs

    n_pis = aig.n_pis()
    putu(n_pis)

    for i, pi in enumerate(aig.get_pis()):
        M[ pi ] = (n_const + i) << 1

    # Latches

    n_latches = aig.n_latches()
    putu(n_latches)

    for i, ll in enumerate(aig.get_latches()):
        M[ ll ] = (n_const + n_pis + i) << 1

    # Gates

    n_ands = aig.n_ands()   
    putu(n_ands)

    for i, f in enumerate(aig.get_and_gates()):

        putu( M[ aig.get_and_right(f) ] << 1)
        putu( M[ aig.get_and_left(f) ] )

        M[ f ] = (n_const + n_pis + n_latches + i) << 1

    # Latches

    V = { AIG.INIT_NONDET:0, AIG.INIT_ZERO:2, AIG.INIT_ONE:3 }
    
    for ll in aig.get_latches():
        putu( (M[ aig.get_next(ll) ] << 2) | V[ aig.get_init(ll) ] )

    # Properties

    output_pos = list( aig.get_pos_by_type(AIG.OUTPUT) )
    bad_pos =  list( aig.get_pos_by_type(AIG.BAD_STATES) )
    constraint_pos =  list( aig.get_pos_by_type(AIG.CONSTRAINT) )
    fairness_pos =  list( aig.get_pos_by_type(AIG.FAIRNESS) )
    justice_pos =  list( aig.get_pos_by_type(AIG.JUSTICE) )
    justice_properties = list( aig.get_justice_properties() )

    if len(bad_pos) == 0 and len(justice_properties)==0 and len(output_pos) > 0:
        bad_pos = output_pos

    putu( len(bad_pos) )
    for po_id, po_fanin, po_type in bad_pos:
        putu( M[po_fanin] ^ 1 )

    # Fairness

    putu(1)

    total = len(justice_pos) + len(justice_properties) * (len(fairness_pos) + 1)
    putu(total)

    for i, po_ids in justice_properties:

        for po_id in po_ids:
            putu( M[ aig.get_po_fanin(po_id) ] )

        for po_id, po_fanin, po_type in fairness_pos:
            putu( M[po_fanin] )

        putu(0)

    # Constraints

    putu( len(constraint_pos) )
    for po_id, po_fanin, po_type in constraint_pos:
        putu( M[po_fanin] )

    return data


class archive(object):

    def __init__(self, data):
        
        self.data = data
        self.pos = 0

    def get_next(self):

        c = self.data[ self.pos ]
        self.pos += 1

        return c

    def getu(self):
        
        x = 0
        shift = 0
        while True:
            c = self.get_next()
            x |= ( c & 0x7F ) << shift
            shift += 7
            if c < 0x80:
                return x


class ifmap(object):
    
    def __init__(self):
        self.m = {}
        
    def __getitem__(self, i):
        return AIG.negate_if(self.m[ i & ~1 ], i&1)
        
    def __setitem__(self, i, f):
        self.m[ i & ~1 ] = AIG.negate_if(f, i&1)


def unmarshal_aiger(data):

    a = archive(data)

    aig = AIG()
    M = ifmap()

    # Constants

    n_const = 2
    M[ 2 ] = AIG.get_const1()

    # PIs

    n_pis = a.getu()

    for i in xrange(n_pis):
        M[ (n_const + i) << 1 ] = aig.create_pi()

    # Latches

    n_latches = a.getu()

    for i in xrange(n_latches):
        M[ (n_const + n_pis + i) << 1 ] = aig.create_latch()

    # Gates

    n_ands = a.getu()

    for i in xrange(n_ands):
        f0 = M[ a.getu() >> 1 ]
        f1 = M[ a.getu() ]
        M[ (n_const + n_pis + n_latches + i) << 1 ] = aig.create_and(f0, f1)
    
    # Latches

    V = { 0:AIG.INIT_NONDET, 2:AIG.INIT_ZERO, 3:AIG.INIT_ONE }

    for ll in aig.get_latches():
        u = a.getu()
        aig.set_init(ll, V[ u & 3])
        aig.set_next(ll, M[ u >> 2 ])

    # Properties

    n_props = a.getu()
    for i in xrange(n_props):
        aig.create_po(M[ a.getu() ^ 1 ], po_type=AIG.BAD_STATES)

    # Liveness

    fair_version = a.getu()
    assert fair_version == 1

    fair_total = a.getu()
    cur_justice = []

    for i in xrange(fair_total):
        u = a.getu()
        if u > 0:
            cur_justice.append( aig.create_po(M[u], po_type=AIG.JUSTICE) )
        else:
            aig.create_justice(cur_justice)
            cur_justice = []

    # Constraints

    n_constr = a.getu()
    for i in xrange(n_constr):
        aig.create_po(M[ a.getu() ^ 1 ], po_type=AIG.CONSTRAINT)

    return aig
