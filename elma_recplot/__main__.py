import logging
import os
from datetime import datetime

import click

from elma_recplot.elma_loader import load_lev, load_rec
from elma_recplot.eol_tools import get_lev_by_id, get_rec_by_id_and_name
from elma_recplot.page_creation import make_recent_replay_page
from elma_recplot.plot import draw_rec
from elma_recplot.util import init_logging

logger = logging.getLogger("elma_recplot")


@click.group()
def cli():
    init_logging()


@cli.command(help="DL lev by ID")
@click.argument("lev_id", type=int)
@click.option("--outfile", default="dl.lev", type=click.File("wb"))
def get_lev(lev_id, outfile):
    lev = get_lev_by_id(lev_id).getvalue()
    logger.info(f"Writing level {lev_id} to {outfile.name!r}")
    outfile.write(lev)


@cli.command(help="DL rec by ID and name")
@click.argument("rec_id")
@click.argument("rec_name")
@click.option("--outfile", default="dl.rec", type=click.File("wb"))
def get_rec(rec_id: str, rec_name: str, outfile):
    rec = get_rec_by_id_and_name(rec_id, rec_name).getvalue()
    logger.info(f"Writing rec {rec_id}/{rec_name} to {outfile.name!r}")
    outfile.write(rec)


@cli.command(help="Plot local lev/rec as plotly html")
@click.argument("lev_file", type=click.File("rb"))
@click.argument("rec_file", type=click.File("rb"))
@click.option("--outfile", default="rec_plot.html", type=click.File("w"))
def plot_rec(rec_file, lev_file, outfile):
    rec = load_rec(rec_file)
    lev = load_lev(lev_file)
    fig = draw_rec(rec, lev)
    logger.info(f"Saving plot to {outfile.name!r}")
    fig.write_html(outfile, include_plotlyjs="cdn")


@cli.command(help="Create a page with recent replays")
@click.option(
    "--index-page",
    default="{}-recent-recs.md".format(datetime.now().strftime("%Y-%m-%d")),
    type=click.Path(),
)
@click.option("--index-dir", default=".", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--rec-dir", default="recs", type=click.Path(exists=True, file_okay=False)
)
@click.option("--num", default=20, type=int)
def make_page(index_page, index_dir, rec_dir, num):
    make_recent_replay_page(
        index_page=os.path.join(index_dir, index_page), rec_dir=rec_dir, num=num
    )


if __name__ == "__main__":
    cli()
