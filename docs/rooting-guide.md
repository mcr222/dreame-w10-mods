# Dreame W10 (P2027): UART root → DustBuilder → Valetudo

A complete walkthrough of rooting a Dreame W10 (`dreame.vacuum.p2027`) **without the Dreame breakout PCB**, using jumper wires straight into the debug port, then installing the DustBuilder rooted firmware and Valetudo. Every step here was done on a real W10 in October 2026.

It follows the official [Valetudo Dreame UART guide](https://valetudo.cloud/pages/installation/dreame/). If anything here disagrees with it, the official guide wins. A printable checklist with the same steps is in [`wiring-checklist.html`](wiring-checklist.html).

**W10 facts** (from [valetudo.cloud](https://valetudo.cloud/pages/general/supported-robots/)): UART root method, **no secure boot**, Valetudo build `armv7-lowmem`.

Placeholders used below:

| Placeholder | Meaning |
|---|---|
| `<SERIAL>` | serial number from the sticker **under the dustbin**, in capitals (starts with `P2027`) |
| `<XXXX>` | last 4 characters of the robot's Wi-Fi hotspot name `dreame-vacuum-p2027_miap<XXXX>` |
| `IP:PORT` | address printed by the file server on your laptop (starts with `192.168.5.`) |
| `<robot-ip>` | the robot's address on your home network after setup |

---

## 1 · How the root works

The stock Dreame firmware has a debug feature: when a USB storage partition (`/dev/sd[a-z][0-9]`) appears, it mounts it and starts a **root login shell on the serial port**. The root password is `base64(md5(serial))`. So you need:

1. a 3.3V UART connection to see and type into the shell,
2. a USB stick on the robot's USB-OTG pins, with the ID pin grounded so the robot acts as USB host,
3. the password calculated from the serial number.

```bash
echo -n "<SERIAL>" | md5sum | base64
```

DustBuilder also shows this password on its build confirmation page, so you can check your calculation.

## 2 · What you need

- **USB-TTL adapter set to 3.3V** (a CH340 was used here; only GND, RXD and TXD are connected)
- **Jumper wires** that fit 2.0mm pitch holes
- **A USB stick** with an MBR partition table and **one FAT32 partition** (no files needed)
- **A USB cable cut to get a female USB-A socket** (4 wires: red 5V, white D−, green D+, black GND)
- **A multimeter**
- Software on the laptop: `picocom` (and optionally `tmux`), [valetudo-helper-httpbridge](https://github.com/Hypfer/valetudo-helper-httpbridge/releases), and [Valetudo `valetudo-armv7-lowmem`](https://github.com/Hypfer/Valetudo/releases)

## 3 · The debug connector

2×8 pins, 2.0mm pitch, behind the rubber flap in the dustbin bay. Viewed with the dustbin removed, **robot top facing up**, looking into the port, col 1 = leftmost. The W10 uses the generic Dreame pinout **rotated 180°**. Every pin below was confirmed in practice: UART and USB both worked.

| | col 1 | col 2 | col 3 | col 4 | col 5 | col 6 | col 7 | col 8 |
|---|---|---|---|---|---|---|---|---|
| **TOP** | VBUS 5V | D− | D+ | USB-ID | GND | TX (robot) | RX (robot) | BOOT_SEL (**leave empty**) |
| **BOTTOM** | – | – | – | – | – | GND | – | – |

### Wiring

The wire colours are the ones used here; they're named in the steps so each wire is easy to track. The adapter has its own jumpers (black/white/brown) that join onto the robot-side wires (black/orange/yellow).

| Part | Pin | Part wire | | Robot wire | Robot hole |
|---|---|---|---|---|---|
| USB-TTL adapter | GND | ⚫ Black | ↔ | ⚫ Black | bottom col 6 · GND |
| USB-TTL adapter | RXD | ⚪ White (tape-marked) | ↔ | 🟠 Orange | top col 6 · robot TX |
| USB-TTL adapter | TXD | 🟤 Brown | ↔ | 🟡 Yellow | top col 7 · robot RX |
| USB socket | 5V | 🔴 Red | ↔ | 🔴 Red | top col 1 · VBUS |
| USB socket | D− | ⚪ White | ↔ | ⚪ White | top col 2 · D− |
| USB socket | D+ | 🟢 Green | ↔ | 🟢 Green | top col 3 · D+ |
| USB socket | GND | ⚫ Black | ↔ | 🔵 Blue | top col 5 · GND |
| USB socket | GND | ⚫ Black (same wire) | ↔ | 🔵 Blue scrap (bridge) | top col 4 · USB-ID |
| **Nothing** | | | | | adapter 3V3 · adapter 5V · robot col 8 (BOOT_SEL) |

```
 Laptop ══USB══ USB-TTL ── black/white/brown ↔ black/orange/yellow ───────────┐
                                                                             ├── Robot debug port
 USB stick ══ USB socket ── red/white/green/black ↔ red/white/green/blue+bridge┘
 Laptop ~~~ Wi-Fi ~~~ robot hotspot (file transfer / Valetudo setup)
```

- **USB-ID bridge:** a short wire from col 4 to GND. Grounding the ID pin puts the robot in USB **host** mode, so it powers and reads the stick, like a phone's OTG adapter.
- **The laptop never connects to the robot's USB pins.** Both would be USB hosts putting out 5V. The laptop only talks to the robot over the USB-TTL adapter (serial) and Wi-Fi.
- **UART crossover:** the adapter's RX listens to the robot's TX, and the adapter's TX talks to the robot's RX.

### Safety rules

- 🔴 Red (VBUS 5V) never goes to the adapter or the laptop.
- Col 8 (BOOT_SEL), adapter 3V3 and adapter 5V stay empty. The adapter must use 3.3V signals.
- Wire only with the robot OFF. Unplug 5V first and ground last. Keep the adapter plugged into the laptop while removing robot-side wires (an unpowered adapter can put junk on the robot's RX).
- Don't push meter probes into the 2mm holes; measure on the wire's metal end.
- Never power off or undock the robot while the firmware is installing.

---

## 4 · Steps

### A · Preparation

1. **Build the rooted firmware on [DustBuilder](https://builder.dontvacuum.me)** for your serial. Options used here: preinstalled tools, **patch DNS** (needed for Valetudo), manual installer. Download `dreame.vacuum.p2027_fw.tar.gz` and check its md5 against the one DustBuilder gives you. You also get an SSH key zip; its password is in the DustBuilder email.
2. **Calculate the root password** (section 1) and compare it with the one DustBuilder shows.
3. **Download while you're still online:** `valetudo-helper-httpbridge` into a folder, and `valetudo-armv7-lowmem` plus a copy of the firmware into its `www/` subfolder. Later steps put the laptop on the robot's hotspot, which has no internet.

### B · Serial connection (UART)

4. Open the debug port: dustbin out, rubber flap open.
5. *(Recommended)* With the adapter in the laptop, measure adapter TXD ↔ GND: it must be about **3.3V**. If it's 5V, stop and switch the adapter's jumper.
6. Robot OFF. Connect the 3 UART wires: GND → bottom col 6, adapter RXD → top col 6 (robot TX), adapter TXD → top col 7 (robot RX).
7. On the laptop:
   ```bash
   sudo apt install picocom tmux
   tmux new -s w10 'picocom -b 115200 --logfile ~/w10_serial.log /dev/ttyUSB0'
   ```
   Your user must be in the `dialout` group. Ctrl+A Ctrl+X quits picocom, Ctrl+B D leaves tmux running, `tmux attach -t w10` gets back. The log file records everything, which is handy when you're offline in part D.
8. Turn the robot on (hold POWER 3s). **Expected:** a readable boot log, `chpasswd: password for 'root' changed`, and the Wi-Fi hotspot `dreame-vacuum-p2027_miap<XXXX>` coming up.

### C · USB stick & root login

9. **Prepare the USB stick:** MBR with **one FAT32 partition**. Check with `lsblk -f`: it must show `sdX1 vfat FAT32`. A partition table with no partition won't trigger the shell. The known-good image `dreame_uart_root.img` from valetudo.cloud is a fallback.
10. **Test the cut USB cable** with the meter: the 4 wires go to the 4 socket contacts in the order red, white, green, black, and red ↔ black must not beep. A socket shell that isn't connected to black is normal on cheap cables.
11. Robot OFF. **Wire the socket:** red → col 1, white → col 2, green → col 3, socket black → col 5 **and** a short bridge to col 4 (USB-ID). Insulate the joints.
12. Power on, wait for `password for 'root' changed`, then plug the stick into the socket. **Expected:** `p2027_release login:`. Log in as `root` with the password from step 2. You get `[root@p2027_release:~]#` on the stock firmware.
13. Check free space:
    ```sh
    df -h /tmp /data
    ```
    About 110 MB free in `/tmp` (RAM) and 120 MB in `/data` is enough for the ~66 MB firmware package and the ~34 MB Valetudo binary.

### D · Backup & file transfer

The laptop joins the robot's hotspot for this part. If it only has one Wi-Fi card, you're offline until step 21, so have these steps open locally. (Phone USB tethering keeps you online.)

14. Laptop → robot hotspot:
    ```bash
    nmcli dev wifi connect "dreame-vacuum-p2027_miap<XXXX>"
    ```
    If the hotspot isn't listed: hold the robot's **two outer buttons** until it talks. It turns off 30 minutes after boot.
15. Start the file server and note the `IP:PORT` it prints (must start with `192.168.5.`):
    ```bash
    cd <httpbridge folder> && ./valetudo-helper-httpbridge-amd64
    ```
16. **Robot: back up the factory data, upload it, free the RAM.** This holds the robot's identity and LiDAR calibration and can't be recreated.
    ```sh
    tar cvf /tmp/backup.tar /mnt/private/ /mnt/misc/ /etc/OTA_Key_pub.pem /etc/publickey.pem
    curl -X POST http://IP:PORT/upload -F 'file=@/tmp/backup.tar'
    rm /tmp/backup.tar
    ```
    **Expected:** `Successfully uploaded`, and a `backup.tar` of about 45 KB in the httpbridge `www/uploads/` folder. It contains `mnt/private/ULI/factory/` (sn, did, key, mac, cpuid: **device identity**), `mnt/misc/lds_config.json` (**LiDAR calibration**), usage stats and the two public keys.
17. **Robot: firmware to `/tmp` and check:**
    ```sh
    cd /tmp
    wget http://IP:PORT/dreame.vacuum.p2027_fw.tar.gz
    md5sum /tmp/dreame.vacuum.p2027_fw.tar.gz
    ```
    The md5 must match DustBuilder's. If not, delete the file and download it again.
18. **Robot: Valetudo to `/data`:**
    ```sh
    wget http://IP:PORT/valetudo-armv7-lowmem -O /data/valetudo
    chmod +x /data/valetudo
    ls -l /data/valetudo
    ```
    The size must match the file on the laptop.
19. Ctrl+C on the file server.
20. Laptop back to your home Wi-Fi.
21. **Keep the backup safe and private.** Copy it off the laptop (another stick or private cloud storage). Don't publish it.

### E · Install the rooted firmware

22. **Robot: unpack and free the RAM:**
    ```sh
    cd /tmp
    tar -xzvf dreame.vacuum.p2027_fw.tar.gz
    rm dreame.vacuum.p2027_fw.tar.gz
    ls -l
    ```
    **Expected:** `rootfs.img` (~29 MB), `boot.img`, `mcu.bin`, `UIMA.bin`, `UIMB.bin`, `install.sh`, `firmware.md5sum`.
23. **Start the install with a 5-minute delay**, so there's time to unwire and dock the robot:
    ```sh
    sleep 300 && ./install.sh
    ```
    `install.sh` checks the model, the `rootfs.img` size and every md5 before writing anything, and aborts if something is off.
24. Unplug the wires from the robot, adapter still in the laptop: red → white → green → bridge → blue → orange → yellow → **black last**.
25. Close the flap, put the dustbin back, **dock the robot**. Then unplug the adapter and the stick.
26. Wait **about 15 minutes** from step 23 without touching it: update voice/beeps → quiet while writing → reboot (startup sound) → charging.
    No reboot at all? The countdown was probably interrupted while unplugging. That's harmless, since nothing was written; repeat steps 22–25.
27. Reconnect **only the 3 UART wires**. No USB stick needed any more: the rooted firmware keeps a login on the serial port.
28. Restart the serial session (step 7), press Enter, log in as `root` (same password).
29. **Check the banner.** It must show:
    ```
    built with dustbuilder (https://builder.dontvacuum.me)
    <build date>
    <build number>
    ```
    You're rooted.

### F · Valetudo

30. **Turn on autostart** (Valetudo is already in `/data` from step 18):
    ```sh
    ls -l /data/valetudo
    cp /misc/_root_postboot.sh.tpl /data/_root_postboot.sh
    reboot
    ```
31. Laptop → robot hotspot → open **http://192.168.5.1** (Valetudo) → enter your **home Wi-Fi** → laptop back to your home Wi-Fi.
32. Find the robot's IP on your home network (router's DHCP list; a DHCP reservation keeps it fixed) → Valetudo at `http://<robot-ip>`. Check it's running from the shell with `ps | grep [v]aletudo`.
33. **SSH** (no more wires needed). Unzip the DustBuilder key zip (password in the DustBuilder email):
    ```bash
    ssh -i <jobid>.id_rsa root@<robot-ip>
    ```

---

## 5 · What the rooted firmware changes

From DustBuilder's `diff.txt` and `install.sh`:

- A permanent root login on the serial port (`getty … /bin/dustshell` on ttyS0), so the USB stick isn't needed after rooting
- SSH (dropbear) with the DustBuilder key (`/mnt/misc/authorized_keys`). Password login stays on unless `/mnt/misc/ssh_disable_passwords` exists
- Auto OTA updates (`MIIO_AUTO_OTA=false`) and silent upgrades turned off
- Boot hooks: `/data/_root_sysconfig.sh` (before the cloud client) and `/data/_root_postboot.sh` (after boot, used to start Valetudo)
- Extra tools (nano, htop, …)

## 6 · Meter checks

| Robot state | Measure | Expected |
|---|---|---|
| OFF, continuity | bottom col 6 ↔ top col 5 | beep (both GND) |
| OFF, continuity | GND ↔ TX / RX / VBUS | no beep |
| ON, DC volts, black probe on GND | TX (col 6) · RX (col 7) | ≈ 3.3V · ≈ 3.3V or lower |
| ON, DC volts | VBUS (col 1) without / with the ID bridge | ≈ 0V / ≈ 5V |
| Adapter in the laptop | adapter TXD ↔ GND | ≈ 3.3V (5V means STOP) |
| Cut cable alone | 4 wires ↔ 4 socket contacts | red, white, green, black in a row; red ↔ black no beep |

## 7 · Troubleshooting

| Symptom | Try |
|---|---|
| No text in picocom | Swap TX/RX. Check GND. `ls /dev/ttyUSB*` |
| Garbage characters | Baud must be 115200; loose GND |
| No login prompt after plugging the stick (stock firmware) | VBUS ≈ 5V? ID bridge to GND? D+/D− swapped? Stick has a real partition? Try the known-good image |
| Login incorrect | Serial in capitals, from the sticker under the dustbin; recompute |
| Robot hotspot gone | Hold the two outer buttons until it talks (it turns off 30 min after boot) |
| curl / wget fails | Laptop on the robot's hotspot? IP 192.168.5.x? File server running? Right port? |
| tmux "no server running" | The session ended (adapter unplugged). Start it again |

## 8 · Lessons learned

- **Track robot-side and adapter-side wires separately.** Watch out for wires of the same colour doing different jobs (here: three white wires, for adapter RXD, robot D− and cable D−).
- **The USB stick needs a partition,** not just a partition table. The trigger looks for `/dev/sdX1`.
- **`/tmp` is RAM.** Delete the firmware tarball right after unpacking and the backup right after uploading.
- **The robot has no internet during setup**, so serve Valetudo from the laptop with httpbridge instead of downloading it on the robot.
- **Valetudo doesn't change sensor behaviour.** It replaces the cloud and the app. Cliff detection runs in the robot's software and its MCU firmware; see [`../mcu/`](../mcu/) for that.

## 9 · Sources

- Valetudo Dreame guide: https://valetudo.cloud/pages/installation/dreame/
- Valetudo supported robots: https://valetudo.cloud/pages/general/supported-robots/
- valetudo-helper-httpbridge: https://github.com/Hypfer/valetudo-helper-httpbridge
- Valetudo releases: https://github.com/Hypfer/Valetudo/releases
- DustBuilder: https://builder.dontvacuum.me
