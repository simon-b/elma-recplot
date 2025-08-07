import logging

import numpy as np
import plotly.graph_objects as go
import polars as pl
from rich.progress import track

from elma_recplot.elma_loader import VOLT_LEFT, VOLT_RIGHT, Lev, ObjType, Rec

KUSKI_COLOR = "#1f77b4"
HEAD_COLOR = "#ff7f0e"
L_WHEEL_COLOR = "#2ca02c"
R_WHEEL_COLOR = "#d62728"
POLY_FILL_COLOR = "#4169E1"

OBJ_COLORS = {
    ObjType.APPLE: "#ff0000",
    ObjType.EXIT: "#ffde21",
    ObjType.KILLER: "#000000",
    ObjType.PLAYER: "#ff9100",
}
VOLT_COLOR = {
    VOLT_RIGHT: "#000080",
    VOLT_LEFT: "#00D1D5",
}
VOLT_WIDTH = {
    VOLT_RIGHT: 4,
    VOLT_LEFT: 2,
}
ITEM_RADIUS = 0.4
BIKE_COLOR = {
    "wheel": "#000000",
    "head": "#a0fdf5",
}
MAX_DRAW_EVENTS = 500

logger = logging.getLogger(__name__)


def draw_rec(rec: Rec, lev: Lev) -> go.Figure:
    fig = go.Figure()

    add_lev_to_fig(lev, fig)
    add_rec_to_fig(rec, fig)

    fig.update_layout(
        # X/Y scaled equal; no labels
        xaxis=dict(scaleanchor="y", visible=False),
        yaxis=dict(scaleratio=1, visible=False),
        # No BG/grids
        plot_bgcolor="rgba(0, 0, 0, 0)",
        paper_bgcolor="rgba(0, 0, 0, 0)",
        margin={"t": 30, "l": 0, "b": 0, "r": 0},
    )
    return fig


def add_rec_to_fig(rec, fig):
    fig.add_trace(
        go.Scatter(
            x=rec.frames["x"],
            y=rec.frames["y"],
            mode="lines",
            name="Kuski",
            line=dict(color=KUSKI_COLOR),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=rec.frames["head_x"],
            y=rec.frames["head_y"],
            mode="lines",
            name="Head",
            line=dict(color=HEAD_COLOR),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=rec.frames["l_wheel_x"],
            y=rec.frames["l_wheel_y"],
            line=dict(color=L_WHEEL_COLOR),
            mode="lines",
            name="Left wheel",
        )
    )
    _xx = rec.frames["l_wheel_x"].clone()
    # Set NaN for non-gasing frames; right gas -> left wheel gas
    _xx = _xx.set(~rec.frames["is_gasing_right"], None)
    fig.add_trace(
        go.Scatter(
            x=_xx,
            y=rec.frames["l_wheel_y"],
            line=dict(color=L_WHEEL_COLOR, width=6),
            mode="lines",
            name="Left wheel gas",
            opacity=0.5,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=rec.frames["r_wheel_x"],
            y=rec.frames["r_wheel_y"],
            line=dict(color=R_WHEEL_COLOR),
            mode="lines",
            name="Right wheel",
        )
    )
    _xx = rec.frames["r_wheel_x"].clone()
    # Set NaN for non-gasing frames; left gas -> right wheel gas
    _xx = _xx.set(~rec.frames["is_gasing_left"], None)
    fig.add_trace(
        go.Scatter(
            x=_xx,
            y=rec.frames["r_wheel_y"],
            line=dict(color=R_WHEEL_COLOR, width=6),
            mode="lines",
            name="Right wheel gas",
            opacity=0.5,
        )
    )

    events_to_draw = rec.events.filter(
        pl.col("event_type").is_in([VOLT_LEFT, VOLT_RIGHT])
    ).sort("timestamp")
    if len(events_to_draw) > MAX_DRAW_EVENTS:
        logger.warning(
            f"Too many volt events ({len(events_to_draw)}); skipping drawing"
        )
        # Slow AF with too many events added as individual traces/circles\
        # TODO: draw as a single trace per event type
    else:
        logger.info(f"Drawing {len(events_to_draw)} volt events")
        for row in events_to_draw.iter_rows(named=True):
            timestamp = row["timestamp"]
            event_type = row["event_type"]
            if event_type not in {VOLT_LEFT, VOLT_RIGHT}:
                continue
            idx = rec.frames["t"].search_sorted(timestamp)
            if idx >= len(rec.frames["t"]):
                idx -= 1
            if idx >= len(rec.frames["t"]):
                logger.warning(f"Skipping event at t={timestamp}; out of bounds")
                continue

            logger.debug(
                f"Drawing volt at t={timestamp} at frame t={rec.frames['t'][idx]}"
            )
            _x = rec.frames.select(["l_wheel_x", "head_x", "r_wheel_x"]).row(idx)
            _y = rec.frames.select(["l_wheel_y", "head_y", "r_wheel_y"]).row(idx)
            color = VOLT_COLOR[event_type]
            width = VOLT_WIDTH[event_type]
            # Trust that left volts are drawn after
            fig.add_trace(
                go.Scatter(
                    x=_x,
                    y=_y,
                    mode="lines",
                    line=dict(color=color, width=width),
                    showlegend=False,
                    name=f"event {idx}",
                    legendgroup="Volts",
                )
            )
            _lx, _ly, _rx, _ry, _hx, _hy = rec.frames.select(
                "l_wheel_x", "l_wheel_y", "r_wheel_x", "r_wheel_y", "head_x", "head_y"
            ).row(idx)
            _add_circle(fig, _lx, _ly, BIKE_COLOR["wheel"], radius=ITEM_RADIUS)
            _add_circle(fig, _rx, _ry, BIKE_COLOR["wheel"], radius=ITEM_RADIUS)
            # TODO: too large for head?
            _add_circle(fig, _hx, _hy, BIKE_COLOR["head"], radius=ITEM_RADIUS)

    # dummy entries for legend
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            line=dict(color=VOLT_COLOR[VOLT_LEFT], width=2),
            name="Left volt",
            legendgroup="Volts",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            line=dict(color=VOLT_COLOR[VOLT_RIGHT], width=4),
            name="Right volt",
            legendgroup="Volts",
        )
    )


