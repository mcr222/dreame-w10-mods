#!/usr/bin/env python3
"""Disable the dViewL (front-left) cliff sensor in the Dreame W10 MCU firmware.

Firmware: GD32F303, CodeVer 0.5.4, GitVer eb4c7dca, md5 a01f7d9c1fad6c18ccf409edb188e601.
Image is linked at 0x08004000 (bootloader below), so file offset = addr - 0x08004000.

Cliff value per sensor = 0x1000 + adc[ch] - ambient[ch]; >= 0xF0A (0xF3C in some modes)
means "no floor" -> cliff. L is computed at 0x0801B4A8:
    ldr  r1,=0x20002D48 ; ldrh r1,[r1,#0x12]   (L raw)
    add  r1,#0x1000
    ldr  r2,=0x20002D48 ; ldrh r2,[r2]         (L ambient)
    subs/sxth ; strh r1,[0x20000AEC+8]          (dViewL)

Variants:
  mirror - read ML's channel (raw +0x14, ambient +2) so L just follows ML.
  off    - store 0 into dViewL, so L never reports a cliff.
  leftoff - store 0 into dViewL, dViewML and dViewBL (whole left side, read in the same ADC
           pass), for testing whether the left sensors are the only fault. No left-side fall
           protection: test away from stairs and flash stock back afterwards.
  alloff - store 0 into all six values (both passes), so no cliff sensor ever reports a
           cliff. Reference build only (not flashed): the robot has no fall protection at all.
           Needs the extra argument --no-fall-protection.

Each variant also replaces the MCU git version "eb4c7dcaC" (4 copies, same length) with a
marker, so the running build can be checked from the robot's Linux shell:
    avacmd sys '{"type":"system", "sys_get":"get_mcu_git_version"}'

Usage: patch_cliff.py {mirror|off|leftoff|alloff} <in mcu.bin> <out dir> [--no-fall-protection]
Writes <out dir>/mcu.bin and <out dir>/mcu_md5sum.
"""
import hashlib
import os
import sys

BASE = 0x08004000
ORIG_MD5 = "a01f7d9c1fad6c18ccf409edb188e601"
MD5_PATH = ("/home/ujenkins/jenkins_data/workspace/platform_workspace/"
            "p2027_release发布_release/build/configs/../../build/output/images/mcu.bin")

PATCHES = {
    "mirror": [
        (0x0801B4AA, "498a", "898a"),  # ldrh r1,[r1,#0x12] -> ldrh r1,[r1,#0x14]
        (0x0801B4B2, "1288", "5288"),  # ldrh r2,[r2]       -> ldrh r2,[r2,#2]
    ],
    "off": [
        # ldr/ldrh/add.w/ldr/ldrh/subs/sxth -> movs r1,#0 ; nop x7
        (0x0801B4A8, "1b49498a01f58051194a1288891a09b2", "0021" + "00bf" * 7),
    ],
    "leftoff": [
        (0x0801B4A8, "1b49498a01f58051194a1288891a09b2", "0021" + "00bf" * 7),  # L
        (0x0801B4BC, "1649898a01f58051144a5288891a09b2", "0021" + "00bf" * 7),  # ML
        (0x0801B4D0, "1149898b01f580510f4a5289891a09b2", "0021" + "00bf" * 7),  # BL
    ],
}
PATCHES["alloff"] = PATCHES["leftoff"] + [
    (0x0801B462, "2d49498b01f580512b4a1289891a09b2", "0021" + "00bf" * 7),  # BR
    (0x0801B476, "2849c98a01f58051264a9288891a09b2", "0021" + "00bf" * 7),  # MR
    (0x0801B48A, "2349098b01f58051214ad288891a09b2", "0021" + "00bf" * 7),  # R
]

GIT_VERSION_ADDRS = (0x08008038, 0x08008528, 0x0800C184, 0x0801FD50)
MARKERS = {"mirror": b"CLIFFLMIR", "off": b"CLIFFLOFF", "leftoff": b"CLIFFLEFT",
           "alloff": b"CLIFFNONE"}
for _v, _m in MARKERS.items():
    PATCHES[_v] += [(a, b"eb4c7dcaC".hex(), _m.hex()) for a in GIT_VERSION_ADDRS]


def main():
    if len(sys.argv) not in (4, 5) or sys.argv[1] not in PATCHES:
        sys.exit(__doc__)
    variant, src, out_dir = sys.argv[1:4]
    if variant == "alloff" and sys.argv[4:] != ["--no-fall-protection"]:
        sys.exit("alloff disables every cliff sensor; add --no-fall-protection to build it")
    data = bytearray(open(src, "rb").read())
    if hashlib.md5(data).hexdigest() != ORIG_MD5:
        sys.exit("input is not the expected original mcu.bin (md5 mismatch)")

    for addr, old, new in PATCHES[variant]:
        off = addr - BASE
        old, new = bytes.fromhex(old), bytes.fromhex(new)
        assert len(old) == len(new)
        if data[off:off + len(old)] != old:
            sys.exit("unexpected bytes at 0x%08X" % addr)
        data[off:off + len(new)] = new

    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "mcu.bin"), "wb").write(data)
    md5 = hashlib.md5(data).hexdigest()
    with open(os.path.join(out_dir, "mcu_md5sum"), "w") as f:
        f.write("%s  %s\n" % (md5, MD5_PATH))
    print("%s: %s  %s" % (variant, md5, os.path.join(out_dir, "mcu.bin")))


if __name__ == "__main__":
    main()
