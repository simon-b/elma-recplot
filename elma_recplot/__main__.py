from elma_recplot.elma_loader import load_rec, load_lev
from elma_recplot.plot import draw_rec
from elma_recplot.util import init_logging


if __name__ == "__main__":
    init_logging()
    with open("biglev.lev", "rb") as lev_file:
        lev = load_lev(lev_file)
    with open("bigrec.rec", "rb") as rec_file:
        rec = load_rec(rec_file)
    fig = draw_rec(rec, lev)
    fig.update_layout(title_text="My Plot Title")
    fig.write_html("bigrec.html")
