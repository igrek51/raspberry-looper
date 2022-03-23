import time

import pyaudio
from nuclear.sublog import log


RATE = 44100  # sampling rate
CHUNK = 1024  # buffer size, number of frames per buffer
FORMAT = pyaudio.paInt16  # Sampling size and format, bit depth (16-bit)
INDEVICE = 1  # index of input device
OUTDEVICE = 1  # index of output device


def wire_input_output():
    log.info("Wiring input with output...")

    pa = pyaudio.PyAudio()

    def loop_callback(in_data, frame_count, time_info, status_flags):
        """
        :param in_data: recorded data if input=True; else None
        :param frame_count: number of frames
        :param time_info: dictionary
        :param status_flags: PaCallbackFlags
        """
        return (in_data, pyaudio.paContinue)

    loop_stream = pa.open(
        format=FORMAT,
        channels=1,  # mono
        rate=RATE,
        input=True,
        output=True,
        input_device_index=INDEVICE,
        output_device_index=OUTDEVICE,
        frames_per_buffer=CHUNK,
        start=True,  # Start the stream running immediately
        stream_callback=loop_callback,
    )

    try:
        while loop_stream.is_active():
            log.debug("Loop stream active...")
            time.sleep(1)

    except KeyboardInterrupt:
        loop_stream.stop_stream()
        loop_stream.close()

        pa.terminate()
        log.info("Stream closed")
