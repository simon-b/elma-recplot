import numpy as np
from elma_recplot.elma_loader import Rec
import plotly.graph_objects as go

KUSKI_COLOR = "#1f77b4"
HEAD_COLOR = "#ff7f0e"
L_WHEEL_COLOR = "#2ca02c"
R_WHEEL_COLOR = "#d62728"


def draw_rec(rec: Rec) -> go.Figure:
    fig = go.Figure()
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
    _xx = _xx.set(~rec.frames["is_gasing_left"], np.nan)
    fig.add_trace(
        go.Scatter(
            x=_xx,
            y=rec.frames["l_wheel_y"],
            line=dict(color=L_WHEEL_COLOR, width=6),
            mode="lines",
            name="Left wheel gas",
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
    _xx = _xx.set(~rec.frames["is_gasing_right"], np.nan)
    fig.add_trace(
        go.Scatter(
            x=_xx,
            y=rec.frames["r_wheel_y"],
            line=dict(color=R_WHEEL_COLOR, width=6),
            mode="lines",
            name="Left wheel gas",
        )
    )
    fig.update_layout(
        xaxis=dict(scaleanchor="y", visible=False),
        yaxis=dict(scaleratio=1, visible=False),
        plot_bgcolor="rgba(0, 0, 0, 0)",
        paper_bgcolor="rgba(0, 0, 0, 0)",
    )
    return fig
