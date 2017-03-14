#!/usr/bin/python

# Author: Baruch Sterin <sterin@berkeley.edu>
# Simple Python AIG readers and writers

import re
import subprocess

from aig import AIG

class _aiger_writer(object):

    def __init__(self, fout, I, L, O, A, B, C, J, F):
        
        M = I+L+A
        fout.write("aig %d %d %d %d %d"%(M,I,L,O,A))
        
        if B+C+J+F > 0:
            fout.write(" %d"%B )
            
        if C+J+F > 0:
            fout.write(" %d"%C )

        if J+F > 0:
            fout.write(" %d"%J )
            
        if F > 0:
            fout.write(" %d"%F )
        
        fout.write('\n')
        
        self._fout = fout
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
    
    def write_inputs(self):
        pass
        
    def write_latch(self, next, init):
        if init==AIG.INIT_ZERO:
            self._fout.write("%d\n"%next)
        elif init==AIG.INIT_ONE:
            self._fout.write("%d 1\n"%next)
        else:
            self._fout.write("%d %d\n"%(next, self._next))
        
        self._next += 2
    
    def write_po(self, po):
        self._fout.write("%d\n"%po)
    
    def write_justice_header(self, pos):
        self._fout.write("%d\n"%len(pos))
    
    def write_and(self, left, right):
        if left < right:
            left, right = right, left

        self._encode( self._next - left)
        self._encode( left - right)

        self._next += 2
    
    def write_input_name(self, i, name):
        self._fout.write("i%d %s\n"%(i, name) )
    
    def write_latch_name(self, i, name):
        self._fout.write("l%d %s\n"%(i, name) )

    def write_po_name(self, type, i, name):
        self._fout.write("%s%d %s\n"%(type, i, name) )

    def _encode(self, x):
        while (x & ~0x7f) > 0:
            ch = ( x & 0x7f ) | 0x80
            self._fout.write( chr(ch) )
            x >>= 7
        
        self._fout.write( chr(x) )

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
        fout, 
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
            writer.write_po_name('o', i, aig.get_name_by_po(po_id) )

    for i, (po_id, _, _) in enumerate(aig.get_pos_by_type(AIG.BAD_STATES)):
        if aig.po_has_name(po_id):
            writer.write_po_name('b', i, aig.get_name_by_po(po_id) )

    for i, (po_id, _, _) in enumerate(aig.get_pos_by_type(AIG.CONSTRAINT)):
        if aig.po_has_name(po_id):
            writer.write_po_name('c', i, aig.get_name_by_po(po_id) )

    for i, po_ids in aig.get_justice_properties():
        
        if not po_ids:
            continue
        
        po_id = po_ids[0]
        
        if aig.po_has_name(po_id):
            writer.write_po_name('j', i, aig.get_name_by_po(po_id) )

    for i, (po_id, _, _) in enumerate(aig.get_pos_by_type(AIG.FAIRNESS)):
        if aig.po_has_name(po_id):
            writer.write_po_name('f',i, aig.get_name_by_po(po_id) )

    return map_aiger


def write_aiger(aig, f):
    if type(f) == str:
        with open(f, "wb") as fout:
            return write_aiger_file(aig, fout)
    else:
        return write_aiger_file(aig, f)


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
    assert header[0] == 'aig' 
    
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
        
        tokens = line.strip().split(' ')
        
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
        
    for line in fin:
        m = re.match( r'i(\d+) (.*)', line )
        if m:
            aig.set_name( vars[int(m.group(1))+1], m.group(2))
            continue
        
        m = re.match( r'l(\d+) (.*)', line )
        if m:
            aig.set_name( vars[I+int(m.group(1))+1], m.group(2))
            continue
        
        m = re.match( r'o(\d+) (.*)', line )
        if m:
            aig.set_po_name( output_pos[int(m.group(1))], m.group(2))
            continue
        
        m = re.match( r'b(\d+) (.*)', line )
        if m:
            aig.set_po_name( bad_states_pos[int(m.group(1))], m.group(2))
            continue
        
        m = re.match( r'c(\d+) (.*)', line )
        if m:
            aig.set_po_name( constraint_pos[int(m.group(1))], m.group(2))
            continue
        
        m = re.match( r'f(\d+) (.*)', line )
        if m:
            aig.set_po_name( fairness_pos[int(m.group(1))], m.group(2))
            continue
        
    return aig


def read_aiger(f):
    if type(f) == str:
        with open(f, "rb") as fin:
            return read_aiger_file(fin)
    else:
        return read_aiger_file(f)
