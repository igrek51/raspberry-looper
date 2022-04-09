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
    # size (in bytes) for the sample format, see pa.get_sample_size(config.format)
    format_bytes: int = 2
    # full-scale amplitude (2**16/2-1)
    max_amplitude: int = 32767

    # index of input device
    in_device: int = 1

    # index of output device
    out_device: int = 1

    # mono
    channels: int = 1

    # latency between recording sound and playing it again in a loopback in milliseconds
    # see https://music.stackexchange.com/a/30325 for optimal values
    latency_ms: float = 46.44

    max_loop_duration_s: float = 4 * 60

    # number of available tracks in looper
    tracks_num: int = 4
    # number of tracks with buttons and LEDs connected to the board
    tracks_gpio_num: int = 2

    # Offline mode - without Raspberry Pi pins nor audio devices
    offline: bool = False

    workdir: str = '/home/pi/looper'

    http_port: int = 8000

    # Output Recorder
    output_recordings_dir: str = "out/recordings"
    leave_wav_recordings: bool = True
    # max gain in dB to normalize recorded output
    recorder_max_gain: float = 30


    @property
    def chunk_length_ms(self) -> float:
        return 1000 * self.chunk_size / self.sampling_rate

    @property
    def chunk_length_s(self) -> float:
        return self.chunk_size / self.sampling_rate

    @property
    def max_loop_chunks(self) -> int:
        return self.max_loop_duration_s // self.chunk_length_s

    @property
    def online(self) -> bool:
        return not self.offline
