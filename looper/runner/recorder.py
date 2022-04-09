from dataclasses import dataclass
import datetime
from enum import Enum
import os
from typing import Callable, List, Optional
from pathlib import Path
from threading import Lock

import wave
import numpy as np
from pydub import AudioSegment
from nuclear.sublog import log

from looper.runner.config import Config


@dataclass
class Recording:
    name: str
    path: Path
    link: str
    filesize_mb: float


class RecorderPhase(Enum):
    IDLE = 1  # not started yet
    RECORDING = 2  # recording output
    BUSY = 3  # saving output files, converting 


@dataclass
class OutputRecorder:
    config: Config
    saving: bool = False
    phase: RecorderPhase = RecorderPhase.IDLE
    chunks_written: int = 0
    wav = None
    _lock: Lock = Lock()

    def start_saving(self):
        if self.phase != RecorderPhase.IDLE:
            log.warn('Recorder is not IDLE')
            return
        self.phase = RecorderPhase.BUSY

        self.filestem = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.wav_path = Path(self.config.output_recordings_dir) / f'{self.filestem}.wav'

        log.debug('creating WAV file', path=self.wav_path)
        Path(self.config.output_recordings_dir).mkdir(exist_ok=True, parents=True)

        with self._lock:
            self.wav = wave.open(str(self.wav_path), 'w')
            self.wav.setnchannels(self.config.channels)
            self.wav.setsampwidth(self.config.format_bytes)
            self.wav.setframerate(self.config.sampling_rate)

        self.chunks_written = 0
        self.phase = RecorderPhase.RECORDING
        log.info('Started saving output to a file')

    def stop_saving(self):
        if self.phase != RecorderPhase.RECORDING:
            log.warn('Recorder is not RECORDING')
            return
        self.phase = RecorderPhase.BUSY

        with self._lock:
            self.wav.close()
            self.wav = None
            duration = self.chunks_written * self.config.chunk_length_s
            wav_filesize_mb = os.path.getsize(self.wav_path) / 1024 / 1024
            log.debug('WAV file saved', 
                filename=self.wav_path, 
                chunks_saved=self.chunks_written,
                duration=f'{duration:.2f}s',
                size=f'{wav_filesize_mb:.2f}MB')

            mp3_path = Path(self.config.output_recordings_dir) / f'{self.filestem}.mp3'

            audio = AudioSegment.from_wav(str(self.wav_path))
            audio = normalize_recording(audio, self.config)
            audio.export(str(mp3_path), format='mp3')

            if self.config.leave_wav_recordings:
                log.warn('leaving raw WAV file', file=self.wav_path, size=f'{wav_filesize_mb:.2f}MB')
            else:
                self.wav_path.unlink()

        self.phase = RecorderPhase.IDLE
        mp3_filesize_mb = os.path.getsize(mp3_path) / 1024 / 1024
        log.info('output converted to MP3', 
            filename=mp3_path, duration=f'{audio.duration_seconds:.2f}s', 
            wav_size=f'{wav_filesize_mb:.2f}MB', mp3_size=f'{mp3_filesize_mb:.2f}MB')

    def toggle_saving(self):
        if self.phase == RecorderPhase.RECORDING:
            self.stop_saving()
        else:
            self.start_saving()

    def transmit(self, chunk: np.array):
        if self.phase == RecorderPhase.RECORDING:
            with self._lock:
                if self.wav is not None:
                    self.wav.writeframes(b''.join(chunk))
                    self.chunks_written += 1

    @property
    def recorded_duration(self) -> float:
        if self.phase != RecorderPhase.RECORDING:
            return 0
        return self.chunks_written * self.config.chunk_length_s

    def list_recordings(self) -> List[Recording]:
        recordings = []
        dirpath = Path(self.config.output_recordings_dir)
        dirpath.mkdir(exist_ok=True, parents=True)
        for path in dirpath.glob('*'):
            filesize_mb = os.path.getsize(path) / 1024 / 1024
            recordings.append(Recording(path.name, path, str(path), filesize_mb))
        return sorted(recordings, key=lambda r: r.name)


def normalize_recording(audio: AudioSegment, config: Config) -> AudioSegment:
    if config.recorder_max_gain <= 0:
        return audio
    volume = audio.max_dBFS
    gain = -volume
    if gain > config.recorder_max_gain:
        gain = config.recorder_max_gain
    audio = audio.apply_gain(gain)
    log.info('Volume normalized', volume=f'{volume:.2f}dB', gain=f'{gain:.2f}dB')
    return audio


def save_wav(filename: str, frames_channel: Callable[[], Optional[np.array]], config: Config):
    log.debug('Saving frames to WAV file', filename=filename)

    Path(filename).parent.mkdir(exist_ok=True, parents=True)

    wav = wave.open(filename, 'w')
    wav.setnchannels(config.channels)
    wav.setsampwidth(config.format_bytes)
    wav.setframerate(config.sampling_rate)

    frames_written = 0
    while True:
        frame = frames_channel()
        if frame is None:
            break
        wav.writeframes(b''.join(frame))
        frames_written += 1

    wav.close()
    duration = frames_written * config.chunk_length_s
    filesize_mb = os.path.getsize(filename) / 1024 / 1024
    log.debug('WAV file saved', filename=filename, chunks_saved=frames_written,
        duration=f'{duration:.2f}s', size=f'{filesize_mb:.2f}MB')


def save_mp3(filename: str, frames_channel: Callable, config: Config):
    tmp_wav_file = Path(filename).with_suffix('.wav')
    save_wav(str(tmp_wav_file), frames_channel, config)

    track = AudioSegment.from_wav(tmp_wav_file)
    track.export(filename, format='mp3')

    tmp_wav_file.unlink()

    filesize_mb = os.path.getsize(filename) / 1024 / 1024
    log.info('MP3 file saved', filename=filename, 
        duration=f'{track.duration_seconds:.2f}s', size=f'{filesize_mb:.2f}MB')
