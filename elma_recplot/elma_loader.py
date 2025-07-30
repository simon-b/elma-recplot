import struct
import logging
import numpy as np
import polars as pl
from dataclasses import dataclass

logger = logging.getLogger(__name__)

#  TODO: verify these constants
VOLT_RIGHT = 6
VOLT_LEFT = 7
MAGIC_TIME_SCALER = 0.001 / (0.182 * 0.0024)
REL_POS_SCALER = 1000
HEADER_SIZE = 36
REC_HEADER_FORMAT_STR = "I 12x I 12s 4x"

assert struct.calcsize(REC_HEADER_FORMAT_STR) == HEADER_SIZE


@dataclass
class Rec:
    checksum: int
    lev_name: str
    frames: pl.DataFrame  # TODO: pandera
    events: pl.DataFrame  # TODO: pandera


@dataclass
class Lev:
    polygons: pl.DataFrame  # TODO: pandera


def load_rec(fname) -> Rec:
    with open(fname, "rb") as f:
        number_of_frames, crc_checksum, level_name = struct.unpack(
            REC_HEADER_FORMAT_STR, f.read(struct.calcsize(REC_HEADER_FORMAT_STR))
        )
        level_name = level_name.decode("latin1").split(".")[0] + ".lev"
        logger.info(
            f"Loaded rec: lev: {fname!r}; frames: {number_of_frames!r}; checksum: {crc_checksum!r}"
        )

        def _col_from_buffer(buffer, size, dtype):
            return np.frombuffer(
                buffer.read((np.dtype(dtype).itemsize) * size), dtype=dtype
            )

        frames = pl.DataFrame(
            data={
                "x": _col_from_buffer(f, number_of_frames, "f4"),
                "y": _col_from_buffer(f, number_of_frames, "f4"),
                "l_wheel_x_rel": _col_from_buffer(f, number_of_frames, "i2"),
                "l_wheel_y_rel": _col_from_buffer(f, number_of_frames, "i2"),
                "r_wheel_x_rel": _col_from_buffer(f, number_of_frames, "i2"),
                "r_wheel_y_rel": _col_from_buffer(f, number_of_frames, "i2"),
                "head_x_rel": _col_from_buffer(f, number_of_frames, "i2"),
                "head_y_rel": _col_from_buffer(f, number_of_frames, "i2"),
                "rot": _col_from_buffer(f, number_of_frames, "i2"),
                "left_wheel_rot": _col_from_buffer(f, number_of_frames, "i1"),
                "right_wheel_rot": _col_from_buffer(f, number_of_frames, "i1"),
                "dir_and_throttle": _col_from_buffer(f, number_of_frames, "i1"),
                "back_wheel": _col_from_buffer(f, number_of_frames, "i1"),
                "collision_strength": _col_from_buffer(f, number_of_frames, "i1"),
            }
        )
        logger.info(f"Loaded {len(frames)} frames")

        (number_of_events,) = struct.unpack("I", f.read(struct.calcsize("I")))
        logger.info(f"Number of events: {number_of_events}")
        event_dtype = np.dtype(
            [
                ("timestamp", np.float64),
                ("event_info", np.uint16),
                ("event_type", np.uint8),
                ("unknown_1", np.uint8),
                ("event_info_2", np.float32),
            ]
        )
        events_df = pl.DataFrame(
            np.frombuffer(
                f.read(16 * number_of_events), dtype=event_dtype, count=number_of_events
            )
        )
        logger.info(f"Loaded {len(events_df)} events")

    frames = frames.with_columns(
        (pl.int_range(pl.len()).cast(pl.Float32) / 30).alias("t")
    )

    frames = frames.with_columns(
        [
            (pl.col("x") + pl.col("l_wheel_x_rel") / REL_POS_SCALER).alias("l_wheel_x"),
            (pl.col("y") + pl.col("l_wheel_y_rel") / REL_POS_SCALER).alias("l_wheel_y"),
            (pl.col("x") + pl.col("r_wheel_x_rel") / REL_POS_SCALER).alias("r_wheel_x"),
            (pl.col("y") + pl.col("r_wheel_y_rel") / REL_POS_SCALER).alias("r_wheel_y"),
            (pl.col("x") + pl.col("head_x_rel") / REL_POS_SCALER).alias("head_x"),
            (pl.col("y") + pl.col("head_y_rel") / REL_POS_SCALER).alias("head_y"),
            # TODO: validate the following intretation of "dir_and_throttle"
            ((pl.col("dir_and_throttle") & 0b1) != 0).alias("is_gasing"),
            ((pl.col("dir_and_throttle") & 0b10) != 0).alias("is_right"),
            ((pl.col("dir_and_throttle") & 0b11) == 0b11).alias("is_gasing_right"),
            ((pl.col("dir_and_throttle") & 0b11) == 0b01).alias("is_gasing_left"),
        ]
    )

    return Rec(
        checksum=crc_checksum,
        lev_name=level_name,
        frames=frames,
        events=events_df,
    )
