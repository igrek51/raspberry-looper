from typing import List
import numpy as np

from looper.runner.config import Config
from looper.runner.sample import sample_format_max_amplitude


class SignalProcessor:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.downramp = np.linspace(1, 0, config.chunk_size)
        self.upramp = np.linspace(0, 1, config.chunk_size)
        self.max_amp = sample_format_max_amplitude(config.sample_format)

    def fade_in(self, buffer):
        np.multiply(buffer, self.upramp, out=buffer, casting="unsafe")

    def fade_out(self, buffer):
        np.multiply(buffer, self.downramp, out=buffer, casting="unsafe")

    def sine(self, frequency: float = 440, amplitude: int = 32767) -> np.array:
        sine_sample_frequency = frequency / self.config.sampling_rate
        sine = np.empty(self.config.chunk_size, dtype=np.int16)
        for i in range(self.config.chunk_size):
            sine[i] = np.sin(2 * np.pi * sine_sample_frequency * i) * amplitude
        return sine

    def silence(self) -> np.array:
        return np.zeros(self.config.chunk_size, dtype=np.int16)

    def amplify(self, chunk: np.array, volume: float) -> np.array:
        """Amplify by a given volume in root-power decibels"""
        result = chunk * 10 ** (volume / 20)
        return result.astype(np.int16)

    def compute_chunk_loudness(self, chunk: np.array) -> float:
        """Compute loudness in decibels relative to full scale (dBFS)"""
        rms = np.sqrt(np.mean(np.square(chunk / self.max_amp)))
        if rms <= 0:
            return -100
        return 20 * np.log10(rms * np.sqrt(2))

    def compute_loudness(self, chunks: List[np.array]) -> float:
        """Compute loudness in decibels relative to full scale (dBFS)"""
        if not chunks:
            return -100
        means = []
        for chunk in chunks:
            means.append(np.mean(np.square(chunk / self.max_amp)))
        rms = np.sqrt(np.mean(means))
        if rms <= 0:
            return -100
        return 20 * np.log10(rms * np.sqrt(2))
