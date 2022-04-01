from pathlib import Path

from pydub import AudioSegment

from looper.runner.config import Config
from looper.runner.dsp import SignalProcessor
from looper.runner.save import save_mp3


def test_save_recording():
    config = Config()
    dsp = SignalProcessor(config)
    sine = dsp.sine(frequency=440)

    frames_left = 20

    def frames_channel():
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
    assert 0.460 <= audio.duration_seconds <= 0.480
    assert -1 < audio.max_dBFS < 1
