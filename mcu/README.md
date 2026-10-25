# Dreame W10 MCU firmware: cliff sensor investigation and patch

Reverse-engineering notes for the Dreame W10 (p2027) motor controller firmware (`mcu.bin`), a patcher that makes the MCU ignore some or all cliff sensors, and tools to read the cliff sensors live from a rooted robot.

> ⚠️ **These patches remove fall protection.** A sensor that's patched out always reports "floor present", so the robot can drive off stairs or ledges on that side. Use them only to diagnose a confirmed sensor fault or as a temporary workaround where the robot can't reach any drop (or block drops with no-go zones). Supervise test runs, and flash stock back once the hardware is repaired. You need a rooted robot (see [`../docs/rooting-guide.md`](../docs/rooting-guide.md)).

## Background

The robot this was developed on raised **Valetudo error 2, "Cliff sensor dirty or robot on the verge of falling"**, even after the left cliff sensor was replaced. Reading the sensors live showed that **the whole left group (L, ML, BL) never saw the floor** on the stock firmware (stuck at "cliff" in 91/91 frames), while the right group (R, MR, BR) worked. The three left sensors are read in the same ADC pass (same emitter phase), so a shared cause (left emitter drive, supply, cable or connector, or the left sensor board) is far more likely than three separate failures.

With the `leftoff` build the robot boots with no error and the right-side sensors still react when it's lifted.

## Firmware facts

| Item | Value |
|---|---|
| File | `mcu.bin`, 141460 bytes, md5 `a01f7d9c1fad6c18ccf409edb188e601` (stock) |
| MCU | GD32F303ZET6 (Cortex-M4, STM32F103-compatible), FreeRTOS, Keil ARMCC, no symbols |
| Version | CodeVer `0.5.4`, GitVer `eb4c7dca`, built Mar 29 2022 |
| Load address | **0x08004000** (16 KB bootloader below it). File offset = address − 0x08004000 |
| RW data | LZ-compressed by Keil scatter-load: source 0x08026434 → 0x20000000, 0x1AD8 bytes, decompressor at 0x08004D4E |

### Cliff sensors in the firmware

Six sensor objects, 16 bytes each. The debug variable table (`{name ptr, RAM addr}` pairs around 0x08025490) points 8 bytes into each object.

| Sensor | Position | Object | Value var (+8) | Status bit |
|---|---|---|---|---|
| L  | front left  | 0x20000AEC | dViewL  0x20000AF4 | bit1 |
| ML | mid left    | 0x20000AFC | dViewML 0x20000B04 | bit0 |
| MR | mid right   | 0x20000B0C | dViewMR 0x20000B14 | bit3 |
| BL | back left   | 0x20000B1C | dViewBL 0x20000B24 | bit4 |
| BR | back right  | 0x20000B2C | dViewBR 0x20000B34 | bit5 |
| R  | front right | 0x20000B3C | dViewR  0x20000B44 | bit2 |

Object layout: `+0` pointer to debounce config, `+4` update function (0x0800905C, shared by all six), `+8` int16 value, `+0xC` cliff flag (1 = no floor).

- **Value** (0x0801B458): `value = 0x1000 + adc_raw − ambient`, from the DMA ADC buffer at 0x20002D48 (raw at +0x12…+0x1C, ambient at +0…+0xA). Computed in two alternating passes:
  - pass A (L, ML, BL): 0x0801B4A8 / 0x0801B4BC / 0x0801B4D0
  - pass B (MR, R, BR): 0x0801B462 / 0x0801B476 / 0x0801B48A
- **Decision** (0x0800905C): `cliff_raw = value >= 0xF0A` (0xF3C in an alternate mode). A sensor that sees the floor reads well below 3850; about 4096 means no reflection.
- **Debounce** (0x08008F4A): config `{limit, counter, stable, last}`; needs the same input twice in a row, then latches it into the flag at +0xC.
- **Status byte** (0x0801FFD0…0x080201CE): copies the six flags into byte 0x20000F23. It only runs while the enable byte 0x20000F2F is non-zero; otherwise it clears all six bits. **So while the robot is idle every bit reads 0, even when lifted.** The bits are live once the robot is active (for example, after starting a clean).

