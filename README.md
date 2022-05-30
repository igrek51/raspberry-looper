# Raspberry Looper
Audio track looper running on Raspberry Pi 
for playing multi-instrumental songs on your own.
You can record and play tracks using physical buttons and LEDs
as well as a web application through WiFi,
which provides more advanced functions.

## Features
Our chief weapons are:

- recording and playing unlimited number of tracks,
- adjusting the volume levels of the input, output and each of the tracks, 
- recording output to MP3 file and downloading it from there,
- built-in metronome,
- saving and restoring all tracks to a session file,
- controlling tracks with physical buttons and web app from a mobile phone,
- visualizing track plots,
- running on either Raspberry Pi or a regular PC with Linux,
- support for JACK low-latency audio streaming or pyAudio library,

## Examples
![](./docs/img/device-in-action-labelled.jpg)

Web application available at http://pi:8000 in your WiFi network:

![](./docs/img/screen-tracks.png)

![](./docs/img/screen-plot.png)

![](./docs/img/screen-volume.png)

Check out [sample recording](https://raw.githubusercontent.com/igrek51/raspberry-looper/master/docs/example/list_2022-04-21_remaster.mp3)

## Setup

### Running on Raspberry Pi
You're going to need:

- Raspberry Pi 3 or other compatible board
- USB soundcard with 1 input and 1 output

On the Raspberry Pi:

1. Flash official [RaspiOS](https://www.raspberrypi.com/software/operating-systems/) `2022-04-04-raspios-bullseye-armhf.img` on SD.  
   Plug in USB soundcard with input and output.
2. Boot Raspberry, let it reboot (expand filesystem), configure WiFi, change user password.
3. Enable SSH: `sudo raspi-config` / Interface Options / SSH

On your host:

4. Log in to the Raspberry Pi:
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
    From now on you can log in with `ssh pi` command.

On the Raspberry Pi:

6. Install pyaudio: `sudo apt install python3-pyaudio`.

7. Install required packages: `sudo apt install libatlas-base-dev screen`

8. Install JACK for real-time, low-latency audio streaming:  
  ```bash
  sudo apt install jackd
  sudo usermod -a -G audio $USER
  id -g
  ```

9. Setup volume levels with `alsamixer`:
    - F6, 
    - select USB Audio Device,
    - F5 (to view Playback and Capture), 
    - Speaker Volume to 100% (0-4 dB),
    - Capture Mic Volume to 13%-27% (0-9 dB).

On the host:

10. Run `make remote-install` to push the source code.

On Raspberry Pi:

11. Log in again via SSH to reload `~/.profile`.

12. Add looper to autostart:
```bash
mkdir -p /home/pi/.config/autostart
cat << 'EOF' > /home/pi/.config/autostart/looper.desktop
[Desktop Entry] 
Type=Application
Exec=screen -dm -S looper bash -c "python3 -m looper run |& tee /home/pi/looper/looper.log; exec bash"
EOF
```

13. Reboot or run `looper run`.

### Running on PC with Linux
Looper can also run on a regular Linux PC in a special "Offline" mode without controlling buttons and LEDs
(cause there is no GPIO module). 
The application can be still controlled by a web browser.
Virtual footswitch can be configured to turn recording on spacebar press.

You need Python 3.8 or higher 
(at this moment `pyaudio` lib has some issues with Python 3.10, so 3.8 or 3.9 versions are recommended).

1. Install required libraries:  
  `sudo apt install python3-pyaudio`  
   (On Debian: `sudo apt install portaudio19-dev` or do as stated [here](https://stackoverflow.com/a/35593426/6772197))
  `sudo apt install libatlas-base-dev`  
2. Install JACK (if you're going to use JACK audio backend):  
  ```bash
  sudo apt install jackd
  sudo usermod -a -G audio $USER
  id -g
  ```
3. Create virtualenv and setup python project with `make setup`. Activate virtualenv: `. venv/bin/activate`.
4. Run `looper run` and visit http://localhost:8000 in your browser to see the frontend app.
5. Happy jamming!

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
- recording output session to MP3 file and downloading it from there,
- displaying track plots.

## Configuration
If you wish to override the default configuration,
create a `default.config.yaml` file in the project directory
and fill it according to [config.py](./looper/runner/config.py).
For instance:
```yaml
# Backend for streaming audio chunks: pyaudio or jack
audio_backend: jack
# Sampling size (bit depth) and sample format
sample_format: float32
# sampling rate [Hz], eg.: 44100, 48000
sampling_rate: 48000
# buffer size, number of frames per buffer
chunk_size: 1024

# number of available tracks in looper
tracks_num: 8

# HTTP server port for web interface and API
http_port: 8080

# If enabled, pressing spacebar key activates recording like footswitch
spacebar_footswitch: true
```

You can also create multiple config files and run `looper run --config variant2.config.yaml`.

## Logs
Watch logs with `less -R /home/pi/looper/looper.log` or with `cd ~/looper && make logs`.

## Latency
Test results:

- With `pyaudio` backend, looper introduces `21 - 46 ms` latency.
- With `jack` audio backend, looper introduces `21 - 67 ms` latency.

## References
- Inspired by [raspi-looper](https://github.com/RandomVertebrate/raspi-looper)
- Controlling buttons and LEDs: [Raspberry GPIO controls](https://gpiozero.readthedocs.io/en/stable/recipes.html)
- Recording and playing audio in Python: [PyAudio docs](http://people.csail.mit.edu/hubert/pyaudio/#docs)
- Streaming with JACK: [JACK client for Python](https://jackclient-python.readthedocs.io/en/0.5.3/)
