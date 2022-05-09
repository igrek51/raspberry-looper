from dataclasses import dataclass, field
from typing import List, Optional

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
    volume: float = 0  # dB
    name: str = ''
    loop_chunks: List[np.array] = field(default_factory=list)
    recording_from: int = -1
    dsp: SignalProcessor = None

    _last_recorded_chunk: Optional[np.array] = None
    _last_recorded_position: int = -1

    def __post_init__(self):
        self.dsp = SignalProcessor(self.config)

    def set_empty(self, chunks_num: int):
        self.loop_chunks = [self.dsp.silence() for i in range(chunks_num)]
        self.empty = True
    
    def set_track(self, chunks: List[np.array], fade: bool):
        if fade:
            self.dsp.fade_in(chunks[0])
            self.dsp.fade_out(chunks[-1])
        self.loop_chunks = chunks
        self.empty = False

    def overdub(self, input_chunk: np.array, position: int):
        # fade in first chunk
        if position == self.recording_from:
            self.dsp.fade_in(input_chunk)
        self.loop_chunks[position] += input_chunk
        self.empty = False
        self._last_recorded_chunk = input_chunk
        self._last_recorded_position = position
        # start playing after reaching a full cycle
        if self.recording_from >= 0 and position == shift_loop_position(self.recording_from, -1, len(self.loop_chunks)):
            self.playing = True
            self.recording_from = -1

    def start_recording(self, at_position: int):
        self.recording = True
        self.recording_from = at_position
        self._last_recorded_chunk = None
        log.debug('overdubbing track...', track_id=self.index)

    def stop_recording(self):
        self.recording = False
        self.playing = True
        # fade out last chunk
        if self._last_recorded_chunk is not None:
            self.loop_chunks[self._last_recorded_position] -= self._last_recorded_chunk
            self.dsp.fade_out(self._last_recorded_chunk)
            self.loop_chunks[self._last_recorded_position] += self._last_recorded_chunk
        log.info('overdub stopped', track_id=self.index)

    def toggle_play(self):
        if self.playing:
            self.playing = False
            log.debug('track muted', track_id=self.index)
        else:
            if self.empty:
                log.warn('cannot start playing empty track', track_id=self.index)
            else:
                self.playing = True
                log.debug('track unmuted', track_id=self.index)

    def current_playback(self, position: int) -> np.array:
        chunk = self.loop_chunks[position]
        return self.dsp.amplify(chunk, self.volume)

    def compute_loudness(self) -> float:
        return self.dsp.compute_loudness(self.loop_chunks)

    def clear(self):
        self.recording = False
        self.playing = False
        self.set_empty(len(self.loop_chunks))


def shift_loop_position(position: int, shift: int, loop_length: int) -> int:
    if loop_length == 0:
        return 0
    return (position + shift + loop_length) % loop_length
