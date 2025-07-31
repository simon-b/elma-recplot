import logging
import logging.config

from elma_recplot.elma_loader import load_rec, load_lev
from elma_recplot.plot import draw_rec


def init_logging():
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "file_handler": {
                    "class": "logging.FileHandler",
                    "formatter": "standard",
                    "filename": "elma_recplot.log",
                },
                "console_handler": {
                    "class": "rich.logging.RichHandler",
                    "level": "DEBUG",
                },
            },
            "root": {
                "handlers": ["file_handler", "console_handler"],
                "level": "DEBUG",
            },
        }
    )


if __name__ == "__main__":
    init_logging()
    with open("22.lev", "rb") as lev_file:
        lev = load_lev(lev_file)
    with open("22wr.rec", "rb") as rec_file:
        rec = load_rec(rec_file)
    fig = draw_rec(rec, lev)
    fig.write_html("rec_plot.html")
