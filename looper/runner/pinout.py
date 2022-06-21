from typing import Callable
from gpiozero import LED, Button, PWMLED


class Pinout:
    def __init__(self) -> None:
        self.loopback_led = PWMLED(27)  # white
        self.progress_led = PWMLED(10)  # blue

        self.record_leds = [
            LED(11),  # red
            LED(22),  # red
        ]
        self.play_leds = [
            LED(9),  # green
            LED(17),  # green
        ]

        self.record_buttons = [
            Button(6),
            Button(3),
        ]
        self.play_buttons = [
            Button(5),
            Button(2),
        ]
        self.shutdown_button = Button(13)
        self.foot_switch = Button(19)

        self.output_relay = LED(26)

        self.init_leds()
        self.output_relay.on()

    def init_leds(self):
        self.loopback_led.on()
        self.progress_led.off()

        for led in self.record_leds:
            led.off()
        for led in self.play_leds:
            led.off()

    def tear_down(self):
        self.init_leds()
        self.output_relay.off()

    def set_output_relay(self, state: bool):
        if state:
            self.output_relay.on()
        else:
            self.output_relay.off()

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

    def on_button_click(self,
        btn: Button,
        on_click: Callable,
    ):
        btn.when_pressed = on_click

    def last_record_led(self) -> LED:
        return self.record_leds[-1]
