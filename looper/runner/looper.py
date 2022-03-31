import asyncio
from dataclasses import dataclass, field
from typing import List
from enum import Enum

from nuclear.sublog import log
import pyaudio
import numpy as np

from looper.runner.config import Config
from looper.runner.pinout import Pinout
from looper.runner.track import Track


class LoopPhase(Enum):
    VOID = 1  # not started yet
    RECORDING_MASTER = 2  # recording first, master track
    LOOP = 3  # loop length determined, looping recorded tracks 


@dataclass
class Looper:
    pinout: Pinout
    config: Config

    phase: LoopPhase = LoopPhase.VOID
    current_position: int = 0  # current buffer (chunk) index
    master_chunks: List[np.array] = field(default_factory=list)
    tracks: List[Track] = field(default_factory=list)

    def reset(self):
        self.phase = LoopPhase.VOID
        self.current_position = 0
        self.master_chunks = []
        self.tracks = []
        for track_idx in range(self.config.tracks_num):
            track = Track(track_idx, self.config)
            self.tracks.append(track)
        self.update_leds()

    def run(self) -> None:
        log.debug("Initializing PyAudio...")
        self.pa = pyaudio.PyAudio()
        self.reset()

        def stream_callback(in_data, frame_count, time_info, status_flags):
            input_chunk = np.frombuffer(in_data, dtype=np.int16)

            # just listening to the input
            if self.phase == LoopPhase.VOID:
                return input_chunk, pyaudio.paContinue

            # Recording master loop
            if self.phase == LoopPhase.RECORDING_MASTER:
                if len(self.master_chunks) < self.config.max_loop_chunks:
                    self.master_chunks.append(input_chunk)
                return input_chunk, pyaudio.paContinue

            # Loop playback + Overdub
            if self.phase == LoopPhase.LOOP:
                # Play input with recorded loops
                out_chunk = self.current_playback(input_chunk)
                self.overdub(input_chunk)
                self.next_chunk()
                return out_chunk, pyaudio.paContinue

        self.loop_stream = self.pa.open(
            format=self.config.format,
            channels=self.config.channels,
            rate=self.config.sampling_rate,
            input=True,
            output=True,
            input_device_index=self.config.in_device,
            output_device_index=self.config.out_device,
            frames_per_buffer=self.config.chunk_size,
            start=False,
            stream_callback=stream_callback,
        )
        self.loop_stream.start_stream()

        self.pinout.loopback_led.pulse(fade_in_time=0.5, fade_out_time=0.5)

        for track in self.tracks:
            self.pinout.on_button_click(
                self.pinout.record_buttons[track.index],
                on_click=lambda: self.toggle_record(track.index),
            )
            self.pinout.on_button_click_and_hold(
                self.pinout.play_buttons[track.index],
                on_click=lambda: self.toggle_play(track.index),
                on_hold=lambda: self.reset_track(track.index),
            )

        log.info('Ready to work')
        try:
            asyncio.run(self.main_loop())
        except KeyboardInterrupt:
            self.close()

    def current_playback(self, input_chunk: np.array) -> np.array:
        active_chunks = [track.loop_chunks[self.current_position]
                         for track in self.tracks
                         if track.playing]
        if len(active_chunks) == 0:
            return input_chunk
        return np.sum(active_chunks) + input_chunk

    def overdub(self, input_chunk: np.array):
        for track in self.tracks:
            if track.recording:
                track.loop_chunks[self.current_position] += input_chunk
                break

    def next_chunk(self):
        self.current_position += 1
        if self.current_position >= len(self.master_chunks):
            self.current_position = 0

    def toggle_record(self, track_idx: int):
        if self.recording:
            self.stop_recording(track_idx)
        else:
            self.start_recording(track_idx)

    def start_recording(self, track_idx: int):
        self.recording = True
        if not self.master_loop_recorded:
            self.current_position = 0
            self.playing = False
            log.debug('recording master loop...')
        else:
            self.playing = True
            log.debug('overdubbing...')
        self.update_leds()

    def stop_recording(self, track_idx: int):
        self.current_position = 0
        self.recording = False
        self.playing = True
        if not self.master_loop_recorded:
            self.master_loop_recorded = True
            loop_duration_s = len(self.master_loop_chunks) * self.config.chunk_length_s
            log.info(f'recorded master loop', 
                chunks=len(self.master_loop_chunks),
                loop_duration_s=loop_duration_s)
        else:   
            log.info(f'overdub stopped')
        self.update_leds()

    def toggle_play(self, track_idx: int):
        self.tracks[track_idx].toggle_playing()
        self.update_leds()

    def reset_track(self, track_idx: int):
        self.tracks[track_idx].reset()
        self.update_leds()

    def update_leds(self):
        for track in self.tracks:
            if track.recording:
                self.pinout.record_leds[track.index].on()
            else:
                self.pinout.record_leds[track.index].off()

            if track.playing:
                self.pinout.play_leds[track.index].on()
            else:
                if track.empty:
                    self.pinout.play_leds[track.index].off()
                else:
                    self.pinout.play_leds[track.index].blink(on_time=0.1, off_time=0.9)

        if self.phase != LoopPhase.LOOP:
            self.pinout.progress_led.off()

    async def main_loop(self):
        await asyncio.gather(
            self.progress_loop(),
        )

    async def progress_loop(self):
        while True:
            if self.phase != LoopPhase.LOOP:
                await asyncio.sleep(0.5)
                continue

            chunks_left = len(self.master_chunks) - self.current_position
            chunks_left_s = chunks_left * self.config.chunk_length_s
            self.pinout.progress_led.pulse(fade_in_time=chunks_left_s, fade_out_time=0, n=1)
            await asyncio.sleep(chunks_left_s)

    def close(self):
        log.debug('closing...')
        self.pinout.init_leds()
        self.loop_stream.stop_stream()
        self.loop_stream.close()
        self.pa.terminate()
        log.info('Stream closed')