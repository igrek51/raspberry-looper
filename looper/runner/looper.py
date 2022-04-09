import asyncio
from dataclasses import dataclass, field
from typing import List
from enum import Enum
from threading import Lock

from nuclear.sublog import log
import pyaudio
import numpy as np

from looper.runner.config import Config
from looper.runner.dsp import SignalProcessor
from looper.runner.pinout import Pinout
from looper.runner.recorder import OutputRecorder
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
    input_volume: float = 0  # dB
    input_muted: bool = False
    output_volume: float = 0  # dB
    output_muted: bool = False
    master_chunks: List[np.array] = field(default_factory=list)
    tracks: List[Track] = field(default_factory=list)
    recorder: OutputRecorder = None
    dsp: SignalProcessor = None
    _lock: Lock = Lock()

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
        with self._lock:
            self.phase = LoopPhase.VOID
            self.current_position = 0
            self.master_chunks = []
            self.tracks = []
            for track_id in range(self.config.tracks_num):
                has_gpio = track_id < self.config.tracks_gpio_num
                track = Track(track_id, self.config, has_gpio)
                self.tracks.append(track)

    def run(self) -> None:
        log.debug("Initializing PyAudio...")
        self.pa = pyaudio.PyAudio()
        self.recorder = OutputRecorder(self.config)
        self.dsp = SignalProcessor(self.config)
        self.reset()

        def stream_callback(in_data, frame_count, time_info, status_flags):
            if self.input_muted:
                input_chunk = self.dsp.silence()
            else:
                input_chunk = np.frombuffer(in_data, dtype=np.int16)
                input_chunk = self.dsp.amplify(input_chunk, self.input_volume)

            with self._lock:
                # just listening to the input
                if self.phase == LoopPhase.VOID:
                    out_chunk = input_chunk

                # Recording master loop
                if self.phase == LoopPhase.RECORDING_MASTER:
                    if self.loop_chunks_num < self.config.max_loop_chunks:
                        self.master_chunks.append(input_chunk)
                    out_chunk = input_chunk

                # Loop playback + Overdub
                if self.phase == LoopPhase.LOOP:
                    # Play input with recorded loops
                    out_chunk = self.current_playback(input_chunk)
                    self.overdub(input_chunk)
                    self.next_chunk()

            if self.output_muted:
                out_chunk = self.dsp.silence()
            else:
                out_chunk = self.dsp.amplify(out_chunk, self.output_volume)

            self.recorder.transmit(out_chunk)
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
        active_chunks = [track.current_playback(self.current_position)
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
        with self._lock:
            self.master_chunks = []
            self.phase = LoopPhase.RECORDING_MASTER
        log.debug('recording master loop...')

    def stop_recording_master(self):
        with self._lock:
            self.current_position = 0
            for track in self.tracks:
                if track.index == 0:
                    track.playing = True
                    track.set_track(self.master_chunks)
                else:
                    track.set_empty(self.loop_chunks_num)
            self.phase = LoopPhase.LOOP

        loop_duration_s = self.loop_chunks_num * self.config.chunk_length_s
        loudness = self.dsp.compute_loudness(self.master_chunks)  # should be below 0
        log.info(f'master loop has been recorded', 
            loop_duration=f'{round(loop_duration_s, 2)}s',
            loudness=f'{round(loudness, 2)}dB',
            chunks=self.loop_chunks_num,
        )
        if loudness > 0:
            log.warn('master loop is too loud', loudness=f'{round(loudness, 2)}dB')

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
        with self._lock:
            self.tracks.append(track)
            if self.phase == LoopPhase.LOOP:
                track.set_empty(self.loop_chunks_num)
        log.info('new track added', tracks_num=self.config.tracks_num)

    def toggle_input_mute(self):
        self.input_muted = not self.input_muted
        if self.input_muted:
            log.info('input muted')
        else:
            log.info('input unmuted')

    def toggle_output_mute(self):
        self.output_muted = not self.output_muted
        if self.output_muted:
            log.info('output muted')
        else:
            log.info('output unmuted')

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
