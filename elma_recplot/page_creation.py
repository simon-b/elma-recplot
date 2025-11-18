import logging
import os

import plotly.io as pio
import polars as pl
from rich.progress import track

from elma_recplot.elma_loader import load_lev, load_rec
from elma_recplot.eol_tools import (
    get_latest_replays,
    get_lev_by_id,
    get_rec_by_id_and_name,
)
from elma_recplot.plot import draw_event_timeline, draw_rec

logger = logging.getLogger(__name__)


def make_recent_replay_page(index_page="index.md", rec_dir=".", num: int = 20):
    # For fun, use polars here
    latest_replays = pl.json_normalize(get_latest_replays(num=num)).with_columns(
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
        logger.info(f"Attempting to create {outfile!r}")
        lev = load_lev(get_lev_by_id(row["LevelIndex"]))
        rec = load_rec(get_rec_by_id_and_name(row["UUID"], row["RecFileName"]))
        fig_map = draw_rec(rec, lev)
        title = "{lev} - {kuski} ({time:.2f}s)".format(
            kuski=row["DrivenByData.Kuski"],
            lev=row["LevelData.LevelName"],
            time=row["ReplayTime"] / 1000,
        )
        fig_map.update_layout(title_text=title)
        fig_events = draw_event_timeline(rec)
        logger.info(f"Saving file {outfile!r}")
        with open(outfile, "w", encoding="utf-8") as f:
            pio.write_html(fig_map, file=f, include_plotlyjs="cdn")
            pio.write_html(fig_events, file=f, include_plotlyjs=False)

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
