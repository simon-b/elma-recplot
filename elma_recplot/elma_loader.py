import logging
import struct
import typing
from dataclasses import dataclass
from enum import Enum

import numpy as np
import polars as pl

logger = logging.getLogger(__name__)

#  TODO: verify these constants
MAGIC_TIME_SCALER = 0.001 / (0.182 * 0.0024)
REL_POS_SCALER = 1000
REC_HEADER_SIZE = 36
REC_HEADER_FORMAT_STR = "I 12x I 12s 4x"

LEV_HEADER_FORMAT_STR = "<5s 2x I 32x 51s 16s 10s 10s d"
LEV_HEADER_SIZE = 138
LEV_ITEM_COUNT_SUBTRAHEND = 0.464_364_3  # from elma-rust; what is this?
assert struct.calcsize(REC_HEADER_FORMAT_STR) == REC_HEADER_SIZE
assert struct.calcsize(LEV_HEADER_FORMAT_STR) == LEV_HEADER_SIZE


# Two enums defined, but not actually stored in polars df.
#  Can be stored via `pl.col("...")..map_elements(ObjType, return_dtype=object)`
#  But this column will then not permit all polars operations well
class ObjType(Enum):
    EXIT = 1
    APPLE = 2
    KILLER = 3
    PLAYER = 4


class EventType(Enum):
    OBJ_TOUCH = 0
    GROUND = 1
    APPLE = 4
    TURN = 5
    VOLT_LEFT = 7
    VOLT_RIGHT = 6


@dataclass
class Rec:
    checksum: int
    lev_name: str
    frames: pl.DataFrame  # TODO: pandera
    events: pl.DataFrame  # TODO: pandera


@dataclass
class Lev:
    name: str
    lgr: str
    ground: str
    sky: str
    polygons: pl.DataFrame  # TODO: pandera
    polygons_coords: pl.DataFrame  # TODO: pandera
    objects: pl.DataFrame  # TODO: pandera


def _col_from_buffer(buffer, size, dtype):
    # Works with simple or composite dtypes
    return np.frombuffer(buffer.read((np.dtype(dtype).itemsize) * size), dtype=dtype)


def load_rec(rec_data: typing.BinaryIO) -> Rec:
    number_of_frames, crc_checksum, level_name = struct.unpack(
        REC_HEADER_FORMAT_STR, rec_data.read(struct.calcsize(REC_HEADER_FORMAT_STR))
    )
    level_name = level_name.decode("latin1").split(".")[0] + ".lev"
    logger.info(f"Loaded rec. Frames: {number_of_frames!r}; checksum: {crc_checksum!r}")

    # TODO: possible to load column-major data directly as composite dtype?
    frames = pl.DataFrame(
        data={
            "x": _col_from_buffer(rec_data, number_of_frames, "f4"),
            "y": _col_from_buffer(rec_data, number_of_frames, "f4"),
            "l_wheel_x_rel": _col_from_buffer(rec_data, number_of_frames, "i2"),
            "l_wheel_y_rel": _col_from_buffer(rec_data, number_of_frames, "i2"),
            "r_wheel_x_rel": _col_from_buffer(rec_data, number_of_frames, "i2"),
            "r_wheel_y_rel": _col_from_buffer(rec_data, number_of_frames, "i2"),
            "head_x_rel": _col_from_buffer(rec_data, number_of_frames, "i2"),
            "head_y_rel": _col_from_buffer(rec_data, number_of_frames, "i2"),
            "rot": _col_from_buffer(rec_data, number_of_frames, "i2"),
            "left_wheel_rot": _col_from_buffer(rec_data, number_of_frames, "i1"),
            "right_wheel_rot": _col_from_buffer(rec_data, number_of_frames, "i1"),
            "dir_and_throttle": _col_from_buffer(rec_data, number_of_frames, "i1"),
            "back_wheel": _col_from_buffer(rec_data, number_of_frames, "i1"),
            "collision_strength": _col_from_buffer(rec_data, number_of_frames, "i1"),
        }
    ).with_columns(
        [
            (pl.int_range(pl.len()).cast(pl.Float32) / 30).alias("t"),
            (pl.col("x") + pl.col("l_wheel_x_rel") / REL_POS_SCALER).alias("l_wheel_x"),
            (pl.col("y") + pl.col("l_wheel_y_rel") / REL_POS_SCALER).alias("l_wheel_y"),
            (pl.col("x") + pl.col("r_wheel_x_rel") / REL_POS_SCALER).alias("r_wheel_x"),
            (pl.col("y") + pl.col("r_wheel_y_rel") / REL_POS_SCALER).alias("r_wheel_y"),
            (pl.col("x") + pl.col("head_x_rel") / REL_POS_SCALER).alias("head_x"),
            (pl.col("y") + pl.col("head_y_rel") / REL_POS_SCALER).alias("head_y"),
            # TODO: validate the following interpretation of "dir_and_throttle"
            ((pl.col("dir_and_throttle") & 0b1) == 0b1).alias("is_gasing"),
            ((pl.col("dir_and_throttle") & 0b10) == 0b10).alias("is_right"),
            ((pl.col("dir_and_throttle") & 0b11) == 0b11).alias("is_gasing_right"),
            ((pl.col("dir_and_throttle") & 0b11) == 0b01).alias("is_gasing_left"),
        ]
    )
    logger.info(f"Loaded {len(frames)} frames")

    (number_of_events,) = struct.unpack("I", rec_data.read(struct.calcsize("I")))
    logger.info(f"Number of events: {number_of_events}")
    events_df = pl.DataFrame(
        _col_from_buffer(
            rec_data,
            number_of_events,
            np.dtype(
                [
                    ("timestamp", np.float64),
                    ("event_info", np.uint16),
                    ("event_type", np.uint8),
                    ("unknown_1", np.uint8),
                    ("event_info_2", np.float32),
                ]
            ),
        )
    ).with_columns(
        pl.col("timestamp") * MAGIC_TIME_SCALER,
    )
    logger.info(f"Loaded {len(events_df)} events")

    return Rec(
        checksum=crc_checksum,
        lev_name=level_name,
        frames=frames,
        events=events_df,
    )


