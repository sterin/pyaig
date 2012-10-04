#!/usr/bin/python

from aig import AIG
    
class aigexpr(object):
    
    @staticmethod
    def const(aig, c):
        return aigexpr(aig, AIG.get_const(c))
        
    @staticmethod
    def create_pi(aig, n=None):
        return aigexpr(aig, aig.create_pi(n))
    
    @staticmethod
    def create_latch(aig, n=None):
        return aigexpr(aig, aig.create_latch(name=n))
    
    def __init__(self, aig, f):
        self.aig = aig
        self.f = f
        
    def get_aig(self):
        return self.aig
    
    def get_f(self):
        return self.f
    
    def is_negated(self):
        return self.aig.is_negated(self.f)
    
    def is_const0(self):
        return self.aig.is_const0(self.f)
        
    def is_pi(self):
        return self.aig.is_pi(self.f)
    
    def is_latch(self):
        return self.aig.is_latch(self.f)

    def get_next(self):
        assert self.is_latch()
        return self.aig.get_next(self.f)

    def set_next(self, next):
        assert self.aig == next.aig
        assert self.is_latch()
        self.aig.set_next(self.f, next.get_f())
    
    def positive_if(self, c):
        return self.negate_if( c^1 )
    
    def negate_if(self, c):
        return aigexpr( self.aig, self.aig.negate_if(self.f, c) )
    
    def is_and(self):
        return self.aig.is_and(self.f)
    
    def get_pos(self):
        return self.aig.get_pos(self.f)
    
    def deref(self):
        return self.aig.deref(self.f)

    def __eq__(self, rhs):
        assert self.aig == rhs.aig
        return self.f == rhs.f
    
    def __and__(self, rhs):
        assert self.aig == rhs.aig
        return aigexpr( self.aig, self.aig.create_and(self.f, rhs.f) )
    
    def __or__(self, rhs):
        assert self.aig == rhs.aig
        return aigexpr( self.aig, self.aig.create_or(self.f, rhs.f) )
    
    def __xor__(self, rhs):
        assert self.aig == rhs.aig
        return aigexpr( self.aig, self.aig.create_xor(self.f, rhs.f) )
    
    def __invert__(self):
        return aigexpr( self.aig, self.aig.negate(self.f) )
    
    def implies(self, rhs):
        return ~self | rhs
    
    def iff(self, rhs):
        return ~(self ^ rhs)
    
    def ite(self, t, e):
        assert self.aig == t.aig == e.aig
        return aigexpr(self.aig, self.aig.create_ite(self.f, t.f, e.f))
    
    def __repr__(self):
        return "aigexpr(%s, %X)"%(str(self.aig), self.f)
         
if __name__=="__main__":
            
    aig = AIG()
    
    x = aigexpr.create_pi(aig)
    l = aigexpr.create_latch(aig)

    l.set_next( ~(x^l) )

    aig.create_po( l.get_f() )

    import aig_io
    aig_io.write_aiger(aig, open('test.aig',"w"))

    