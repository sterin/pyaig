import argparse

from aig import AIG
from aig_io import read_aiger, write_aiger


def live(args):

    aig = read_aiger(args.src)

    po_ids = [ po_id for po_id, _, _ in aig.get_pos_by_type(AIG.OUTPUT) ]

    for po_id in po_ids:
        aig.set_po_type(po_id, AIG.JUSTICE)

    aig.create_justice(po_ids)

    write_aiger(aig, args.dst)


parser = argparse.ArgumentParser(description='PyAIG utils')
subparsers = parser.add_subparsers(help='sub-command help')

live_parser = subparsers.add_parser('live', help='Create a Justice PO from Output POs.')

live_parser.add_argument('src', type=argparse.FileType('rb'), help='source AIGER file')
live_parser.add_argument('dst', type=argparse.FileType('wb'), help='destination AIGER file')
live_parser.set_defaults(func=live)

args = parser.parse_args()
args.func(args)