def _poly_area(x: pl.Series, y: pl.Series) -> float:
    # TODO: can this be done with polars series directly?
    _x = x.to_numpy()
    _y = y.to_numpy()
    area = 0.5 * (np.dot(_x, np.roll(_y, 1)) - np.dot(_y, np.roll(_x, 1)))
    return area


def load_lev(lev_data: typing.BinaryIO) -> Lev:
    (version, link, level_name, lgr_name, ground_name, sky_name, num_polygons) = (
        struct.unpack(
            LEV_HEADER_FORMAT_STR, lev_data.read(struct.calcsize(LEV_HEADER_FORMAT_STR))
        )
    )
    level_name, lgr_name, ground_name, sky_name = map(
        lambda el: el.split(b"\0")[0].decode("latin-1"),
        (level_name, lgr_name, ground_name, sky_name),
    )
    num_polygons = round(num_polygons - LEV_ITEM_COUNT_SUBTRAHEND)
    logger.info(
        f"Loaded lev. "
        f"Version: {version!r}; "
        f"link: {link!r}; "
        f"Name: {level_name!r}; "
        f"LGR: {lgr_name!r}; Ground texture: {ground_name!r}; "
        f"Sky texture: {sky_name!r} "
        f"Polygons: {num_polygons!r} "
    )

    # Load polys
    summary_rows = []
    poly_coords_dfs = []
    poly_header_format_str = "<I I"
    for p_idx in range(num_polygons):
        grass, num_vertices = struct.unpack(
            poly_header_format_str,
            lev_data.read(struct.calcsize(poly_header_format_str)),
        )
        grass = bool(grass)
        poly_coords_df = pl.DataFrame(
            _col_from_buffer(
                lev_data,
                num_vertices,
                np.dtype([("x", np.float64), ("y", np.float64)]),
            )
        )
        poly_coords_df = poly_coords_df.with_columns(
            pl.lit(p_idx).alias("index"),
            pl.col("y") * -1.0,  # TODO: why negative?
        )
        poly_coords_dfs.append(poly_coords_df)

        summary_rows.append(
            {
                "index": p_idx,
                "is_grass": grass,
                "n_vertices": num_vertices,
                "area": _poly_area(poly_coords_df["x"], poly_coords_df["y"]),
            }
        )

    polygons = pl.DataFrame(summary_rows)
    polygons_coords = pl.concat(poly_coords_dfs)
    logger.info(f"Loaded {len(polygons)} polygons")

    # Load objects
    # object_count = (remaining.read_f64::<LE>()? - 0.464_364_3).round() as usize;
    (n_objects,) = struct.unpack("d", lev_data.read(struct.calcsize("d")))
    n_objects = round(n_objects - LEV_ITEM_COUNT_SUBTRAHEND)
    logger.info(f"Number of objects: {n_objects}")
    objects_df = pl.DataFrame(
        _col_from_buffer(
            lev_data,
            n_objects,
            np.dtype(
                [
                    ("x", np.float64),
                    ("y", np.float64),
                    ("object_type", np.int32),
                    ("gravity", np.int32),
                    ("animation", np.int32),
                ]
            ),
        )
    ).with_columns(
        pl.col("y") * -1.0,
    )

    return Lev(
        name=level_name,
        lgr=lgr_name,
        ground=ground_name,
        sky=sky_name,
        polygons=polygons,
        polygons_coords=polygons_coords,
        objects=objects_df,
    )
