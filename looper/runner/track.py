from dataclasses import dataclass, field
from typing import List

import numpy as np

from looper.runner.config import Config
from looper.runner.dsp import SignalProcessor


@dataclass
class Track:
    index: int
    config: Config

    recording: bool = False
    playing: bool = False
    empty: bool = True
    loop_chunks: List[np.array] = field(default_factory=list)

    def set_empty(self, chunks_num: int):
        dsp = SignalProcessor(self.config)
        self.loop_chunks = [dsp.silence() for i in range(chunks_num)]
        self.empty = True
    
    def set_track(self, chunks: List[np.array]):
        self.loop_chunks = chunks
        self.empty = False

    def toggle_play(self):
        if self.playing:
            self.playing = False
        elif not self.empty:
            self.playing = True

    def clear(self):
        self.recording = False
        self.playing = False
        self.empty = True
        self.loop_chunks = []