### MCU ↔ Linux link (USART0 ↔ `/dev/ttyS4`)

- 115200 baud, 8 data bits, **even parity**, 1 stop bit (same as the stock OTA script).
- Frame: `3C [len] [type] [payload × len] [crc_lo] [crc_hi] 3E`; the byte 0x3F escapes the next byte.
- CRC: MODBUS-style CRC-16, init 0xFFFF, table-driven (high/low tables at 0x08024C31 / 0x08024D31, routine 0x0800560C).
- **Type 0x00** (about 10 per second): payload = RAM 0x20000F22…0x20000F28; **payload byte 1 = cliff status byte** (bit0 ML, bit1 L, bit2 R, bit3 MR, bit4 BL, bit5 BR; 1 = cliff).
- The raw cliff values are not sent to Linux in the normal stream.

### MCU text debug console (USART1)

- **Not reachable from Linux.** USART1 is remapped to **PD5 (MCU TX, LQFP144 pin 119)** and **PD6 (MCU RX, pin 122)**, 115200, 3.3 V logic. Needs its own USB-UART adapter soldered to the board.
- Command table at 0x08025000 (`{name, handler}`): logup, remote, model, exit, log, ver, yaw, move, fan, lds, bit, roll, side, mop, coolfan, wheel, core, info, **get**, **set**, **mon**, save, add, mem, reset, shutdown, ota, cpu, echo1, unecho, time, state, **io**, ircode, led, calilds, caliimu, fct, calitof, fandry, rftest, bkp.
- Useful for reading raw values: `get dViewML`, `mon <period> dViewL dViewML …`, `io 1` (prints `drop-left/right`).
- A letter-command protocol (`C`/`Q`/`S`/`T` + letter; `Cm` returns all six values) also exists, but only on this console UART.
- Not tested yet: whether the console has commands to force cliff detection on or off without patching.

## The patches (`patch_cliff.py`)

### Get the stock `mcu.bin`

The patcher only accepts the exact stock file above (md5 `a01f7d9c…`). A rooted robot keeps a copy on its read-only rootfs at `/mcu.bin`; the DustBuilder firmware package contains the same file. Copy it to your PC, for example with `scp root@<robot-ip>:/mcu.bin .` or by uploading it to httpbridge (`curl -X POST http://IP:PORT/upload -F 'file=@/mcu.bin'`).

If your md5 differs, your robot runs a different MCU version and these offsets don't apply. The script refuses to patch it.

### Build

```bash
python3 patch_cliff.py leftoff mcu.bin build/leftoff
```

The script checks the input md5 and the exact original bytes at every patch site before writing, then writes `build/<variant>/mcu.bin` and a matching `mcu_md5sum`. Builds are reproducible, so your md5 must match the table below.

| Variant | Marker | md5 | Change |
|---|---|---|---|
| stock | `eb4c7dcaC` | a01f7d9c1fad6c18ccf409edb188e601 | none |
| mirror | `CLIFFLMIR` | cfd675fc1d20c450655220754599c426 | L reads ML's channel: 0x0801B4AA `498a`→`898a`, 0x0801B4B2 `1288`→`5288` |
| off | `CLIFFLOFF` | 0e6048edb52792d5fe90841e1741c623 | L value = 0 |
| **leftoff** | **`CLIFFLEFT`** | **8aff145c24b8168f5d2dd8072431163c** | L, ML and BL values = 0 |
| alloff (never flashed) | `CLIFFNONE` | 554e1822e57ae7e0c2b0eb613844c74d | all six values = 0 |

The "value = 0" patch replaces each sensor's 16-byte calculation (`ldr/ldrh/add.w/ldr/ldrh/subs/sxth`) with `movs r1,#0` + 7 × `nop`. The following `strh r1,[obj,#8]` is kept, so the sensor always reads "floor present":

