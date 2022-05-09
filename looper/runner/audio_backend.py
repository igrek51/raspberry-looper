from abc import ABC, abstractmethod
from typing import Callable

import pyaudio
from nuclear.sublog import log
from nuclear import CommandError
import numpy as np
import jack
import backoff

from looper.runner.config import AudioBackendType, Config
from looper.check.devices import find_device_index
from looper.runner.cmd import BackgroundCommand


class AudioBackend(ABC):
    @classmethod
    def make(cls, backend_type: AudioBackendType) -> 'AudioBackend':
        if backend_type == AudioBackendType.PYAUDIO:
            return PyAudioBackend()
        if backend_type == AudioBackendType.JACK:
            return JackBackend()
        raise ValueError(f"Unknown audio backend: {backend_type}")
        
    @abstractmethod
    def open(self, config: Config, stream_callback: Callable[[np.ndarray], np.ndarray]):
        raise NotImplemented()

    @abstractmethod
    def close(self):
        raise NotImplemented()


class PyAudioBackend(AudioBackend):
    def open(self, config: Config, stream_callback: Callable[[np.ndarray], np.ndarray]):
        log.debug('Initializing PyAudio...')
        self._pa = pyaudio.PyAudio()
        in_device, out_device = find_device_index(config, self._pa)

        def pyaudio_stream_callback(in_data, frame_count, time_info, status_flags):
            input_chunk = np.frombuffer(in_data, dtype=np.int16)
            out_chunk = stream_callback(input_chunk)
            return out_chunk, pyaudio.paContinue

        self._loop_stream = self._pa.open(
            format=config.format,
            channels=config.channels,
            rate=config.sampling_rate,
            input=True,
            output=True,
            input_device_index=in_device,
            output_device_index=out_device,
            frames_per_buffer=config.chunk_size,
            start=False,
            stream_callback=pyaudio_stream_callback,
        )
        self._loop_stream.start_stream()
        log.debug('PyAudio stream started')

    def close(self):
        self._loop_stream.stop_stream()
        self._loop_stream.close()
        self._pa.terminate()
        log.info('Audio Stream closed')


class JackBackend(AudioBackend):
    def open(self, config: Config, stream_callback: Callable[[np.ndarray], np.ndarray]):
        log.debug('Starting JACK server...')
        if config.online:
            cmdline = '/usr/bin/jackd -ndefault --realtime -d alsa --device hw:1 --period 1024 --rate 44100'
        else:
            cmdline = '/usr/bin/jackd -ndefault --realtime -d alsa --device hw:0 --period 1024 --rate 44100'

        def on_jackd_error(e: CommandError):
            log.error(f'JACK server failed to start')

        self.jackd_cmd = BackgroundCommand(cmdline, print_stdout=True, on_error=on_jackd_error)

        client = self.open_client()
        self.jack_client = client
        log.info('JACK server started')

        looper_input = client.inports.register('input_2')
        looper_output = client.outports.register('output_2')

        system_inputs = client.get_ports(is_audio=True, is_output=True, is_physical=True)
        assert system_inputs, 'No jack inputs found to record from'
        system_input = system_inputs[-1]

        system_outputs = client.get_ports(is_audio=True, is_input=True, is_physical=True)
        assert system_outputs, 'No jack outputs found to play to'
        if len(system_outputs) > 1:
            system_playback_ports = [system_outputs[-2], system_outputs[-1]]
        else:
            system_playback_ports = [system_outputs[-1]]
        playback_names = ', '.join([port.name for port in system_playback_ports])
        log.info('Wiring JACK ports', capture=system_input.name, playback_ports=playback_names)

        @client.set_process_callback
        def process(blocksize: int):
            input_chunk: np.ndarray = looper_input.get_array()
            input_chunk = (input_chunk * config.max_amplitude).astype(np.int16)
            out_chunk = stream_callback(input_chunk)
            out_chunk = (out_chunk / config.max_amplitude).astype(np.float32)
            looper_output.get_array()[:] = out_chunk

        @client.set_shutdown_callback
        def shutdown(status, reason):
            log.info('JACK shutdown', status=status, reason=reason)

        client.activate()
        client.connect(system_input, looper_input)
        for playback_port in system_playback_ports:
            client.connect(looper_output, playback_port)

        log.debug('JACK stream started')

    def close(self):
        self.jack_client.outports.clear()
        self.jack_client.inports.clear()
        self.jack_client.deactivate(ignore_errors=True)
        self.jack_client.close(ignore_errors=True)
        log.info('Audio JACK Stream closed')
        self.jackd_cmd.interrupt()
        log.debug('JACK server closed')

    @backoff.on_exception(backoff.fibo, jack.JackOpenError, max_value=3, max_time=5, jitter=None)
    def open_client(self) -> jack.Client:
        log.debug('Connecting to JACK server...')
        return jack.Client('raspberry_looper', no_start_server=True)
