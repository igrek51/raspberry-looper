from gpiozero import LED, Button, PWMLED


class Pinout:
    green_led = PWMLED(17)
    blue_led = LED(27)
    record_button = Button(2)
    play_button = Button(3)