def add_lev_to_fig(lev, fig):
    poly_data = lev.polygons_coords.join(lev.polygons, on="index", how="inner")
    # TODO: if largest poly is filled, we should invert all
    for (idx,), group in poly_data.filter(
        (~pl.col("is_grass")) & (pl.col("area") < 0)
    ).group_by("index"):
        fig.add_trace(
            go.Scatter(
                x=group["x"],
                y=group["y"],
                mode="lines",
                fill="toself",
                line=dict(color="rgba(0, 0, 0, 0)"),
                showlegend=False,
                fillcolor=POLY_FILL_COLOR,
                name=f"Polygon {idx}",
                legendgroup="Polygons",
            )
        )
    largest_poly_idx = (
        lev.polygons.with_columns(pl.col("area").abs().alias("abs_area"))
        .sort("abs_area", descending=True)
        .select(pl.col("index").first())
        .item()
    )
    largest_poly = poly_data.filter(pl.col("index") == largest_poly_idx)
    largest_poly_x, largest_poly_y = largest_poly.select("x", "y")

    fig.add_trace(
        go.Scatter(
            x=pl.concat([largest_poly_x, largest_poly_x.head()]),
            y=pl.concat([largest_poly_y, largest_poly_y.head()]),
            mode="lines",
            line=dict(color=POLY_FILL_COLOR),
            legendgroup="Polygons",
            name="Polygons",
        )
    )
    objs_df = lev.objects.with_columns(
        pl.col("object_type")
        .map_elements(OBJ_COLORS.get, return_dtype=str)
        .alias("color")
    )
    for row in objs_df.iter_rows(named=True):
        _add_circle(
            fig, row["x"], row["y"], row["color"], radius=ITEM_RADIUS, opacity=0.2
        )


def _add_circle(fig, x, y, color, radius=ITEM_RADIUS, opacity=0.2):
    # TODO: possible for these to feature in legend?
    fig.add_shape(
        type="circle",
        xref="x",
        yref="y",
        x0=x - radius,
        y0=y - radius,
        x1=x + radius,
        y1=y + radius,
        line_color=color,
        fillcolor=color,
        opacity=opacity,
    )
