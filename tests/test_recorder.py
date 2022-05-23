from pathlib import Path
from typing import Optional

import numpy as np
from pydub import AudioSegment

from looper.runner.config import Config
from looper.runner.dsp import SignalProcessor
from looper.runner.recorder import save_mp3
from looper.runner.sample import sample_format_max_amplitude


def test_save_recording():
    config = Config()
    dsp = SignalProcessor(config)
    amplitude = sample_format_max_amplitude(config.sample_format)
    sine = dsp.sine(frequency=440, amplitude=amplitude)

    frames_left = 20

    def frames_channel() -> Optional[np.array]:
        nonlocal frames_left
        if frames_left == 0:
            return None
        else:
            frames_left -= 1
        return sine

    save_mp3('out/test.mp3', frames_channel, config)

    assert not Path('out/test.wav').exists()
    assert Path('out/test.mp3').exists()

    audio = AudioSegment.from_mp3('out/test.mp3')
    assert 0.400 <= audio.duration_seconds <= 0.440
    assert -1 < audio.max_dBFS < 1
