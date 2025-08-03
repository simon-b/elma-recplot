import requests
from cachecontrol import CacheControl
from cachecontrol.caches import SeparateBodyFileCache
from io import BytesIO
from cachecontrol.heuristics import ExpiresAfter

# Cache response content for files; valid rec/lev files but obfuscated names...
sess = CacheControl(
    requests.Session(),
    cache=SeparateBodyFileCache(".eol_cache"),
    heuristic=ExpiresAfter(days=30),
)


def get_lev_by_id(lev_id: int) -> BytesIO:
    response = sess.get(
        "https://api.elma.online/dl/level/{lev_id}".format(lev_id=lev_id)
    )
    response.raise_for_status()
    return BytesIO(response.content)


def get_rec_by_id_and_name(rec_id: str, rec_name: str) -> BytesIO:
    response = sess.get(
        "https://space.elma.online/replays/{rec_id}/{rec_name}".format(
            rec_id=rec_id, rec_name=rec_name
        )
    )
    response.raise_for_status()
    return BytesIO(response.content)


def get_latest_replays(page=0, num=20) -> dict:
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
