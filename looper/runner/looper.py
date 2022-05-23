import asyncio
from dataclasses import dataclass, field
from typing import List
from enum import Enum
from threading import Lock

from nuclear.sublog import log
import numpy as np
from looper.runner.audio_backend import AudioBackend

from looper.runner.config import Config
from looper.runner.dsp import SignalProcessor
from looper.runner.metronome import Metronome
from looper.runner.pinout import Pinout
from looper.runner.recorder import OutputRecorder
from looper.runner.sample import sample_format_bytes, sample_format_max_amplitude
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
    _baseline_bias: float = 0  # samples value that input baseline will be moved
    main_track: int = 0  # index of a track controllable by foot switch
    master_chunks: List[np.array] = field(default_factory=list)
    tracks_num: int = 0
    tracks: List[Track] = field(default_factory=list)

    audio_backend: AudioBackend = None
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
    def loop_tempo(self) -> float:
        if not self.master_chunks:
            return 0
        tempo = 60 / self.loop_duration  # BPM
        while tempo < 60:
            tempo *= 2
        return tempo

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
            self.tracks_num = self.config.tracks_num
            self.main_track = 0
            for track_id in range(self.tracks_num):
                has_gpio = track_id < self.config.tracks_gpio_num
                track = Track(track_id, self.config, has_gpio)
                self.tracks.append(track)

    def run(self) -> None:
        self.recorder = OutputRecorder(self.config)
        self.dsp = SignalProcessor(self.config)
        self.reset()
        self.audio_backend = AudioBackend.make(self.config.audio_backend_type)
        self.audio_backend.open(self.config, self.stream_audio_chunk)

        if self.config.online:
            self.pinout.loopback_led.pulse(fade_in_time=0.5, fade_out_time=0.5)
            self.update_leds()
            self.bind_buttons()

    def stream_audio_chunk(self, input_chunk: np.ndarray) -> np.ndarray:
        """Read recorded input and generate playback audio chunk"""
        if self.input_muted:
            input_chunk = self.dsp.silence()
        else:
            input_chunk = input_chunk + self._baseline_bias
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
        return out_chunk
    
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
        self.pinout.on_button_click(
            self.pinout.foot_switch,
            on_click=self.on_footswitch_press,
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
            self.main_track = track_id
            if self.tracks[track_id].recording:
                self.stop_recording(track_id)
            else:
                self.start_recording(track_id)
        
        self.update_leds()

    def start_recording_master(self):
        with self._lock:
            self.master_chunks = []
            self.main_track = 0
            self.phase = LoopPhase.RECORDING_MASTER
        log.debug('recording master loop...')

    def stop_recording_master(self):
        with self._lock:
            if self.config.auto_anti_bias:
                chunks_bias = self.dsp.calculate_baesline_bias(self.master_chunks)
                chunks_bias_fraction = chunks_bias / sample_format_max_amplitude(self.config.sample_format)
                self.dsp.move_by_offset(self.master_chunks, -chunks_bias)
                self._baseline_bias -= chunks_bias
                log.info(f'input baseline bias has been automatically compensated', 
                    bias=f'{round(chunks_bias, 6)}',
                    full_scale_fraction=f'{round(chunks_bias_fraction, 6)}',
                )

            self.current_position = 0
            for track in self.tracks:
                if track.index == 0:
                    track.set_track(self.master_chunks, fade=True)
                    track.playing = True
                else:
                    track.set_empty(self.loop_chunks_num)
            self.phase = LoopPhase.LOOP

        loudness = self.dsp.compute_loudness(self.master_chunks)  # should be below 0
        samples_num = self.loop_chunks_num * self.config.chunk_size
        track_kb = samples_num * sample_format_bytes(self.config.sample_format) / 1024
        log.info(f'master loop has been recorded', 
            loop_duration=f'{round(self.loop_duration, 2)}s',
            loop_tempo=f'{round(self.loop_tempo, 2)} BPM',
            loudness=f'{round(loudness, 2)}dB',
            chunks=self.loop_chunks_num,
            samples=samples_num,
            track_memory=f'{track_kb} kiB',
        )
        if loudness > 0:
            log.warn('master loop is too loud', loudness=f'{round(loudness, 2)}dB')

    def start_recording(self, track_id: int):
        if self.phase != LoopPhase.LOOP:
            return
        for track in self.tracks:
            if track.index != track_id:
                track.recording = False
        with self._lock:
            self.tracks[track_id].start_recording(self.current_position)

    def stop_recording(self, track_id: int):
        if self.phase != LoopPhase.LOOP:
            return
        with self._lock:
            self.tracks[track_id].stop_recording()

    def toggle_play(self, track_id: int):
        self.tracks[track_id].toggle_play()
        self.update_leds()

    def reset_track(self, track_id: int):
        self.main_track = track_id
        self.tracks[track_id].clear()
        if self.tracks[track_id].has_gpio and self.config.online:
            self.pinout.record_leds[track_id].blink(on_time=0.1, off_time=0.1, n=2, background=False)
        log.info('track cleared', track=track_id)
        if all(track.empty for track in self.tracks):
            with self._lock:
                self.phase = LoopPhase.VOID
                self.master_chunks = []
                self.current_position = 0
            log.info('all tracks reset, looper void')
        self.update_leds()

    def update_leds(self):
        if self.config.online:
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
                else:
                    if self.is_recording(track.index):
                        self.pinout.last_record_led().on()

            if self.phase != LoopPhase.LOOP:
                self.pinout.progress_led.off()

    def is_recording(self, track_id: int) -> bool:
        return self.tracks[track_id].recording or (self.phase == LoopPhase.RECORDING_MASTER and track_id == 0)

    def add_track(self):
        track_id = self.tracks_num
        self.tracks_num += 1
        has_gpio = track_id < self.config.tracks_gpio_num
        track = Track(track_id, self.config, has_gpio)
        with self._lock:
            self.tracks.append(track)
            if self.phase == LoopPhase.LOOP:
                track.set_empty(self.loop_chunks_num)
        log.info('new track added', tracks_num=self.tracks_num)

    def remove_track(self, track_id: int):
        if self.tracks_num == 1:
            raise RuntimeError('can not remove last track')
        if track_id >= self.tracks_num:
            raise RuntimeError(f'track {track_id} does not exist')

        with self._lock:
            self.tracks_num -= 1
            self.tracks.pop(track_id)
            for track_id in range(self.tracks_num):
                self.tracks[track_id].index = track_id
        log.info('track has been removed', track_id=track_id)

    def set_metronome_tracks(self, bpm: float, beats: int = 4, bars: int = 1):
        if self.phase != LoopPhase.VOID:
            raise RuntimeError('loop has to be empty to add metronome track')

        with self._lock:
            self.master_chunks = Metronome(self.config).generate_beat(bpm, beats, bars)
            self.current_position = 0
            for track in self.tracks:
                if track.index == 0:
                    track.set_track(self.master_chunks, fade=False)
                    track.playing = True
                    track.name = f'Metronome {int(bpm)}BPM'
                else:
                    track.set_empty(self.loop_chunks_num)
            self.phase = LoopPhase.LOOP

        log.info(f'master loop has been set to metronome beats', 
            bpm=bpm,
            beats=beats,
            loop_duration=f'{round(self.loop_duration, 2)}s',
            chunks=self.loop_chunks_num,
            samples=self.loop_chunks_num*self.config.chunk_size,
        )
    
    def on_footswitch_press(self):
        self.toggle_record(self.main_track)

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

    @property
    def baseline_bias(self) -> float:
        """Return fraction of full-scale that input baseline is moved"""
        return self._baseline_bias / sample_format_max_amplitude(self.config.sample_format)

    @baseline_bias.setter
    def baseline_bias(self, bias_fraction: float):
        self._baseline_bias = bias_fraction * sample_format_max_amplitude(self.config.sample_format)
        log.info('baseline bias set', bias_value=self._baseline_bias, bias_fraction=bias_fraction)

    async def update_progress(self):
        if self.phase != LoopPhase.LOOP:
            await asyncio.sleep(0.5)
            return

        chunks_left = self.loop_chunks_num - self.current_position
        chunks_left_s = chunks_left * self.config.chunk_length_s
        self.pinout.progress_led.pulse(fade_in_time=chunks_left_s, fade_out_time=0, n=1)
        await asyncio.sleep(chunks_left_s)
    
    def close(self):
        log.debug('closing looper...')
        if self.config.online:
            self.pinout.init_leds()
        self.audio_backend.close()
