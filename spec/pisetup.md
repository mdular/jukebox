# 1. Flash Raspberry Pi OS

Download **Raspberry Pi OS Lite (64-bit)**.

Use **Raspberry Pi Imager** (recommended):

```text
https://www.raspberrypi.com/software/
```

Steps:

1. Insert SD card
2. Open Imager
3. Choose OS
   → **Raspberry Pi OS Lite**
4. Choose Storage → your SD card

Before writing, open the **advanced options**.

Shortcut:

```
Ctrl + Shift + X
```

This lets you configure everything headless.

---

# 2. Configure headless settings

Enable the following:

### Hostname

```
jukebox
```

---

### Enable SSH

Enable:

```
Use password authentication
```

(or add an SSH key if you prefer)

---

### Username / password

Example:

```
username: pi
password: <choose something>
```

---

### WiFi

Enter your network credentials:

```
SSID: your-wifi
Password: your-password
Country: DE
```

Setting the correct WiFi country matters for regulatory compliance and radio settings. ([raspberrypi.com](https://www.raspberrypi.com/documentation/computers/configuration.html#setting-the-wifi-country-code))

---

### Locale settings

Recommended:

```
Time zone: Europe/Berlin
Keyboard: us or de
```

---

# 3. Write the SD card

Click **Write**.

This injects all settings before first boot.

---

# 4. Boot the Pi

Insert the SD card into the Pi and power it.

Boot time:

```
~30–60 seconds
```

The Pi will automatically:

* connect to WiFi
* enable SSH
* set hostname
* create the user

---

# 5. Connect from your laptop

### Option A: mDNS

Most networks support this.

```
ssh pi@jukebox.local
```

---

### Option B: find IP via router

Check DHCP client list.

Then:

```
ssh pi@192.168.x.x
```

---

# 6. First setup commands

Once logged in:

Update packages:

```bash
sudo apt update
sudo apt upgrade -y
```

Install basics:

```bash
sudo apt install -y git python3-pip python3-venv
```

Set correct audio output later if needed.

---

# 7. Optional but recommended tweaks

### Expand filesystem

Usually automatic now, but check:

```bash
sudo raspi-config
```

System → expand filesystem.

---

### Set static hostname

Already done if you used the Imager settings.

Check:

```bash
hostname
```

---

### Enable SSH key login later

After first login you can add your key:

```bash
mkdir -p ~/.ssh
nano ~/.ssh/authorized_keys
```

---

# 8. Test the QR scanner

When the scanner arrives:

Plug into Pi.

Then run:

```bash
cat
```

Scan a QR code.

Expected output:

```
spotify:track:4cOdK2wGLETKBW3PvgPWqT
```

The scanner behaves like a keyboard device.

---

# 9. Suggested directory on the Pi

Once your repo is ready:

```bash
mkdir ~/projects
cd ~/projects
git clone <repo>
cd jukebox
```

---

# 10. Future service setup

Eventually you will run the controller as a system service:

```
/etc/systemd/system/jukebox.service
```

But that can wait until the code exists.

---

# Optional (nice improvement)

If you'd like, I can also show you how to enable:

* **automatic WiFi fallback network**
* **OTA updates via git pull**
* **read-only filesystem mode** (very useful for appliance devices)

Those make the jukebox much more robust.
