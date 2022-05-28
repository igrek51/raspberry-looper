from enum import Enum
from typing import List, Optional

from pydantic import BaseSettings


class AudioBackendType(Enum):
    PYAUDIO = 'pyaudio'  # pyAudio backend, not distrupting other apps
    JACK = 'jack'  # JACKd server for real-time, low-latency audio streaming, but disabling other apps


class Config(BaseSettings):
    # Backend for streaming audio (on all devices): pyaudio or jack
    audio_backend: Optional[AudioBackendType] = None

    # sampling rate [Hz], eg.: 44100, 48000
    sampling_rate: int = 48000

    # buffer size, number of frames per buffer
    chunk_size: int = 1024

    # Sampling size (bit depth) and sample format
    # - int16 - 16bits, integer
    # - int32 - 32bits, integer
    # - float32 - 32bits, float
    sample_format: str = 'int32'

    # index of input device, -1 find automatically
    in_device: int = -1
    # index of output device, -1 find automatically
    out_device: int = -1

    # name of the audio card device that should be used with JACK
    jack_online_in_device: str = 'hw:1'
    jack_online_out_device: str = 'hw:0'
    jack_offline_in_device: str = 'hw:0'
    jack_offline_out_device: str = 'hw:0'

    jack_capture_ports: Optional[List[str]] = None
    jack_playback_ports: Optional[List[str]] = None

    # mono
    channels: int = 1

    # maximum duration of a track in seconds
    max_loop_duration_s: float = 4 * 60

    # number of available tracks in looper
    tracks_num: int = 4
    # number of tracks with buttons and LEDs connected to the board
    tracks_gpio_num: int = 2

    # Whether to play input to the output
    listen_input: bool = True
    # Amplification of the input signal [dB]
    input_volume: float = 0

    # Offline mode - without Raspberry Pi pins
    offline: bool = False

    # Working directory to be used for storing recordings and sessions
    workdir: str = '/home/pi/looper'

    # HTTP server port for web interface and API
    http_port: int = 8000

    # Output Recorder
    output_recordings_dir: str = "out/recordings"
    leave_wav_recordings: bool = False
    # max gain in dB to normalize recorded output
    recorder_max_gain: float = 30

    # Sessions
    output_sessions_dir: str = "out/sessions"

    # Metronome
    metronome_volume: float = -17

    # If enabled, pressing spacebar key activates recording like footswitch does
    spacebar_footswitch: bool = True

    # If enabled, baseline bias will be automatically normalized
    auto_anti_bias: bool = True


    @property
    def chunk_length_s(self) -> float:
        return self.chunk_size / self.sampling_rate

    @property
    def max_loop_chunks(self) -> int:
        return self.max_loop_duration_s // self.chunk_length_s

    @property
    def online(self) -> bool:
        return not self.offline

    @property
    def active_audio_backend_type(self) -> AudioBackendType:
        if self.audio_backend is not None:
            return self.audio_backend
        return AudioBackendType.PYAUDIO
