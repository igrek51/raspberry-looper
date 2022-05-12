import io
import signal
import sys
import subprocess
from typing import Callable
import threading
import psutil

from nuclear.shell import CommandError
from nuclear.sublog import log


class BackgroundCommand:
    def __init__(self,
        cmd: str,
        on_next_line: Callable[[str], None] = None,
        on_error: Callable[[CommandError], None] = None,
        print_stdout: bool = False,
        print_stderr: bool = True,
        debug: bool = False,
    ):
        """Run system shell command in background."""
        self._stop: bool = False
        self._captured_stream = io.StringIO()
        self._debug = debug

        def monitor_output(stream: BackgroundCommand):
            stdout_iter = iter(stream._process.stdout.readline, b'')
            
            while True:
                if stream._stop:
                    break
                try:
                    line = next(stdout_iter)
                except StopIteration:
                    break

                line_str = line.decode()
                if print_stdout:
                    sys.stdout.write(line_str)
                    sys.stdout.flush()
                if on_next_line is not None:
                    on_next_line(line_str)
                self._captured_stream.write(line_str)

            stream._process.wait()
            if stream._process.returncode != 0 and on_error is not None and not self._stop:
                stdout = self._captured_stream.getvalue()
                on_error(CommandError(cmd, stdout, stream._process.returncode))

            if debug:
                log.debug(f'Command finished: {cmd}')

        self._monitor_thread = threading.Thread(
            target=monitor_output,
            args=(self,),
            daemon=True,
        )

        if debug:
            log.debug(f'Command: {cmd}')
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if print_stderr else subprocess.PIPE,
            shell=True,
        )

        self._monitor_thread.start()

    def terminate(self):
        self._stop = True

        parent = psutil.Process(self._process.pid)
        children = parent.children(recursive=False)
        for child in children:
            if self._debug:
                log.debug(f'terminating child process', pid=child.pid)
            child.send_signal(signal.SIGTERM)

        self._process.terminate()
        self._process.poll()  # wait for subprocess
        if self._debug:
            log.debug(f'subprocess terminated', pid=self._process.pid)
        self._monitor_thread.join()  # wait for thread is finished

    def wait(self):
        self._process.poll()
        self._monitor_thread.join()  # wait for thread is finished

    @property
    def stdout(self) -> str:
        return self._captured_stream.getvalue()

    @property
    def is_running(self) -> bool:
        return self._monitor_thread.is_alive()
