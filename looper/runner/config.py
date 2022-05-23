from dataclasses import dataclass
from enum import Enum
from typing import Optional
import os
from pathlib import Path

import yaml
import dacite
from nuclear.sublog import log


class AudioBackendType(Enum):
    PYAUDIO = 'pyaudio'  # pyAudio backend, not distrupting other apps
    JACK = 'jack'  # JACKd server for real-time, low-latency audio streaming, but disabling other apps


@dataclass
class Config:
    # Superior backend for streaming audio chunks (on all devices): pyaudio or jack
    audio_backend: Optional[AudioBackendType] = None
    # Backend for streaming audio chunks on Raspberry Pi
    online_audio_backend: AudioBackendType = AudioBackendType.JACK
    # Backend for streaming audio chunks on regular PC
    offline_audio_backend: AudioBackendType = AudioBackendType.PYAUDIO

    # sampling rate [Hz], eg.: 44100, 48000
    sampling_rate: int = 44100

    # buffer size, number of frames per buffer
    chunk_size: int = 1024

    # Sampling size (bit depth) and sample format
    # - int16 - 16bits, integer
    # - int32 - 32bits, integer
    # - float32 - 32bits, float
    sample_format: str = 'int16'

    # index of input device, -1 find automatically
    in_device: int = -1
    # index of output device, -1 find automatically
    out_device: int = -1

    # name of the audio card device that should be used with JACK
    online_jack_device: str = 'hw:1'
    offline_jack_device: str = 'hw:0'

    # mono
    channels: int = 1

    # latency between recording sound and playing it again in a loopback in milliseconds
    # see https://music.stackexchange.com/a/30325 for optimal values
    latency_ms: float = 46.44

    # maximum duration of a track in seconds
    max_loop_duration_s: float = 4 * 60

    # number of available tracks in looper
    tracks_num: int = 4
    # number of tracks with buttons and LEDs connected to the board
    tracks_gpio_num: int = 2

    # Offline mode - without Raspberry Pi pins nor audio devices
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

    @property
    def audio_backend_type(self) -> AudioBackendType:
        if self.audio_backend is not None:
            return self.audio_backend
        return self.offline_audio_backend if self.offline else self.online_audio_backend


def load_config(config_file_path: Optional[str] = None) -> Config:
    if not config_file_path:
        config_file_path = os.environ.get('CONFIG_FILE')
    if not config_file_path:
        path = Path('default.config.yaml')
        if path.is_file():
            log.info(f'found "{path}" file at default config path')
            return load_config_from_file(path)

        log.info('CONFIG_FILE env is unspecified, loading default config')
        return Config()

    path = Path(config_file_path)
    return load_config_from_file(path)


def load_config_from_file(path: Path) -> Config:
    if not path.is_file():
        raise FileNotFoundError(f"config file {path} doesn't exist")

    try:
        with path.open() as file:
            config_dict = yaml.load(file, Loader=yaml.FullLoader)
            if not config_dict:
                log.info('config file is empty, loading default config')
                return Config()
                
            config = dacite.from_dict(
                data_class=Config,
                data=config_dict,
                config=dacite.Config(cast=[AudioBackendType]),
            )
            log.info(f'config loaded from {path}: {config_dict}')
            return config
    except Exception as e:
        raise RuntimeError('loading config failed') from e
