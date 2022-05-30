from abc import ABC, abstractmethod
from typing import Callable, List

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

        # Multiple soundcards with JACK: https://jackaudio.org/faq/multiple_devices.html
        # ALSA driver options: http://ccrma.stanford.edu/planetccrma/man/man1/jackd.1.html
        if in_device == out_device:
            device_line = f' --device {in_device}'
        else:
            device_line = f' --capture {in_device} --playback {out_device}'
        cmdline = f'/usr/bin/jackd -ndefault --realtime -d alsa' \
                  f'{device_line}' \
                  f' --period {config.chunk_size}' \
                  f' --nperiods 2' \
                  f' --rate {config.sampling_rate}'

        def on_jackd_error(e: CommandError):
            log.error(f'JACK server failed')
        
        def on_next_line(line: str):
            log.debug(f'JACK output', stdout=line.strip())

        self.jackd_cmd = BackgroundCommand(
            cmdline, on_error=on_jackd_error, on_next_line=on_next_line, 
            print_stdout=False, debug=True,
        )

        client: jack.Client = self.open_client()
        self.jack_client: jack.Client = client
        log.info('JACK server started')
        self.list_ports()

        looper_input = client.inports.register('input_2')
        looper_output = client.outports.register('output_2')

        capture_ports = self.get_capture_ports(config)
        playback_ports = self.get_playback_ports(config)

        capture_names = ', '.join([port.name for port in capture_ports])
        playback_names = ', '.join([port.name for port in playback_ports])
        log.info('Wiring JACK ports', capture_ports=capture_names, playback_ports=playback_names)

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
                input_copy = np.copy(input_chunk)
                out_chunk = stream_callback(input_copy)
                looper_output.get_array()[:] = out_chunk

        else:
            raise ValueError(f"Unknown sample format: {config.sample_format}")

        @client.set_shutdown_callback
        def shutdown(status, reason):
            log.info('JACK shutdown', status=status, reason=reason)

        client.activate()
        for capture_port in capture_ports:
            client.connect(capture_port, looper_input)
        for playback_port in playback_ports:
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

    def list_ports(self):
        playback_ports = self.jack_client.get_ports(is_input=True)
        capture_ports = self.jack_client.get_ports(is_output=True)

        port_names = ', '.join([port.name for port in capture_ports])
        log.debug('found JACK capture ports', capture_ports=port_names)
        port_names = ', '.join([port.name for port in playback_ports])
        log.debug('found JACK playback ports', playback_ports=port_names)

    def get_capture_ports(self, config: Config) -> List[jack.Port]:
        if config.jack_capture_ports:
            ports = []
            for port_name in config.jack_capture_ports:
                capture_ports = self.jack_client.get_ports(port_name, is_audio=True, is_output=True)
                assert capture_ports, f'Not found jack capture port {port_name}'
                ports.extend(capture_ports)
            return ports
        else:
            capture_ports = self.jack_client.get_ports(is_audio=True, is_physical=True, is_output=True)
            assert capture_ports, 'No jack capture ports found to record from'
            return [capture_ports[-1]]

    def get_playback_ports(self, config: Config) -> List[jack.Port]:
        if config.jack_playback_ports:
            ports = []
            for port_name in config.jack_playback_ports:
                playback_ports = self.jack_client.get_ports(port_name, is_audio=True, is_input=True)
                assert playback_ports, f'Not found jack playback port {port_name}'
                ports.extend(playback_ports)
            return ports
        else:
            playback_ports = self.jack_client.get_ports(is_audio=True, is_physical=True, is_input=True)
            assert playback_ports, 'No jack playback ports found to play to'
            return playback_ports
