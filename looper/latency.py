import time
from pathlib import Path

import pyaudio
from nuclear.sublog import log
import numpy as np

from looper.runner.config import Config


def measure_latency():
    log.info("Measuring latency...")
    pa = pyaudio.PyAudio()
    config = Config()
    chunk = config.chunk_size

    silence = np.zeros(chunk, dtype=np.int16)

    log.info(f"one buffer length: {config.buffer_length_ms}ms")

    sine_frequency = 440
    sine_sample_frequency = sine_frequency / config.sampling_rate
    sine = np.empty(chunk, dtype=np.int16)
    for i in range(chunk):
        sine[i] = np.sin(2 * np.pi * sine_sample_frequency * i) * 32767

    max_recordings = 10
    recordings = np.zeros([max_recordings, chunk], dtype=np.int16)
    started = False
    current_buffer_idx: int = -1

    def stream_callback(in_data, frame_count, time_info, status_flags):
        nonlocal started, current_buffer_idx, recordings
        if not started:
            return silence, pyaudio.paContinue

        if current_buffer_idx == -1:  # play tone
            current_buffer_idx += 1
            return sine, pyaudio.paContinue

        if current_buffer_idx >= max_recordings:
            return silence, pyaudio.paComplete

        recordings[current_buffer_idx, :] = np.frombuffer(in_data, dtype=np.int16)
        current_buffer_idx += 1
        return silence, pyaudio.paContinue

    loop_stream = pa.open(
        format=config.format,
        channels=config.channels,
        rate=config.sampling_rate,
        input=True,
        output=True,
        input_device_index=config.in_device,
        output_device_index=config.out_device,
        frames_per_buffer=config.chunk_size,
        start=False,
        stream_callback=stream_callback,
    )
    loop_stream.start_stream()

    started = True
    log.debug("stream started")
    while loop_stream.is_active():
        time.sleep(0.1)
    log.debug("recording stopped")

    record_file = Path('out/latency.rec')
    record_file.parent.mkdir(exist_ok=True)
    np.save(str(record_file), recordings)
    log.debug(f"recordings saved to {record_file}")
