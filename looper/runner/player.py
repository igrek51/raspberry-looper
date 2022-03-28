from signal import pause
from dataclasses import dataclass
import math
import time
from typing import List

from nuclear.sublog import log
import pyaudio
import numpy as np

from looper.runner.config import Config
from looper.runner.pinout import Pinout


@dataclass
class Player:
    pinout: Pinout
    config: Config

    recording: bool = False
    playing: bool = False
    master_loop_recorded: bool = False
    master_loop_chunks: List[np.array] = None
    current_buffer_idx: int = 0

    def init(self) -> None:
        self.pinout.loopback_blue_led.pulse(fade_in_time=0.5, fade_out_time=0.5)

        config = self.config

        silence = np.zeros(config.chunk_size, dtype=np.int16)

        log.debug("Initializing PyAudio...")
        pa = pyaudio.PyAudio()

        def stream_callback(in_data, frame_count, time_info, status_flags):
            """
            :param in_data: recorded data if input=True; else None
            :param frame_count: number of frames
            :param time_info: dictionary
            :param status_flags: PaCallbackFlags
            """
            # Recording
            input_chunk = np.frombuffer(in_data, dtype=np.int16)
            out_chunk = None

            if self.recording:
                if not self.master_loop_recorded:
                    if self.master_loop_chunks is None:
                        self.master_loop_chunks = []
                    self.master_loop_chunks.append(input_chunk)
                else:
                    # overdub
                    out_chunk = self.master_loop_chunks[self.current_buffer_idx] + input_chunk
                    self.master_loop_chunks[self.current_buffer_idx] = out_chunk

            # Playing input with recorded loops
            if self.playing and self.master_loop_recorded:
                if out_chunk is None:
                    out_chunk = self.master_loop_chunks[self.current_buffer_idx] + input_chunk
                self.current_buffer_idx += 1
                if self.current_buffer_idx >= len(self.master_loop_chunks):
                    self.current_buffer_idx = 0
                return out_chunk, pyaudio.paContinue

            else:
                # just listening to input
                return input_chunk, pyaudio.paContinue

        loop_stream = pa.open(
            format=config.format,
            channels=config.channels,
            rate=config.sampling_rate,
            input=True,
            output=True,
            input_device_index=config.in_device,
            output_device_index=config.out_device,
            frames_per_buffer=config.chunk_size,
            start=True,
            stream_callback=stream_callback,
        )

        self.pinout.on_button_click_and_hold(
            self.pinout.record_button, 
            on_click=self.toggle_recording, 
            on_hold=self.reset_loop)

        log.info('Ready to work')

        try:
            while loop_stream.is_active():
                time.sleep(1)

        except KeyboardInterrupt:
            log.debug('closing...')
            loop_stream.stop_stream()
            loop_stream.close()
            pa.terminate()
            log.info('Stream closed')


    def toggle_recording(self):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.recording = True
        if not self.master_loop_recorded:
            self.current_buffer_idx = 0
            log.debug('recording master loop...')
        else:
            log.debug('overdubbing...')
        self.pinout.record_red_led.on()

    def stop_recording(self):
        self.current_buffer_idx = 0
        self.recording = False
        self.playing = True
        if not self.master_loop_recorded:
            self.master_loop_recorded = True
            log.info(f'recorded master loop', chunks=len(self.master_loop_chunks))
        else:   
            log.info(f'overdub stopped', chunks=len(self.master_loop_chunks))
        self.pinout.record_red_led.off()
        self.pinout.play_green_led.on()

    def reset_loop(self):
        self.current_buffer_idx = 0
        self.recording = False
        self.playing = False
        self.master_loop_recorded = False
        self.master_loop_chunks = []
        self.pinout.play_green_led.off()
        self.pinout.record_red_led.off()
        log.debug('loop reset')
