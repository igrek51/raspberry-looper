import re
import time
from pathlib import Path
import math
from typing import List

import pyaudio
from nuclear.sublog import log
import numpy as np
from looper.runner.audio_backend import AudioBackend, PyAudioBackend

from looper.runner.config import Config
from looper.runner.dsp import SignalProcessor
from looper.runner.sample import sample_format_numpy_type, sample_format_max_amplitude


def measure_input_latency():
    log.info("Measuring output-input latency...")
    log.info("Put microphone close to a speaker or wire the output with the input.")
    log.debug("Initializing PyAudio...")
    pa = pyaudio.PyAudio()

    config = Config()
    chunk = config.chunk_size
    dsp = SignalProcessor(config)

    silence = dsp.silence()
    amplitude = sample_format_max_amplitude(config.sample_format)

    log.info(f"one buffer length: {config.chunk_length_s * 1000}ms")

    sine = dsp.sine(frequency=440, amplitude=amplitude)

    max_recordings = 10
    np_type = sample_format_numpy_type(config.sample_format)
    recordings = np.zeros([max_recordings, chunk], dtype=np_type)
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

        recordings[current_buffer_idx, :] = np.frombuffer(in_data, dtype=np_type)
        current_buffer_idx += 1
        return silence, pyaudio.paContinue

    loop_stream = pa.open(
        format=PyAudioBackend.pyaudio_sample_format(config.sample_format),
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


def measure_cycle_latency():
    log.info("Measuring full cycle latency...")
    log.info("Put microphone close to a speaker or wire the output with the input.")

    config = Config()
    dsp = SignalProcessor(config)
    audio_backend = AudioBackend.make(config.active_audio_backend_type)

    log.info(f"one buffer length", chunk_length=f'{config.chunk_length_s * 1000}ms')

    max_amplitude = sample_format_max_amplitude(config.sample_format)
    short_sine = _short_sine(dsp, config)
    silence = dsp.silence()
    arming_chunks_num = 20
    recorded_chunks: List[np.array] = []
    chunk_size = config.chunk_size

    def stream_audio_chunk(input_chunk: np.ndarray) -> np.ndarray:
        recorded_chunks.append(input_chunk)
        if len(recorded_chunks) <= 10:
            return silence
        if len(recorded_chunks) == arming_chunks_num:
            return short_sine
        return input_chunk

    audio_backend.open(config, stream_audio_chunk)

    while len(recorded_chunks) < 40:
        log.debug("Recording chunks...")
        time.sleep(0.1)

    audio_backend.close()
    log.info("Recording stopped", chunks=len(recorded_chunks))

    joined = np.concatenate(recorded_chunks)
    record_file = Path('out/latency.rec')
    record_file.parent.mkdir(exist_ok=True)
    np.save(str(record_file), joined)
    log.debug("recordings saved", record_file=record_file)

    armed_chunks = joined[arming_chunks_num * chunk_size:]
    peaks_mask = np.absolute(armed_chunks) > 0.1
    max_recorded_amplitude = np.max(np.absolute(armed_chunks))
    assert any(peaks_mask), f'no peak detected in recorded audio, max recorded amplitude: {max_recorded_amplitude}'

    peak_indices = []
    view = peaks_mask
    offset = 0
    while True:
        first_peak = np.argmax(view)
        if view[first_peak] == False:
            break
        peak_indices.append(first_peak + offset)
        offset += first_peak+chunk_size
        view = view[first_peak+chunk_size:]
        if view.size == 0:
            break
    assert len(peak_indices) == 2, 'at least two peaks are expected'

    peak_indices_diff = []
    for i in range(len(peak_indices) - 1):
        peak_indices_diff.append(peak_indices[i+1] - peak_indices[i])
    peak_indices_diff

    latency_median = np.median(peak_indices_diff)
    latency_ms = latency_median * 1000 / config.sampling_rate

    log.info('latency measured', 
        latency_samples=latency_median,
        latency_ms=f'{latency_ms} ms')


def _short_sine(dsp: SignalProcessor, config: Config):
    max_amplitude = sample_format_max_amplitude(config.sample_format)
    sine = dsp.sine(frequency=440, amplitude=max_amplitude)
    for i in range(config.chunk_size):
        if i > config.chunk_size // 2:
            sine[i] = 0
    return sine
