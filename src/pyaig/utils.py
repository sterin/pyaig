from aig import AIG

def extract_justice_po(aig, j_po):
    
    dst = AIG()
    
    latches = []
    M = AIG.map(aig, dst)

    po_map = {}
    
    for po_id, po_fanin, po_type in aig.get_pos():
        if po_type in ( AIG.CONSTRAINT, AIG.FAIRNESS ):
            po_map[ po_id ] = len(po_map)
            
    for po_id in aig.get_justice_pos(j_po):
        po_map[ po_id ] = len(po_map)

    cone = aig.get_seq_cone( aig.get_po_fanin(po_id) for po_id in po_map.iterkeys() )
    
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
            
    for po_id in po_map.iterkeys():
        dst.create_po( M[aig.get_po_fanin(po_id)], po_type=aig.get_po_type(po_id) )
        
    dst.create_justice( po_map[po_id] for po_id in aig.get_justice_pos(j_po) )
            
    return dst
