#!/bin/bash
# capture N seconds of MCU stream on the robot and decode locally
# needs the robot console in tmux session "w10" running picocom with --logfile $W10_LOG
L=${W10_LOG:-$HOME/w10_serial.log}; S=$(cd "$(dirname "$0")" && pwd); N=${1:-3}
S0=$(stat -c %s $L)
tmux send-keys -t w10 "stty -F /dev/ttyS4 115200 cs8 -parodd parenb -cstopb -echo raw; (cat /dev/ttyS4 > /tmp/s4.bin &) ; sleep $N; killall cat; echo ==\"\"=HEXSTART===; hexdump -v -e '32/1 \"%02x\" \"\\n\"' /tmp/s4.bin; echo ==\"\"=HEXEND===" Enter
for i in $(seq 1 $((N*2+120))); do grep -aq '^===HEXEND===' <(tail -c +$S0 $L | tr -d '\r') && break; sleep 0.5; done
tail -c +$S0 $L | tr -d '\r' | sed -n '/^===HEXSTART===/,/^===HEXEND===/p' | grep -aE '^[0-9a-f]+$' | tr -d '\n' > $S/s4.hex
echo "captured $(( $(wc -c < $S/s4.hex) / 2 )) bytes"
python3 -I $S/frames.py $S/s4.hex | sed -n '/^---/,$p'
