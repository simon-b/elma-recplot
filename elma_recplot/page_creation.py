from elma_recplot.util import init_logging

from elma_recplot.elma_loader import load_rec, load_lev
from elma_recplot.plot import draw_rec
from elma_recplot.eol_tools import (
    get_lev_by_id,
    get_rec_by_id_and_name,
    get_latest_replays,
)
from rich.progress import track

import polars as pl
import os
import logging

logger = logging.getLogger(__name__)


def make_recent_replay_page(index_page="index.md", rec_dir="."):
    # For fun, use polars here
    latest_replays = pl.json_normalize(get_latest_replays(num=100)).with_columns(
        (pl.col("RecFileName").str.strip_suffix(".rec") + ".html").alias("rec_base"),
    )
    for row in track(
        latest_replays.iter_rows(named=True),
        description="Processing recent recs",
        total=len(latest_replays),
    ):
        outfile = os.path.join(rec_dir, row["rec_base"])
        if os.path.exists(outfile):
            logger.info(f"Skipping existing file {outfile!r}")
            continue
        lev = load_lev(get_lev_by_id(row["LevelIndex"]))
        rec = load_rec(get_rec_by_id_and_name(row["UUID"], row["RecFileName"]))
        fig = draw_rec(rec, lev)
        title = "{lev} - {kuski} ({time:.2f}s)".format(
            kuski=row["DrivenByData.Kuski"],
            lev=row["LevelData.LevelName"],
            time=row["ReplayTime"] / 1000,
        )
        fig.update_layout(title_text=title)
        logger.info(f"Saving file {outfile!r}")
        fig.write_html(outfile, include_plotlyjs="cdn")

    def _rec_link(rec):
        return f"[{rec}](recs/{rec})"

    page_df = latest_replays.select(
        [
            pl.from_epoch("Uploaded", time_unit="s").alias("Date"),
            pl.col("LevelData.LevelName").alias("Lev"),
            pl.col("DrivenByData.Kuski").alias("Kuski"),
            (pl.col("ReplayTime") / 1000).alias("Time (s)"),
            pl.col("rec_base").alias("Static rec").map_elements(_rec_link),
        ]
    )
    logger.info(f"Saving file {index_page!r}")
    with open(index_page, "w", encoding="utf-8") as f:
        f.write(page_df.to_pandas().to_markdown(index=False))


if __name__ == "__main__":
    init_logging()
    make_recent_replay_page(
        index_page="/home/shb/elma-recplot-page/docs/_posts/2025-08-02-recent-recs.md",
        rec_dir="/home/shb/elma-recplot-page/docs/recs",
    )
