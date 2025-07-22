import struct
import logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
VOLT_RIGHT=6
VOLT_LEFT=7
HEADER_SIZE = 36
MAGIC_TIME_SCALER = 2.2893772893772897
REL_POS_SCALER = 1000
HEADER_FORMAT_STR = "I 12x I 12s 4x"
assert struct.calcsize(HEADER_FORMAT_STR) == HEADER_SIZE

fname = "22K3855.rec"

with open(fname, "rb") as f:
    number_of_frames, crc_checksum, level_name = struct.unpack(
        HEADER_FORMAT_STR, f.read(struct.calcsize(HEADER_FORMAT_STR))
    )
    level_name = level_name.decode("latin1")
    logger.info(f"Number of frames: {number_of_frames}")
    logger.info(f"Checksum: {crc_checksum}")
    logger.info(f"level_name: {level_name}")

    data = pd.DataFrame(
        data={
            "x": np.frombuffer(f.read(4 * number_of_frames), dtype="f4"),
            "y": np.frombuffer(f.read(4 * number_of_frames), dtype="f4"),
            "l_wheel_x_rel": np.frombuffer(f.read(2 * number_of_frames), dtype="i2"),
            "l_wheel_y_rel": np.frombuffer(f.read(2 * number_of_frames), dtype="i2"),
            "r_wheel_x_rel": np.frombuffer(f.read(2 * number_of_frames), dtype="i2"),
            "r_wheel_y_rel": np.frombuffer(f.read(2 * number_of_frames), dtype="i2"),
            "head_x_rel": np.frombuffer(f.read(2 * number_of_frames), dtype="i2"),
            "head_y_rel": np.frombuffer(f.read(2 * number_of_frames), dtype="i2"),
            "rot": np.frombuffer(f.read(2 * number_of_frames), dtype="i2"),
            "left_wheel_rot": np.frombuffer(f.read(number_of_frames), dtype="i1"),
            "right_wheel_rot": np.frombuffer(f.read(number_of_frames), dtype="i1"),
            "dir_and_throttle": np.frombuffer(f.read(number_of_frames), dtype="i1"),
            "back_wheel": np.frombuffer(f.read(number_of_frames), dtype="i1"),
            "collision_strength": np.frombuffer(f.read(number_of_frames), dtype="i1"),
        }
    )
    logger.info(f"Parsed {len(data)} frames")
    (number_of_events,) = struct.unpack("I", f.read(struct.calcsize("I")))
    logger.info(f"Number of events: {number_of_events}")

    # events_df = pd.DataFrame(data={'timestamp': np.frombuffer(f.read(8 * number_of_events), dtype="f8")})

    event_dtype = np.dtype(
        [
            ("timestamp", np.float64),
            ("event_info", np.uint16),
            ("event_type", np.uint8),
            ("unknown_1", np.uint8),
            ("event_info_2", np.float32),
        ]
    )
    events_df = pd.DataFrame(np.frombuffer(
        f.read(16 * number_of_events), dtype=event_dtype, count=number_of_events
    ))

data["t"] = data.index * 1.0 / 30
import IPython
IPython.embed()

data["l_wheel_x"] = data.x + data.l_wheel_x_rel / REL_POS_SCALER
data["l_wheel_y"] = data.y + data.l_wheel_y_rel / REL_POS_SCALER
data["r_wheel_x"] = data.x + data.r_wheel_x_rel / REL_POS_SCALER
data["r_wheel_y"] = data.y + data.r_wheel_y_rel / REL_POS_SCALER
data["head_x"] = data.y + data.head_x_rel / REL_POS_SCALER
data["head_y"] = data.y + data.head_y_rel / REL_POS_SCALER

data["is_gasing"] = (data.dir_and_throttle & 0b1).astype(bool)
data["is_right"] = (data.dir_and_throttle & 0b10).astype(bool)

import plotly.express as px
import plotly.graph_objects as go

fig = px.scatter(x=data.x, y=data.y, title="Scatter Plot using Plotly")
fig = go.Figure(data=go.Scatter(x=data.x, y=data.y, mode="lines+markers", name="Kuski"))
fig.write_html("path.html")

fig = go.Figure(
    data=go.Scatter(
        x=data.l_wheel_x, y=data.l_wheel_y, mode="lines+markers", name="Left wheel"
    )
)
fig.add_trace(
    go.Scatter(
        x=data.r_wheel_x, y=data.r_wheel_y, mode="lines+markers", name="Right wheel"
    )
)
fig.update_layout(
    xaxis=dict(
        scaleanchor="y"
    ),  # This ensures the x-axis scale is anchored to the y-axis
    yaxis=dict(
        scaleratio=1
    ),  # This sets the ratio of the y-axis scale to 1:1 with the x-axis
)
fig.write_html("relative_wheels.html")


