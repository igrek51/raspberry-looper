from gpiozero import LED, Button, PWMLED


class Pinout:
    def __init__(self) -> None:
        self.green_led = PWMLED(17)
        self.blue_led = LED(27)
        self.record_button = Button(2)
        self.play_button = Button(3)
