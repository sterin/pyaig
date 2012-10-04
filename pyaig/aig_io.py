#!/usr/bin/python

# Author: Baruch Sterin <sterin@berkeley.edu>
# Simple Python AIG readers and writers

import re
import subprocess

from aig import AIG

class _aiger_writer(object):
    
    def __init__(self, fout, I, L, O, A):
        M = I+L+A
        fout.write("aig %d %d %d %d %d\n"%(M,I,L,O,A))
        self._fout = fout
        self._M = M
        self._I = I
        self._L = L
        self._O = O
        self._A = A
        self._next = (I+1)<<1
    
    def write_inputs(self):
        pass
    
    def write_latch(self, next):
        self._fout.write("%d\n"%next)
        self._next += 2
    
    def write_po(self, po):
        self._fout.write("%d\n"%po)
    
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

    def write_po_name(self, i, name):
        self._fout.write("o%d %s\n"%(i, name) )

    def _encode(self, x):
        while (x & ~0x7f) > 0:
            ch = ( x & 0x7f ) | 0x80
            self._fout.write( chr(ch) )
            x >>= 7
        
        self._fout.write( chr(x) )

    
def write_aiger(aig, fout):
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
    
    writer = _aiger_writer(fout, aig.n_pis(), aig.n_latches(), aig.n_pos(), aig.n_nonterminals())
        
    writer.write_inputs()

    for l in aig.get_latches():
        writer.write_latch(aiger_lit(aig.get_next(l)))
                    
    for po in aig.get_pos():
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
        
    for i,_ in enumerate(aig.get_pos()):
        if aig.po_has_name(i):
            writer.write_po_name(i, aig.get_name_by_po(i) )

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
    
    for po in aig.get_pos():
        fout.write( "%d 0\n"%lit(po) )             

    for g in aig.get_and_gates():
        n = aig.deref(g)

        x = lit(g, map_cnf)
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

def read_aiger(fin):
    aig = AIG()

    header = fin.readline().split()
    assert header[0] == 'aig' 
    
    (M,I,L,O,A) = [ int(t) for t in header[1:] ]
   
    vars = []
    nexts = []
    pos = []
    
    vars.append( aig.get_const0() )
    
    for i in xrange(I):
        vars.append( aig.create_pi() )
        
    for i in xrange(L):
        vars.append( aig.create_latch() )
        nexts.append( int( fin.readline() ) )

    for i in xrange(O):
        pos.append( int( fin.readline() ) )
    
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
        aig.set_next( vars[v], lit(nexts[l]) )
        
    for i in xrange(O):
        aig.create_po( lit(pos[i]) )
        
    for line in fin:
        m = re.match( r'i(\d+) (.*)', line )
        if m:
            aig.set_name( vars[int(m.group(1))+1], m.group(2))
            continue
        
        m = re.match( r'l(\d+) (.*)', line )
        if m:
            aig.set_name( vars[I+int(m.group(1))+1], m.group(2))
            continue
        
    return aig
