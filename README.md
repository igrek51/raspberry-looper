# Raspberry Looper
Audio track looper running on Raspberry Pi.

## Setup

On the Raspberry Pi:

1. Flash official RaspiOS `2022-01-28-raspios-bullseye-armhf.img` on SD.  
   Plug in USB soundcard with input and output.
2. Boot Raspberry, let it reboot (expand filesystem), configure WiFi, change user password.
3. Enable SSH: `sudo raspi-config` / Interface Options / SSH

On the host:

5. Log in the Raspberry Pi:
    ```bash
    ssh-keygen -f "$HOME/.ssh/known_hosts" -R "192.168.0.51"
    ssh -o StrictHostKeyChecking=no pi@192.168.0.51 "mkdir -p /home/pi/.ssh"
    # Allow to log in with your ssh key
    scp -o StrictHostKeyChecking=no ~/.ssh/id_rsa.pub pi@192.168.0.51:/home/pi/.ssh/authorized_keys
    ```

4. Configure SSH alias in `$HOME/.ssh/config`:
    ```
    Host pi
        HostName 192.168.0.51
        User pi
    ```
    From now on you can log in with `ssh pi`.

On the Raspberry Pi:

5. Install pyaudio: `sudo apt install python3-pyaudio`.  
    On Debian: `sudo apt install portaudio19-dev` or do as stated [here](https://stackoverflow.com/a/35593426/6772197)

6. Setup volume levels with `alsamixer`:
    - F6, 
    - select USB Audio Device,
    - F5 (to view Playback and Capture), 
    - Speaker Volume to 100% (0 dB),
    - Capture Mic Volume to 13% (0 dB).

7. Comment out `load-module module-suspend-on-idle` in `/etc/pulse/default.pa`.

On the host:

8. Run `make push-first` to push source code.

On Raspberry Pi:

9. Run `looper run`.

10. (Optional) Add looper to autostart:
```bash
mkdir -p /home/pi/.config/autostart
cat << 'EOF' > /home/pi/.config/autostart/looper.desktop
[Desktop Entry] 
Type=Application
Exec=lxterminal -e "python3 -m looper run |& tee /home/pi/looper/looper.log"
EOF
```
Watch logs with `less -R /home/pi/looper/looper.log`

## List input devices
To find out what is your device index:

```python
import pyaudio

pa = pyaudio.PyAudio()
n = pa.get_device_count()

print('Found ' + str(n) + ' devices.')

for i in range(n):
    print('INDEX ' + str(i) + ': ' + str(pa.get_device_info_by_index(i)['name']))

pa.terminate()
```

or

```python
import pyaudio
p = pyaudio.PyAudio()
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')
for i in range(0, numdevices):
    if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
        print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))
```


## References
- https://github.com/RandomVertebrate/raspi-looper
- http://people.csail.mit.edu/hubert/pyaudio/#docs
- https://gpiozero.readthedocs.io/en/stable/recipes.html