| Sensor | Address | Original bytes | New bytes | Used by |
|---|---|---|---|---|
| L  | 0x0801B4A8 | `1b49498a01f58051194a1288891a09b2` | `0021` + `00bf`×7 | off, leftoff, alloff |
| ML | 0x0801B4BC | `1649898a01f58051144a5288891a09b2` | `0021` + `00bf`×7 | leftoff, alloff |
| BL | 0x0801B4D0 | `1149898b01f580510f4a5289891a09b2` | `0021` + `00bf`×7 | leftoff, alloff |
| BR | 0x0801B462 | `2d49498b01f580512b4a1289891a09b2` | `0021` + `00bf`×7 | alloff |
| MR | 0x0801B476 | `2849c98a01f58051264a9288891a09b2` | `0021` + `00bf`×7 | alloff |
| R  | 0x0801B48A | `2349098b01f58051214ad288891a09b2` | `0021` + `00bf`×7 | alloff |

Each variant also replaces the four copies of the git version `eb4c7dcaC` (0x08008038, 0x08008528, 0x0800C184, 0x0801FD50) with a same-length marker, so you can check which build is running:

```sh
avacmd sys '{"type":"system", "sys_get":"get_mcu_git_version"}'
```

(`get_fw_mcu` = 0.5.4 comes from `/etc/os-release`, not from the MCU, so it never changes.)

**`alloff`** leaves the robot with no way to detect any stairs or ledges. It exists only as a reference test of whether anything other than the cliff sensors raises error 2, and it has never been flashed. Building it needs an extra `--no-fall-protection` argument. If you ever try it: one floor, no reachable drops, supervised, and flash back right after.

## Flashing (from the robot's root shell)

The stock path is `install-mcufw.sh` → `avacmd ota … AVA_UNPACK_OK` → `ota_mcu_update.sh`. That script stops `ava`, waits for the bootloader's `C`, sends the file over ymodem on ttyS4, waits for `update_OK`, then checks `/tmp/update/only_update_mcu_mark`. **If the mark is missing, it also runs the full Linux update** (`ota_arm_update.sh`), which switches the boot slot.

1. Serve the file from the PC (time-limited), in the folder that holds the patched `mcu.bin`:
   ```bash
   timeout 60 python3 -m http.server 1337 --bind <PC_IP>
   ```
2. On the robot:
   ```sh
   rm -rf /tmp/update; mkdir -p /tmp/update
   wget -q http://<PC_IP>:1337/mcu.bin -O /tmp/update/mcu.bin
   md5sum /tmp/update/mcu.bin          # must match the table above
   ( while :; do [ -f /tmp/update/only_update_mcu_mark ] || echo 1 > /tmp/update/only_update_mcu_mark; sleep 1; done ) &
   avacmd ota '{"type": "ota", "cmd": "report_upgrade_status", "status": "AVA_UNPACK_OK", "result": "ok"}'
   ```
   The background loop keeps the "MCU only" mark in place (see gotcha 1).
3. The robot reboots after about 30 seconds. Then check that `fw_printenv boot_partition` is unchanged and that the git version marker is the one you expect.

**Rollback to stock:** same steps, but `cp /mcu.bin /tmp/update/mcu.bin` instead of the wget.

## Tools in this folder

| File | Runs on | Purpose |
|---|---|---|
| `patch_cliff.py` | PC | Builds the patched variants from the stock `mcu.bin` |
| `cliffmon.sh` | robot (copy to `/data/cliffmon.sh`) | Live, CRC-checked per-sensor cliff bits from the type 0x00 frame. Prints on change and every 20th frame. Ctrl-C to stop. Shares ttyS4 with `ava`, so don't run it during a clean. |
| `cap.sh` + `frames.py` | PC | Captures N seconds of the ttyS4 stream through a tmux session `w10` running picocom with a log file (`W10_LOG`, default `~/w10_serial.log`), then decodes it |
| `s4.hex` | — | Example capture (robot flat on the floor, ML + BL reporting cliff) |
| `re_tools/` | PC | Reverse-engineering helpers (need `pip install capstone`): `dis.py <bin> <hexaddr> <n>` disassemble, `full.py <bin> <out.asm>` whole-image listing, `lit.py <bin> <lo> <hi>` find code loading addresses in a range, `xref.py <bin> <string…>` pointer refs to strings, `decomp.py <bin> <out>` unpack the compressed RW data (0x20000000 image) |

## How this was found

