from nuclear.sublog import log, logerr
from nuclear import CliBuilder

from looper.wire import wire_input_output


def main():
    cli = CliBuilder()

    @cli.add_command("wire")
    def wire():
        wire_input_output()

    @cli.add_command("run")
    def run():
        wire_input_output()

    with logerr():
        cli.run()
