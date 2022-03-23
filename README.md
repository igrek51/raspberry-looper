# Raspberry Looper
Audio track looper running on Raspberry Pi.

## Setup

On the Raspberry Pi:
1. Flash official RaspiOS `2022-01-28-raspios-bullseye-armhf.img` on SD.
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
Then you can log in with `ssh pi`.