1. **Identified the image.** Stock W10 MCU firmware; found the cliff ("drop") strings and the `dView*` variables.
2. **Base address.** The reset vector at file offset 0x1E0 showed the image is linked at 0x08004000. Found Keil's compressed RW data, wrote a decompressor, and recovered the variable table and the sensor objects with their shared update function.
3. **Decoded the cliff logic**: value, threshold, debounce and status byte, as above.
4. **First patch, `mirror`** (L follows ML). Flashed through the stock OTA scripts: `update_OK`, **but error 2 persisted.**
5. **Second patch, `off`** (L = 0), with the git version marker added. **Error 2 still persisted.**
6. **Reading sensors without extra wiring.** The text console is on USART1 (physical access only), so the ttyS4 stream was captured instead: frames are unsolicited, and the type 0x00 status frame carries per-sensor cliff bits.
7. **Live monitor `cliffmon.sh`.** The first version had no CRC check and showed impossible readings: two readers on one tty split the data and the decoder spliced frames together. With the firmware's CRC-16, spliced frames are dropped.
8. **Cover test on `off`:** R, MR and BR toggle correctly; ML and BL never reach 0.
9. **Cover test on stock** (to rule the patches out): L, ML and BL stuck at 1 in 91/91 frames, right side fine. **Conclusion: left sensor group fault, not firmware.**
10. **`leftoff`** (L, ML, BL = 0): lift test shows R/MR/BR → 1, left stays 0. Robot idle with no error after boot.

### Things that didn't help

- **`/data/Robot_Para.yaml` thresholds.** This factory calibration file has `IRCliff` values per sensor (here L was `850`, the rest `3700`). Setting L to `0` or `4095` changed nothing: error 2 still appeared as soon as the robot drove. The file is read at boot, but the cliff decision is made in the MCU. Back the file up before experimenting.
- **White paper over the faulty sensor window:** no change, because the whole left group was failing.
- **Logs:** `/data/log` and `/tmp/log` never mention the cliff sensors. The MCU keeps its own binary log at `/data/log/mculog.bin`.

## Testing results

| # | Firmware | Test | Result |
|---|---|---|---|
| 1 | mirror (unmarked) | normal run | error 2 |
| 2 | off `CLIFFLOFF` | normal run | error 2 |
| 3 | off | 3 s capture on dock, `ava` stopped | cliff byte 0x00 (idle) |
| 4 | off | 3 s capture on floor | 0x11 = ML + BL cliff (25 CRC-valid frames) |
| 5 | off | live monitor during clean start | 0x3D = every sensor except L "cliff" (robot lifted / starting) |
| 6 | off | cover test | R/MR/BR toggle; ML/BL never 0 |
| 7 | stock `eb4c7dcaC` | cover test | L/ML/BL = 1 in 91/91 frames; R 51×0, MR 47×0, BR 48×0 |
| 8 | leftoff `CLIFFLEFT` | lift test after power cycle | R/MR/BR → 1, left stays 0; Valetudo idle, no error |
| — | alloff `CLIFFNONE` | built and disassembly-checked only | not flashed |

## Gotchas

1. **Linux slot switch.** During the first flash, `only_update_mcu_mark` was gone when `ota_mcu_update.sh` checked it. The script then ran `ota_arm_update.sh`, which switched `boot_partition` boot1 → boot2. The other slot held the same rooted build, so no harm, but the guard loop in the flashing steps is there to prevent it.
2. **`pkill -f` can match its own shell** (the pattern is in its own command line). Use `timeout N` on the HTTP server instead.
3. **Stopping `ava`** (`killall -9 monitor.sh ava`) makes a watchdog reboot the robot a few minutes later. A reboot also clears `/tmp`, so keep helper scripts in `/data`.
4. **Two readers on ttyS4** (`ava` + a monitor) each get part of the stream; always check the CRC.
5. **Cliff bits read 0 while the robot is idle** (enable byte 0x20000F2F = 0). Test while the robot is active.

## Diagnosing your own robot

1. Copy `cliffmon.sh` to `/data`, start a clean with the robot on the floor, and watch which bits stay at 1.
2. Hardware checks: film the underside with a phone camera during a clean start to see whether the IR emitters glow; check the sensor cables and connectors; compare the supply at the left and right sensor connectors.
3. Only if a sensor is confirmed faulty and the area has no drops: build and flash the matching variant, and flash stock back after the repair.
