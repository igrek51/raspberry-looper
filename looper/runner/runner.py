from signal import pause

from nuclear.sublog import log

from looper.runner.pinout import Pinout


def run_looper():
    log.info("Starting looper...")

    pinout = Pinout()

    pinout.green_led.pulse(fade_in_time=0.2, fade_out_time=0.2)

    log.info("Ready to work")
    pause()
