# Raspberry Looper
Audio track looper running on Raspberry Pi.
It is controlled by physical buttons and LEDs,
more functions are provided by frontend through WiFi.

## Setup
On the Raspberry Pi:

1. Flash official RaspiOS `2022-04-04-raspios-bullseye-armhf.img` on SD.  
   Plug in USB soundcard with input and output.
2. Boot Raspberry, let it reboot (expand filesystem), configure WiFi, change user password.
3. Enable SSH: `sudo raspi-config` / Interface Options / SSH

On the host:

4. Log in the Raspberry Pi:
    ```bash
    ssh-keygen -f "$HOME/.ssh/known_hosts" -R "192.168.0.51"
    ssh pi@192.168.0.51 "mkdir -p /home/pi/.ssh"
    # Allow to log in with your ssh key
    scp ~/.ssh/id_rsa.pub pi@192.168.0.51:/home/pi/.ssh/authorized_keys
    ```

5. Configure SSH alias in `$HOME/.ssh/config`:
    ```
    Host pi
        HostName 192.168.0.51
        User pi
    ```
    From now on you can log in with `ssh pi`.

On the Raspberry Pi:

6. Install pyaudio: `sudo apt install python3-pyaudio` (on RaspberryPi).  
    On Debian: `sudo apt install portaudio19-dev` or do as stated [here](https://stackoverflow.com/a/35593426/6772197)

7. Install `sudo apt install libatlas-base-dev`

8. Setup volume levels with `alsamixer`:
    - F6, 
    - select USB Audio Device,
    - F5 (to view Playback and Capture), 
    - Speaker Volume to 100% (0 dB),
    - Capture Mic Volume to 13% (0 dB).

On the host:

9. Run `make remote-install` to push source code.

10. Log in again via SSH to reload `~/.profile`.

On Raspberry Pi:

11. Run `looper run`.

12. (Optional) Add looper to autostart:
```bash
mkdir -p /home/pi/.config/autostart
cat << 'EOF' > /home/pi/.config/autostart/looper.desktop
[Desktop Entry] 
Type=Application
Exec=lxterminal -e "python3 -m looper run |& tee /home/pi/looper/looper.log"
EOF
```

## Examples
![](./docs/img/device-in-action-labelled.jpg)

![](./docs/img/screen-tracks.jpg)

![](./docs/img/screen-plot.jpg)

![](./docs/img/screen-volume.jpg)

![](./docs/img/screen-recorder.jpg)

## Usage
Run `looper --help` to see available commands.

- `looper run` - Run looper in a standard mode for recording and playing.
- `looper devices` - List input devices to find out what is your device index.
- `looper latency` - Measure output-input latency. 
  Put microphone close to a speaker or wire the output with the input.
- `looper wire` - Wire the input with the output to see 
  if you're comfortable with the audio quality and latency.

Apart from controlling the looper with the physical buttons, 
you can also visit HTTP frontend page at http://192.168.0.51:8000 .
This gives access to more options like:
- recording/playing more tracks (unlimited number), 
- adjusting the volume levels for the input and each of the tracks, 
- recording output session to MP3 file and downloading it from there.

## Logs
Watch logs with `less -R /home/pi/looper/looper.log` or with `cd ~/looper && make logs`.

## References
- Inspired by [raspi-looper](https://github.com/RandomVertebrate/raspi-looper)
- [PyAudio docs](http://people.csail.mit.edu/hubert/pyaudio/#docs)
- [Raspberry GPIO controls](https://gpiozero.readthedocs.io/en/stable/recipes.html)
