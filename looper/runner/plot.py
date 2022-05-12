import io
import random

import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from starlette.responses import StreamingResponse
from looper.runner.looper import Looper
from looper.runner.sample import sample_format_max_amplitude

from looper.runner.track import Track


def generate_track_plot(track: Track, looper: Looper) -> StreamingResponse:
    matplotlib.rcParams["agg.path.chunksize"] = 10_000
    matplotlib.style.use("fast")

    max_amp = sample_format_max_amplitude(looper.config.sample_format)
    if len(track.loop_chunks) == 0:
        all_chunks = looper.dsp.silence()
    else:
        all_chunks = np.concatenate(track.loop_chunks)
        all_chunks = all_chunks / max_amp

    figure = plt.figure()
    figure.set_size_inches((1260 - 52) / 100, (320 - 29) / 100)
    figure.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
    plt.margins(0, 0)
    color = random.choice(["r", "g", "b", "c", "m", "y"])

    plt.plot(all_chunks, color=color, marker="", linewidth=0.2)

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format="png", dpi=100, bbox_inches="tight", pad_inches=0)

    img_buffer.seek(0)
    return StreamingResponse(img_buffer, media_type="image/png")


def plot_series(series: np.array):
    matplotlib.rcParams["agg.path.chunksize"] = 10_000
    matplotlib.style.use("fast")
    figure = plt.figure()
    figure.set_size_inches((1260 - 52) / 100, (320 - 29) / 100)
    figure.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
    plt.margins(0, 0)
    color = random.choice(["r", "g", "b", "c", "m", "y"])
    plt.plot(series, color=color, marker="", linewidth=0.2)
