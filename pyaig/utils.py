from .aig import AIG
from .aig_io import read_aiger, write_aiger

def extract_justice_po(aig, j_po):
    
    dst = AIG()
    
    latches = []
    M = AIG.fmap()

    po_map = {}
    
    for po_id, po_fanin, po_type in aig.get_pos():
        if po_type in ( AIG.CONSTRAINT, AIG.FAIRNESS ):
            po_map[ po_id ] = len(po_map)
            
    for po_id in aig.get_justice_pos(j_po):
        po_map[ po_id ] = len(po_map)

    cone = aig.get_seq_cone( aig.get_po_fanin(po_id) for po_id in po_map )
    
    for f in cone:
        
        n = aig.deref(f)
        
        if n.is_pi():

            M[f] = dst.create_pi()
            
        elif n.is_and():

            M[f] = dst.create_and( M[n.get_left()], M[n.get_right()] )
            
        elif n.is_latch():

            l = dst.create_latch(init=n.get_init())
            M[f] = l

            latches.append( (f, l) )

    for f, l in latches:
        
        next = M[aig.get_next(f)]
        dst.set_next(l, next)
            
    for po_id in po_map:
        dst.create_po( M[aig.get_po_fanin(po_id)], po_type=aig.get_po_type(po_id) )
        
    dst.create_justice( po_map[po_id] for po_id in aig.get_justice_pos(j_po) )
            
    return dst

class po_info(object):
    
    def __init__(self, aig):
        
        self.pos_by_type = {}
        self.j_props = []

        self.save(aig)
            
    def save(self, aig):

        for po_id, _, po_type in aig.get_pos():
            self.pos_by_type.setdefault(po_type, set()).add( po_id )
            
        for i, po_ids in aig.get_justice_properties():
            self.j_props.append(po_ids)

    @staticmethod
    def remove(aig):

        aig.remove_justice()

        for po_id, _, po_type in aig.get_pos():
            aig.set_po_type(po_id, AIG.OUTPUT)

    def restore(self, aig):
    
        for po_type, po_ids in iteritems(self.pos_by_type):
            for po_id in po_ids:
                aig.set_po_type(po_id, po_type)

        for po_ids in self.j_props:
            aig.create_justice(po_ids)

def save_po_info( aiger_in, aiger_out ):

    with open(aiger_in, 'r') as fin:
        aig = read_aiger( fin )
        
    saved = po_info(aig)
    
    po_info.remove(aig)
    
    with open(aiger_out, 'w') as fout:
        write_aiger( aig, fout )    
    
    return saved

def restore_po_info( saved, aiger_in, aiger_out ):
    
    with open(aiger_in, 'r') as fin:
        aig = read_aiger( fin )

    saved.restore(aig)

    with open(aiger_out, 'w') as fout:
        write_aiger( aig, fout )
        
def delay(aig, f, n=1, init=AIG.INIT_ZERO, name=None):
    """ delay 'f' for 'n' cycles, start at 'init' """

    for i in xrange(n):
        f = aig.create_latch(name=name, init=init, next=f)
        
    return f

def dfs(roots, children):

    dfs_stack = roots

    visited = set()

    while dfs_tack:

        cur = dfs_stack.pop()

        if cur in visited:
            continue

        visited.add(cur)
        yield cur

        for c in children(cur):
            if c not in visited:
                dfs_stack.append(c)

visited = set()
order = []

def visit(cur, children):

    if cur in visited:
        return

    visited.add(cur)

    for c in children(cur):
        visit(c, childen)

    order.append(cur)


def topological_sort(roots, children, mark, unmark, is_marked):

    dfs_stack = [ unmark(r) for r in roots ]

    visited = set()

    while dfs_stack:

        cur = dfs_stack.pop()

        if is_marked(cur):
            yield umark(cur)

        elif cur not in visited:

            visited.add(cur)

            dfs_stack.append( mark(cur) )
            dfs_stack.extend( unmark(c) for c in children(cur) if c not in visited )
