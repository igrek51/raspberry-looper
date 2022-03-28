from nuclear.sublog import log
from looper.runner.config import Config

from looper.runner.pinout import Pinout
from looper.runner.player import Player


def run_looper():
    log.info("Starting looper...")
    pinout = Pinout()
    config = Config()
    player = Player(pinout, config)
    player.init()
