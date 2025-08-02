import requests
from elma_recplot.util import init_logging
from cachecontrol import CacheControl
from cachecontrol.caches import SeparateBodyFileCache
from io import BytesIO

# Cache response content for files; valid rec/lev files but obfuscated names...
sess = CacheControl(requests.Session(), cache=SeparateBodyFileCache(".web_cache"))


def get_lev_by_id(lev_id: int):
    response = sess.get(
        "https://api.elma.online/dl/level/{lev_id}".format(lev_id=lev_id)
    )
    response.raise_for_status()
    return BytesIO(response.content)


def get_rec_by_id_and_name(rec_id: str, rec_name: str):
    response = sess.get(
        "https://space.elma.online/replays/{rec_id}/{rec_name}".format(
            rec_id=rec_id, rec_name=rec_name
        )
    )
    response.raise_for_status()
    return BytesIO(response.content)


def get_latest_replays(page=0, num=20):
    response = requests.get(
        "https://api.elma.online/api/replay",
        params={
            "page": page,
            "pageSize": num,
            "sortBy": "uploaded",
            "order": "desc",
            "levelPack": 0,
        },
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    init_logging()
    from elma_recplot.elma_loader import load_rec, load_lev
    from elma_recplot.plot import draw_rec

    draw_rec(
        load_rec(get_rec_by_id_and_name("ecl8e9chww", "DODGEPIPTm1353.rec")),
        load_lev(get_lev_by_id(194114)),
    ).write_html("rec_plot.html")
