from dataclasses import dataclass

import pyaudio


@dataclass
class Config:
    # sampling rate [Hz]
    sampling_rate: int = 44100

    # buffer size, number of frames per buffer
    chunk_size: int = 1024

    # Sampling size and format, bit depth (16-bit)
    format = pyaudio.paInt16

    # index of input device
    in_device: int = 1

    # index of output device
    out_device: int = 1

    # mono
    channels: int = 1

    # latency between recording sound and playing it again in a loopback in milliseconds
    # see https://music.stackexchange.com/a/30325 for optimal values
    latency_ms: float = 46.44

    max_loop_duration_s: float = 2 * 60


    @property
    def chunk_length_ms(self) -> float:
        return 1000 * self.chunk_size / self.sampling_rate
