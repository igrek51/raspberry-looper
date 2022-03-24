from nuclear.sublog import logerr
from nuclear import CliBuilder
from looper.latency import measure_latency

from looper.wire import wire_input_output
from looper.runner.runner import run_looper


def main():
    cli = CliBuilder()

    @cli.add_command("run")
    def run():
        run_looper()

    @cli.add_command("wire")
    def wire():
        wire_input_output()

    @cli.add_command("latency")
    def latency():
        measure_latency()

    with logerr():
        cli.run()
