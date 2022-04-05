from dataclasses import dataclass, field
from typing import List

import numpy as np
from nuclear.sublog import log

from looper.runner.config import Config
from looper.runner.dsp import SignalProcessor


@dataclass
class Track:
    index: int
    config: Config
    has_gpio: bool  # has corresponding GPIO buttons/LEDs

    recording: bool = False
    playing: bool = False
    empty: bool = True
    loop_chunks: List[np.array] = field(default_factory=list)
    recording_from: int = -1

    def set_empty(self, chunks_num: int):
        dsp = SignalProcessor(self.config)
        self.loop_chunks = [dsp.silence() for i in range(chunks_num)]
        self.empty = True
    
    def set_track(self, chunks: List[np.array]):
        self.loop_chunks = chunks
        self.empty = False

    def overdub(self, input_chunk: np.array, position: int):
        self.loop_chunks[position] = self.loop_chunks[position] + input_chunk
        self.empty = False
        if position == shift_loop_position(self.recording_from, -1, len(self.loop_chunks)):
            self.playing = True  # start playing after reaching a full cycle
            self.recording_from = -1

    def start_recording(self, at_position: int):
        self.recording = True
        self.recording_from = at_position

    def toggle_play(self):
        if self.playing:
            self.playing = False
        else:
            if self.empty:
                log.warn('cannot start playing empty track', track_idx=self.index)
            else:
                self.playing = True

    def clear(self):
        self.recording = False
        self.playing = False
        self.set_empty(len(self.loop_chunks))


def shift_loop_position(position: int, shift: int, loop_length: int) -> int:
    if loop_length == 0:
        return 0
    return (position + shift + loop_length) % loop_length
