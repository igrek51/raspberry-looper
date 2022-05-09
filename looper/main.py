from typing import Optional
from nuclear import CliBuilder

from looper.check.devices import list_devices
from looper.check.latency import measure_latency
from looper.check.wire import wire_input_output
from looper.runner.runner import run_looper


def main():
    cli = CliBuilder(log_error=True)

    @cli.add_command("run")
    def run(backend: Optional[str] = None):
        """
        Run looper in a standard mode
        :param backend: audio backend for streaming chunks, pyaudio or jack
        """
        run_looper(backend)

    @cli.add_command("wire")
    def wire():
        """Wire input with output"""
        wire_input_output()

    @cli.add_command("latency")
    def latency():
        """Measure output-input latency"""
        measure_latency()

    @cli.add_command("devices")
    def devices():
        """List input devices"""
        list_devices()

    cli.run()
