import os
from typing import Callable, Optional
from pathlib import Path

import wave
import numpy as np
from pydub import AudioSegment

from looper.runner.config import Config
from nuclear.sublog import log


def save_wav(filename: str, frames_channel: Callable[[], Optional[np.array]], config: Config):
    log.debug('Saving frames to WAV file', filename=filename)

    Path(filename).parent.mkdir(exist_ok=True, parents=True)

    wav = wave.open(filename, 'w')
    wav.setnchannels(config.channels)
    wav.setsampwidth(config.format_bytes)
    wav.setframerate(config.sampling_rate)

    frames_written = 0
    while True:
        frame = frames_channel()
        if frame is None:
            break
        wav.writeframes(b''.join(frame))
        frames_written += 1

    wav.close()
    duration = frames_written * config.chunk_length_s
    filesize_mb = os.path.getsize(filename) / 1024 / 1024
    log.debug('WAV file saved', filename=filename, chunks_saved=frames_written,
        duration=f'{duration:.2f}s', size=f'{filesize_mb:.2f}MB')


def save_mp3(filename: str, frames_channel: Callable, config: Config):
    tmp_wav_file = Path(filename).with_suffix('.wav')
    save_wav(str(tmp_wav_file), frames_channel, config)

    track = AudioSegment.from_wav(tmp_wav_file)
    track.export(filename, format='mp3')

    tmp_wav_file.unlink()

    filesize_mb = os.path.getsize(filename) / 1024 / 1024
    log.info('MP3 file saved', filename=filename, 
        duration=f'{track.duration_seconds:.2f}s', size=f'{filesize_mb:.2f}MB')
