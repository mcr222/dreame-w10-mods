# Dreame W10 (P2027): root, Valetudo and cliff sensor MCU patches

Notes and tools from rooting a Dreame W10 (`dreame.vacuum.p2027`) and tracking down a cliff sensor error.

| Folder | What |
|---|---|
| [`docs/rooting-guide.md`](docs/rooting-guide.md) | Step-by-step guide: wiring the debug port without a breakout PCB, getting a root shell over UART, installing the DustBuilder rooted firmware and setting up Valetudo |
| [`docs/wiring-checklist.html`](docs/wiring-checklist.html) | The same steps as a printable, tickable checklist with a colour pin map (open it in a browser) |
| [`mcu/`](mcu/) | Reverse-engineering notes for the W10 motor controller (MCU) firmware, a patcher that can ignore some or all cliff sensors, and tools to read the sensors live from the robot |

## ⚠️ Read this first

- **Rooting and flashing can brick your robot and will void your warranty.** Follow the official [Valetudo Dreame guide](https://valetudo.cloud/pages/installation/dreame/) as the source of truth; this repo adds concrete W10 details on top.
- **The MCU patches turn off fall protection.** A robot running a patched build can drive off stairs and ledges. They are meant for diagnosing a confirmed sensor fault or as a temporary workaround in a home with no drops, never as a general "fix" for cliff errors. Flash stock back once the hardware is repaired.
- Not affiliated with Dreame, Valetudo or DustBuilder.

## What's not in this repo

On purpose, and you shouldn't commit these either:

- **Firmware binaries** (`mcu.bin`, the DustBuilder firmware package, Valetudo). They're copyrighted by their authors. `patch_cliff.py` builds the patched MCU images from the stock `mcu.bin` on your own robot.
- **Anything tied to your robot**: the DustBuilder SSH key zip and PDF, the identity backup (`/mnt/private/ULI/factory`: serial, DID, key, MAC), and serial logs. The root password is derived from the serial number, so treat the serial as a secret too.

## License

[MIT](LICENSE) for the scripts and documentation in this repo. The license doesn't cover the firmware the scripts operate on, which belongs to Dreame.

## Credits

- [Valetudo](https://valetudo.cloud) by Hypfer, cloud-free control for robot vacuums
- [DustBuilder](https://builder.dontvacuum.me) by Dennis Giese, rooted firmware builds
- [valetudo-helper-httpbridge](https://github.com/Hypfer/valetudo-helper-httpbridge), the file server used during the install
