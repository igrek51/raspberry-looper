import io

import matplotlib.pyplot as plt
import numpy as np
from starlette.responses import StreamingResponse
from looper.runner.looper import Looper

from looper.runner.track import Track


def generate_track_plot(track: Track, looper: Looper) -> StreamingResponse:
    if len(track.loop_chunks) == 0:
        all_chunks = looper.dsp.silence()
    else:
        all_chunks = np.concatenate(track.loop_chunks)

    plt.figure(figsize=(18, 4))
    plt.plot(all_chunks)
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png')
    img_buffer.seek(0)

    return StreamingResponse(img_buffer, media_type="image/png")
