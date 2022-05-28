from typing import Optional
from nuclear import CliBuilder

from looper.check.devices import list_devices
from looper.check.latency import measure_input_latency, measure_cycle_latency
from looper.check.wire import wire_input_output
from looper.runner.runner import run_looper


def main():
    cli = CliBuilder(log_error=True)

    @cli.add_command("run")
    def run(config: Optional[str] = None, backend: Optional[str] = None):
        """
        Run looper in a standard mode
        :param config: path to config YAML file
        :param backend: audio backend for streaming chunks, pyaudio or jack
        """
        run_looper(config, backend)

    @cli.add_command("wire")
    def wire():
        """Wire input with output"""
        wire_input_output()

    @cli.add_command('latency', 'input')
    def latency_input():
        """Measure output-input latency"""
        measure_input_latency()

    @cli.add_command('latency', 'cycle')
    def latency_cycle():
        """Measure full cycle latency"""
        measure_cycle_latency()

    @cli.add_command("devices")
    def devices():
        """List input devices"""
        list_devices()

    cli.run()
