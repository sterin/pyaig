import click

from . aig import AIG
from . aig_io import read_aiger, write_aiger


@click.group()
def cli():
    """ PyAIG utils """
    pass


@cli.command()
@click.argument('src', type=click.Path(exists=True, dir_okay=False))# , help='source AIGER file')
@click.argument('dst', type=click.Path())#, help='destination AIGER file')
def live(src, dst):
    """ Create a Justice PO from all output POs. """

    aig = read_aiger(src)

    po_ids = [ po_id for po_id, _, _ in aig.get_pos_by_type(AIG.OUTPUT) ]

    for po_id in po_ids:
        aig.set_po_type(po_id, AIG.JUSTICE)

    aig.create_justice(po_ids)

    write_aiger(aig, dst)


cli()
