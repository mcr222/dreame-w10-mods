#!/bin/sh
# cliffmon.sh - runs ON THE ROBOT. Live per-sensor cliff bits from the MCU status frame.
# MCU->Linux frames on ttyS4: 3C [len][type][payload][crc16] 3E, 0x3F escapes the next byte.
# Type 0x00 payload byte 1 = cliff bits: b0 ML, b1 L, b2 R, b3 MR, b4 BL, b5 BR (1 = no floor).
# Frames are checked with the MCU's CRC16 (tables copied from 0x08024C31/0x08024D31), so
# frames spliced together while sharing the port with ava are dropped.
# Prints on every change and every 20th frame. Shares the port with ava, so it only sees part
# of the stream while ava runs. Stop with Ctrl-C.
stty -F /dev/ttyS4 115200 cs8 -parodd parenb -cstopb -echo raw
hexdump -v -e '1/1 "%02x\n"' /dev/ttyS4 | awk '
function t(tb, i) { return h(substr(tb, i*2+1, 2)) }
function bxor(a, b,   r, k) { r=0; for (k=1; k<256; k*=2) if ((int(a/k)%2) != (int(b/k)%2)) r+=k; return r }
function crcok(   hi, lo, i, k) { hi=255; lo=255; for (k=0; k<n-2; k++) { i=bxor(h(f[k]), hi); hi=bxor(t(TH, i), lo); lo=t(TL, i) }; return hi==h(f[n-1]) && lo==h(f[n-2]) }
function h(s) { return (index("0123456789abcdef", substr(s,1,1))-1)*16 + index("0123456789abcdef", substr(s,2,1))-1 }
BEGIN { TH="00c1814001c0804101c0804100c1814001c0804100c1814000c1814001c0804101c0804100c1814000c1814001c0804100c1814001c0804101c0804100c1814001c0804100c1814000c1814001c0804100c1814001c0804101c0804100c1814000c1814001c0804101c0804100c1814001c0804100c1814000c1814001c0804101c0804100c1814000c1814001c0804100c1814001c0804101c0804100c1814000c1814001c0804101c0804100c1814001c0804100c1814000c1814001c0804100c1814001c0804101c0804100c1814001c0804100c1814000c1814001c0804101c0804100c1814000c1814001c0804100c1814001c0804101c0804100c18140"; TL="00c0c101c30302c2c60607c705c5c404cc0c0dcd0fcfce0e0acacb0bc90908c8d81819d91bdbda1a1ededf1fdd1d1cdc14d4d515d71716d6d21213d311d1d010f03031f133f3f23236f6f737f53534f43cfcfd3dff3f3efefa3a3bfb39f9f83828e8e929eb2b2aeaee2e2fef2dedec2ce42425e527e7e62622e2e323e12120e0a06061a163a3a26266a6a767a56564a46cacad6daf6f6eaeaa6a6bab69a9a86878b8b979bb7b7ababe7e7fbf7dbdbc7cb47475b577b7b67672b2b373b17170b0509091519353529296565797559594549c5c5d9d5f9f9e5e5a9a9b5b99595898884849894b8b8a4a4e8e8f4f8d4d4c8c44848545874746868242438341818040"
  inf=0; esc=0; n=0; last=-1; cnt=0; split("ML L R MR BL BR", nm, " ") }
{
  b=$1
  if (!inf) { if (b=="3c") { inf=1; n=0; esc=0 }; next }
  if (esc) { f[n++]=b; esc=0; next }
  if (b=="3f") { esc=1; next }
  if (b=="3c") { n=0; next }
  if (b=="3e") {
    inf=0
    if (n==11 && f[0]=="07" && f[1]=="00" && crcok()) {
      v=h(f[3]); cnt++
      if (v!=last || cnt%20==0) {
        s=""; p=1; for (i=0;i<6;i++) { s = s sprintf("%s=%d ", nm[i+1], int(v/p)%2); p*=2 }
        printf "cliff 0x%02x  %s%s\n", v, s, (v!=last ? "<- changed" : "")
        fflush(); last=v
      }
    }
    next
  }
  f[n++]=b
}'
