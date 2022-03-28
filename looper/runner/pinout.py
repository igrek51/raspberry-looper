from typing import Callable
from gpiozero import LED, Button, PWMLED


class Pinout:
    def __init__(self) -> None:
        self.loopback_blue_led = PWMLED(27)
        self.record_red_led = LED(22)
        self.play_green_led = LED(17)

        self.record_button = Button(3)
        self.play_button = Button(2)

        self.init_led()

    def init_led(self):
        self.loopback_blue_led.on()
        self.record_red_led.off()
        self.play_green_led.off()

    def on_button_click_and_hold(self, 
        btn: Button,
        on_click: Callable,
        on_hold: Callable,
    ):
        was_pressed = False

        def _on_press():
            nonlocal was_pressed
            was_pressed = True

        def _on_release():
            nonlocal was_pressed
            if was_pressed:
                on_click()
            
        def _on_held():
            nonlocal was_pressed
            was_pressed = False
            on_hold()

        btn.when_held = _on_held
        btn.when_pressed = _on_press
        btn.when_released = _on_release