fig = go.Figure()
fig.add_trace(go.Scatter(x=data.x, y=data.y, mode="lines", name="Kuski"))
fig.add_trace(
    go.Scatter(
        x=data.l_wheel_x,
        y=data.l_wheel_y,
        line=dict(color="red"),
        mode="lines",
        name="Left wheel",
    )
)
_xx = data.l_wheel_x.copy()
_xx[~(data.is_right & data.is_gasing)] = np.nan
fig.add_trace(
    go.Scatter(
        x=_xx,
        y=data.l_wheel_y,
        line=dict(color="red", width=6),
        mode="lines",
        name="Left wheel gas",
    )
)
fig.add_trace(
    go.Scatter(
        x=data.r_wheel_x,
        y=data.r_wheel_y,
        line=dict(color="purple"),
        mode="lines",
        name="Right wheel",
    )
)
_xx = data.r_wheel_x.copy()
_xx[~(~data.is_right & data.is_gasing)] = np.nan
fig.add_trace(
    go.Scatter(
        x=_xx,
        y=data.r_wheel_y,
        line=dict(color="purple", width=6),
        mode="lines",
        name="Right wheel gas",
    )
)
fig.update_layout(
    xaxis=dict(
        scaleanchor="y"
    ),  # This ensures the x-axis scale is anchored to the y-axis
    yaxis=dict(
        scaleratio=1
    ),  # This sets the ratio of the y-axis scale to 1:1 with the x-axis
)
fig.write_html("wheels.html")


from elma.models import Level

lev = Level.load("QWQUU022.lev")

for obj in lev.objects:
    if obj.type == 4:
        start_x, start_y = obj.point.x, obj.point.y

polygons = sorted(lev.ground_polygons, key=lambda p: p.area(), reverse=True)
for idx, poly in enumerate(polygons):
    if poly.is_filled():
        polygon_x = np.array([p.x for p in poly.points])  # - start_x
        polygon_y = -1.0 * np.array([p.y for p in poly.points])  # - start_y
        fig.add_trace(
            go.Scatter(
                x=polygon_x,
                y=polygon_y,
                mode="lines",
                fill="toself",
                line=dict(color="rgba(0, 0, 0, 0)"),
                name=f"Polygon_{idx}",
                fillcolor="rgba(65, 105, 225, 0.2)",
            )
        )
outer_poly = polygons[0]
if not outer_poly.is_filled():
    poly_x = np.array([p.x for p in outer_poly.points])
    poly_y = -1.0 * np.array([p.y for p in outer_poly.points])
    fig.add_trace(
        go.Scatter(
            x=np.append(poly_x, poly_x[0]),
            y=np.append(poly_y, poly_y[0]),
            mode="lines",
            name="Outer",
        )
    )

for _, row in events_df[events_df.event_type.isin({VOLT_LEFT, VOLT_RIGHT})].sort_values(by=["timestamp", "event_type"]).iterrows():
    timestamp = row.timestamp * MAGIC_TIME_SCALER
    type = row.event_type
    logger.info(f"Drawing volt at t={timestamp}")
    idx = np.searchsorted(data.t, timestamp)
    logger.info(f"Drawing at frame t={data.t[idx]}")
    _x = [data.l_wheel_x[idx], data.x[idx], data.r_wheel_x[idx]]
    _y = [data.l_wheel_y[idx], data.y[idx], data.r_wheel_y[idx]]
    color = "yellow" if row.event_type == VOLT_LEFT else "green"
    width = 2 if row.event_type == VOLT_LEFT else 4
    # Trust that left volts are drawn after
    fig.add_trace(
        go.Scatter(
            x=_x,
            y=_y,
            mode="lines",
            line=dict(color=color, width=width),
            showlegend=False,
            name=f"event {idx}"
        )
    )

fig.add_trace(go.Scatter(
    x=[None],
    y=[None],
    mode='lines',
    line=dict(color="yellow", width=2),
    name='Left volt'
))
fig.add_trace(go.Scatter(
    x=[None],
    y=[None],
    mode='lines',
    line=dict(color="green", width=4),
    name='Right volt'
))

# SKIP_FRAME = 10
# for frame in range(0, number_of_frames, SKIP_FRAME):
#     _x = [data.l_wheel_x[frame], data.x[frame], data.r_wheel_x[frame]]
#     _y = [data.l_wheel_y[frame], data.y[frame], data.r_wheel_y[frame]]
#     fig.add_trace(
#         go.Scatter(
#             x=_x,
#             y=_y,
#             mode="lines",
#             line=dict(color="yellow"),
#             showlegend=False,
#         )
#     )

fig.update_layout(
    #title="Plot with Manual Legend Entry",
    #xaxis_title="X Axis",
    #yaxis_title="Y Axis",
    showlegend=True,
    plot_bgcolor='white',  # Set plot background color to white
    #paper_bgcolor='white'  # Set figure background color to white
)
fig.write_html("wheels_and_poly.html")

import IPython

IPython.embed()

