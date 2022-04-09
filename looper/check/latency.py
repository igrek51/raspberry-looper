import time
from pathlib import Path
import math

import pyaudio
from nuclear.sublog import log
import numpy as np

from looper.runner.config import Config
from looper.runner.dsp import SignalProcessor


def measure_latency():
    log.info("Measuring output-input latency...")
    log.info("Put microphone close to a speaker or wire the output with the input.")
    log.debug("Initializing PyAudio...")
    pa = pyaudio.PyAudio()

    config = Config()
    chunk = config.chunk_size
    dsp = SignalProcessor(config)

    silence = dsp.silence()
    amplitude = 32767

    log.info(f"one buffer length: {config.chunk_length_ms}ms")

    sine = dsp.sine(frequency=440, amplitude=amplitude)

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
    log.debug("recordings saved", record_file=record_file)

    joined = np.concatenate(recordings)
    threshold_amp = amplitude / 2
    start_sample = np.argmax(joined>threshold_amp)
    
    if start_sample == 0:
        raise RuntimeError('cannot find a tone in a recorded audio')

    max_amplitude = max(np.max(joined), -np.min(joined))

    latency_chunks = math.ceil(start_sample / config.chunk_size)

    chunk_length_ms = 1000 * config.chunk_size / config.sampling_rate

    log.debug("tone recognized", 
        start_sample=start_sample, 
        max_amplitude=max_amplitude, 
        latency_chunks=latency_chunks, 
        chunk_length_ms=chunk_length_ms)

    sample_time_s = 1 / config.sampling_rate
    latency_ms = start_sample * sample_time_s * 1000

    # latency based on minimum number of recorded chunks
    latency_max_ms = latency_chunks * config.chunk_size * sample_time_s * 1000

    log.info('latency calculated', 
        min_latency_ms=latency_ms, 
        max_latency_max_ms=latency_max_ms)
    log.info(f'suggested latency: {latency_max_ms}ms')
