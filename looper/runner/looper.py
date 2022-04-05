import asyncio
from dataclasses import dataclass, field
from typing import List
from enum import Enum

from nuclear.sublog import log
import pyaudio
import numpy as np

from looper.runner.config import Config
from looper.runner.pinout import Pinout
from looper.runner.save import OutputSaver
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

    @property
    def loop_chunks_num(self) -> int:
        return len(self.master_chunks)
        
    @property
    def loop_duration(self) -> float:
        return len(self.master_chunks) * self.config.chunk_length_s

    @property
    def relative_progress(self) -> float:
        if len(self.master_chunks) == 0:
            return 0
        return self.current_position / len(self.master_chunks)

    def reset(self):
        self.phase = LoopPhase.VOID
        self.current_position = 0
        self.master_chunks = []
        tracks = []
        for track_id in range(self.config.tracks_num):
            has_gpio = track_id < self.config.tracks_gpio_num
            track = Track(track_id, self.config, has_gpio)
            tracks.append(track)
        self.tracks = tracks

    def run(self) -> None:
        log.debug("Initializing PyAudio...")
        self.pa = pyaudio.PyAudio()
        self.reset()
        self.saver = OutputSaver(self.config)

        def stream_callback(in_data, frame_count, time_info, status_flags):
            input_chunk = np.frombuffer(in_data, dtype=np.int16)

            # just listening to the input
            if self.phase == LoopPhase.VOID:
                self.saver.transmit(input_chunk)
                return input_chunk, pyaudio.paContinue

            # Recording master loop
            if self.phase == LoopPhase.RECORDING_MASTER:
                if self.loop_chunks_num < self.config.max_loop_chunks:
                    self.master_chunks.append(input_chunk)
                self.saver.transmit(input_chunk)
                return input_chunk, pyaudio.paContinue

            # Loop playback + Overdub
            if self.phase == LoopPhase.LOOP:
                # Play input with recorded loops
                out_chunk = self.current_playback(input_chunk)
                self.overdub(input_chunk)
                self.next_chunk()
                self.saver.transmit(out_chunk)
                return out_chunk, pyaudio.paContinue

        if self.config.offline:
            return

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
        self.update_leds()
        self.bind_buttons()
    
    def bind_buttons(self):
        for track in self.tracks:
            if track.has_gpio:
                def _toggle_record(track_index: int):
                    return lambda: self.toggle_record(track_index)

                def _toggle_play(track_index: int):
                    return lambda: self.toggle_play(track_index)
                    
                def _reset_track(track_index: int):
                    return lambda: self.reset_track(track_index)

                self.pinout.on_button_click(
                    self.pinout.record_buttons[track.index],
                    on_click=_toggle_record(track.index),
                )
                self.pinout.on_button_click_and_hold(
                    self.pinout.play_buttons[track.index],
                    on_click=_toggle_play(track.index),
                    on_hold=_reset_track(track.index),
                )

    def current_playback(self, input_chunk: np.array) -> np.array:
        active_chunks = [track.loop_chunks[self.current_position]
                         for track in self.tracks
                         if track.playing]
        if len(active_chunks) == 0:
            return input_chunk
        if len(active_chunks) == 1:
            return active_chunks[0] + input_chunk
        return sum(active_chunks) + input_chunk

    def overdub(self, input_chunk: np.array):
        for track in self.tracks:
            if track.recording:
                track.overdub(input_chunk, self.current_position)
                break

    def next_chunk(self):
        self.current_position += 1
        if self.current_position >= self.loop_chunks_num:
            self.current_position = 0

    def toggle_record(self, track_id: int):
        if self.phase == LoopPhase.VOID:
            if track_id != 0:
                log.warn('master loop has to be recorded on first track', track_id=track_id)
                return
            self.start_recording_master()

        elif self.phase == LoopPhase.RECORDING_MASTER:
            if track_id != 0:
                log.warn('master loop has to be stopped on first track', track_id=track_id)
                return
            self.stop_recording_master()

        elif self.phase == LoopPhase.LOOP:
            if self.tracks[track_id].recording:
                self.stop_recording(track_id)
            else:
                self.start_recording(track_id)
        
        self.update_leds()

    def start_recording_master(self):
        self.master_chunks = []
        self.phase = LoopPhase.RECORDING_MASTER
        log.debug('recording master loop...')

    def stop_recording_master(self):
        self.current_position = 0
        self.phase = LoopPhase.LOOP
        for track in self.tracks:
            if track.index == 0:
                track.playing = True
                track.set_track(self.master_chunks)
            else:
                track.set_empty(self.loop_chunks_num)

        loop_duration_s = self.loop_chunks_num * self.config.chunk_length_s
        log.info(f'recorded master loop', 
            chunks=self.loop_chunks_num,
            loop_duration=f'{round(loop_duration_s, 2)}s')

    def start_recording(self, track_id: int):
        if self.phase != LoopPhase.LOOP:
            return
        for track in self.tracks:
            if track.index != track_id:
                track.recording = False
        self.tracks[track_id].start_recording(self.current_position)
        log.debug('overdubbing track...', track=track_id)

    def stop_recording(self, track_id: int):
        if self.phase != LoopPhase.LOOP:
            return
        self.tracks[track_id].recording = False
        self.tracks[track_id].playing = True
        log.info('overdub stopped', track=track_id)

    def toggle_play(self, track_id: int):
        self.tracks[track_id].toggle_play()
        self.update_leds()

    def reset_track(self, track_id: int):
        self.tracks[track_id].clear()
        if self.tracks[track_id].has_gpio:
            self.pinout.record_leds[track_id].blink(on_time=0.1, off_time=0.1, n=2, background=False)
        log.info('track cleared', track=track_id)
        if all(track.empty for track in self.tracks):
            self.reset()
            log.info('all tracks reset, looper void')
        self.update_leds()

    def update_leds(self):
        for track in self.tracks:
            if track.has_gpio:
                if self.is_recording(track.index):
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

    def is_recording(self, track_id: int) -> bool:
        return self.tracks[track_id].recording or (self.phase == LoopPhase.RECORDING_MASTER and track_id == 0)

    def add_track(self):
        track_id = self.config.tracks_num
        self.config.tracks_num += 1
        has_gpio = track_id < self.config.tracks_gpio_num
        track = Track(track_id, self.config, has_gpio)
        self.tracks.append(track)
        if self.phase == LoopPhase.LOOP:
            track.set_empty(self.loop_chunks_num)
        log.info('new track added', tracks_num=self.config.tracks_num)

    async def update_progress(self):
        if self.phase != LoopPhase.LOOP:
            await asyncio.sleep(0.5)
            return

        chunks_left = self.loop_chunks_num - self.current_position
        chunks_left_s = chunks_left * self.config.chunk_length_s
        self.pinout.progress_led.pulse(fade_in_time=chunks_left_s, fade_out_time=0, n=1)
        await asyncio.sleep(chunks_left_s)
    
    def close(self):
        log.debug('closing...')
        if self.config.online:
            self.pinout.init_leds()
            self.loop_stream.stop_stream()
            self.loop_stream.close()
        self.pa.terminate()
        log.info('Stream closed')
