from nuclear.sublog import logerr
from nuclear import CliBuilder
from looper.devices import list_devices
from looper.latency import measure_latency

from looper.wire import wire_input_output
from looper.runner.runner import run_looper


def main():
    cli = CliBuilder()

    @cli.add_command("run")
    def run():
        """Run looper in a standard mode"""
        run_looper()

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

    with logerr():
        cli.run()
