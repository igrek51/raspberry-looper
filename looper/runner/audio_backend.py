from abc import ABC, abstractmethod
from random import sample
from typing import Callable

import pyaudio
from nuclear.sublog import log, log_exception
from nuclear import CommandError
import numpy as np
import jack
import backoff

from looper.runner.cmd import BackgroundCommand
from looper.runner.config import AudioBackendType, Config
from looper.check.devices import find_device_index
from looper.runner.sample import sample_format_max_amplitude, sample_format_numpy_type


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
        log.info('Initializing PyAudio for streaming audio...')
        self._pa = pyaudio.PyAudio()
        in_device, out_device = find_device_index(config, self._pa)
        dst_np_type = sample_format_numpy_type(config.sample_format)

        def pyaudio_stream_callback(in_data, frame_count, time_info, status_flags):
            input_chunk = np.frombuffer(in_data, dtype=dst_np_type)
            out_chunk = stream_callback(input_chunk)
            return out_chunk, pyaudio.paContinue

        self._loop_stream = self._pa.open(
            format=self.pyaudio_sample_format(config.sample_format),
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
        log.info('PyAudio stream started')

    def close(self):
        self._loop_stream.stop_stream()
        self._loop_stream.close()
        self._pa.terminate()
        log.info('Audio Stream closed')

    @staticmethod
    def pyaudio_sample_format(sample_format: str):
        if sample_format == 'int16':
            return pyaudio.paInt16
        elif sample_format == 'int32':
            return pyaudio.paInt32
        elif sample_format == 'float32':
            return pyaudio.paFloat32
        raise ValueError(f"Unknown sample format: {sample_format}")


class JackBackend(AudioBackend):
    def open(self, config: Config, stream_callback: Callable[[np.ndarray], np.ndarray]):
        log.info('Initializing JACK server for streaming audio...')
        if config.online:
            in_device = config.jack_online_in_device
            out_device = config.jack_online_out_device
        else:
            in_device = config.jack_offline_in_device
            out_device = config.jack_offline_out_device

        cmdline = f'/usr/bin/jackd -ndefault --realtime -d alsa' \
                  f' --device {in_device}' \
                  f' --device {out_device}' \
                  f' --period {config.chunk_size}' \
                  f' --rate {config.sampling_rate}'

        def on_jackd_error(e: CommandError):
            log.error(f'JACK server failed to start')
        
        def on_next_line(line: str):
            log.debug(f'JACK output', stdout=line.strip())

        self.jackd_cmd = BackgroundCommand(
            cmdline, on_error=on_jackd_error, on_next_line=on_next_line, 
            print_stdout=False, debug=True,
        )

        client = self.open_client()
        self.jack_client = client
        log.info('JACK server started')

        looper_input = client.inports.register('input_2')
        looper_output = client.outports.register('output_2')

        system_inputs = client.get_ports(is_audio=True, is_output=True, is_physical=True)
        assert system_inputs, 'No jack inputs found to record from'
        system_input = system_inputs[-1]

        if config.jack_playback_ports:
            system_playback_ports = []
            for port_name in config.jack_playback_ports:
                ports = client.get_ports(port_name, is_audio=True, is_input=True, is_physical=True)
                assert len(ports) == 1, f'No jack output found for {port_name}'
                system_playback_ports.extend(ports)
        else:
            system_playback_ports = client.get_ports(is_audio=True, is_input=True, is_physical=True)
            assert system_playback_ports, 'No jack outputs found to play to'

        playback_names = ', '.join([port.name for port in system_playback_ports])
        log.info('Wiring JACK ports', capture=system_input.name, playback_ports=playback_names)

        if config.sample_format in {'int16', 'int32'}:
            dst_max_amp = sample_format_max_amplitude(config.sample_format)
            dst_np_type = sample_format_numpy_type(config.sample_format)

            @client.set_process_callback
            def process(blocksize: int):
                input_chunk: np.ndarray = looper_input.get_array()  # float32
                input_chunk = (input_chunk * dst_max_amp).astype(dst_np_type)
                out_chunk = stream_callback(input_chunk)
                out_chunk = (out_chunk / dst_max_amp).astype(np.float32)
                looper_output.get_array()[:] = out_chunk

        elif config.sample_format == 'float32':
            @client.set_process_callback
            def process(blocksize: int):
                input_chunk: np.ndarray = looper_input.get_array()  # float32
                out_chunk = stream_callback(input_chunk)
                looper_output.get_array()[:] = out_chunk

        else:
            raise ValueError(f"Unknown sample format: {config.sample_format}")

        @client.set_shutdown_callback
        def shutdown(status, reason):
            log.info('JACK shutdown', status=status, reason=reason)

        client.activate()
        client.connect(system_input, looper_input)
        for playback_port in system_playback_ports:
            client.connect(looper_output, playback_port)

        log.info('JACK stream started')

    def close(self):
        try:
            self.jack_client.outports.clear()
            self.jack_client.inports.clear()
        except jack.JackErrorCode as e:
            log_exception(e)
        self.jack_client.deactivate(ignore_errors=True)
        self.jack_client.close(ignore_errors=True)
        log.info('Audio JACK Stream closed')
        self.jackd_cmd.terminate()
        log.debug('JACK server closed')

    @backoff.on_exception(backoff.expo, jack.JackOpenError, factor=0.2, max_value=2, max_time=10, jitter=None)
    def open_client(self) -> jack.Client:
        log.debug('Connecting to JACK server...')
        return jack.Client('raspberry_looper', no_start_server=True)
