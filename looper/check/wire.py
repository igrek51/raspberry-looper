import time

import pyaudio
from nuclear.sublog import log
from looper.runner.audio_backend import PyAudioBackend

from looper.runner.config import Config


def wire_input_output():
    log.info("Wiring input with output...")

    config = Config()

    pa = pyaudio.PyAudio()

    buffers_processed = 0
    log.info(f'one buffer length: {config.chunk_length_ms}ms')

    def loop_callback(in_data, frame_count, time_info, status_flags):
        """
        :param in_data: recorded data if input=True; else None
        :param frame_count: number of frames
        :param time_info: dictionary
        :param status_flags: PaCallbackFlags
        """
        nonlocal buffers_processed
        buffers_processed += 1
        return (in_data, pyaudio.paContinue)

    loop_stream = pa.open(
        format=PyAudioBackend.pyaudio_sample_format(config.sample_format),
        channels=config.channels,
        rate=config.sampling_rate,
        input=True,
        output=True,
        input_device_index=config.in_device,
        output_device_index=config.out_device,
        frames_per_buffer=config.chunk_size,
        start=True,  # Start the stream running immediately
        stream_callback=loop_callback,
    )

    try:
        start_time = time.time()
        start_buffers_processed = 0
        while loop_stream.is_active():
            delta_time = time.time() - start_time
            delta_buffers = buffers_processed - start_buffers_processed
            if delta_buffers > 0:
                delta_buffer_length_ms = delta_time / delta_buffers * 1000
                log.debug(f"delta_buffer_length_ms: {delta_buffer_length_ms}")
            log.debug(f"Loop stream active, all buffers processed: {buffers_processed}")

            start_time = time.time()
            start_buffers_processed = buffers_processed
            time.sleep(1)

    except KeyboardInterrupt:
        loop_stream.stop_stream()
        loop_stream.close()

        pa.terminate()
        log.info("Stream closed")
