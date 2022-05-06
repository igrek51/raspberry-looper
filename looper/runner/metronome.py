from typing import List
from pathlib import Path

import wave
import numpy as np

from looper.runner.config import Config
from looper.runner.dsp import SignalProcessor


class Metronome:
    def __init__(self, config: Config) -> None:
        self.config = config

    def generate_beat(self, bpm: float, beats: int, bars: int) -> List[np.array]:
        chunk_length_s = self.config.chunk_length_s
        beat_period_s = 60 / bpm
        chunks_num = int(beat_period_s * beats / chunk_length_s)
        samples_num = self.config.chunk_size * chunks_num
        samples_per_beat = int(beat_period_s * self.config.sampling_rate)

        beat_high = self.load_wav_array(Path('sfx') / 'metronome-beat-high.wav')
        beat_low = self.load_wav_array(Path('sfx') / 'metronome-beat-low.wav')

        track = np.zeros(samples_num, dtype=np.int16)

        for beat in range(beats):
            if beat == 0:  # high beat
                _add_track_at_offset(track, beat_high, 0)
            else: # low beat
                _add_track_at_offset(track, beat_low, beat * samples_per_beat)

        dsp = SignalProcessor(self.config)
        track = dsp.amplify(track, -17)

        return np.split(track, chunks_num) * bars

    def load_wav_array(self, path: Path) -> np.array:
        ifile = wave.open(str(path))
        samples = ifile.getnframes()
        audio = ifile.readframes(samples)                                                                          
        return np.frombuffer(audio, dtype=np.int16)

def _add_track_at_offset(track: np.array, sound: np.array, offset: int):
    for sound_index in range(len(sound)):
        if sound_index + offset < len(track):
            track[offset + sound_index] += sound[sound_index]
