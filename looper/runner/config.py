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


    @property
    def buffer_length_ms(self) -> float:
        return 1000 * self.chunk_size / self.sampling_rate
