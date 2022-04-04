from dataclasses import dataclass
import datetime
import os
from typing import Callable, Optional
from pathlib import Path
import threading

import wave
import numpy as np
from pydub import AudioSegment

from looper.runner.config import Config
from nuclear.sublog import log

lock = threading.Lock()


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


@dataclass
class LoopSaver:
    config: Config
    saving: bool = False
    chunks_written: int = 0

    def start_saving(self):
        if self.saving:
            log.warn('Already saving')
            return

        self.filestem = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.wav_path = Path(self.config.records_dir) / f'{self.filestem}.wav'

        log.debug('creating WAV file', path=self.wav_path)
        Path(self.wav_path).parent.mkdir(exist_ok=True, parents=True)

        with lock:
            self.wav = wave.open(str(self.wav_path), 'w')
            self.wav.setnchannels(self.config.channels)
            self.wav.setsampwidth(self.config.format_bytes)
            self.wav.setframerate(self.config.sampling_rate)

        self.chunks_written = 0
        self.saving = True
        log.info('Started saving output to a file')

    def stop_saving(self):
        if not self.saving:
            log.warn('Already not saving')
            return

        self.saving = False

        with lock:
            self.wav.close()
            duration = self.chunks_written * self.config.chunk_length_s
            filesize_mb = os.path.getsize(self.wav_path) / 1024 / 1024
            log.debug('WAV file saved', 
                filename=self.wav_path, 
                chunks_saved=self.chunks_written,
                duration=f'{duration:.2f}s',
                size=f'{filesize_mb:.2f}MB')

            mp3_path = Path(self.config.records_dir) / f'{self.filestem}.mp3'

            audio = AudioSegment.from_wav(str(self.wav_path))
            audio.export(str(mp3_path), format='mp3')

            self.wav_path.unlink()

        filesize_mb = os.path.getsize(mp3_path) / 1024 / 1024
        log.info('output converted to MP3', filename=mp3_path, 
            duration=f'{audio.duration_seconds:.2f}s', size=f'{filesize_mb:.2f}MB')

    def toggle_saving(self):
        if self.saving:
            self.stop_saving()
        else:
            self.start_saving()

    def transmit(self, chunk: np.array):
        if not self.saving:
            return
        
        with lock:
            self.wav.writeframes(b''.join(chunk))
            self.chunks_written += 1
