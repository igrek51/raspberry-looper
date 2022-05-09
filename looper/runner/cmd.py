from typing import Callable
import subprocess
import sys
import io
import threading

from nuclear import CommandError, log


class BackgroundCommand:
    def __init__(self,
                 cmd: str,
                 on_next_line: Callable[[str], None] = None,
                 on_error: Callable[[CommandError], None] = None,
                 print_stdout: bool = False,
                 ):
        self.stop: bool = False
        log.debug(f'Command: {cmd}')
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        self.stdout: str = ''

        def monitor_output(stream: BackgroundCommand):
            captured_stream = io.StringIO()
            for line in iter(stream.process.stdout.readline, b''):
                if stream.stop:
                    break
                line_str = line.decode()
                if print_stdout:
                    sys.stdout.write(line_str)
                    sys.stdout.flush()
                if on_next_line is not None:
                    on_next_line(line_str)
                captured_stream.write(line_str)

            stream.process.wait()
            stream.stdout = captured_stream.getvalue()
            if stream.process.returncode != 0 and on_error is not None and not self.stop:
                on_error(CommandError(cmd, stream.stdout, stream.process.returncode))

            log.debug(f'Command finished: {cmd}')

        self.thread = threading.Thread(
            target=monitor_output,
            args=(self,),
            daemon=True,
        )
        self.thread.start()

    def interrupt(self):
        self.stop = True
        self.process.terminate()
