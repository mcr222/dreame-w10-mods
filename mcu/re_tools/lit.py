import sys,struct
d=open(sys.argv[1],'rb').read(); B=0x08004000
lo,hi=int(sys.argv[2],16),int(sys.argv[3],16)
lits={}
for i in range(0,len(d)-3,4):
    v=struct.unpack_from('<I',d,i)[0]
    if lo<=v<hi: lits[i]=v
# find pc-relative loads
for o in range(0,0x22000,2):
    h=struct.unpack_from('<H',d,o)[0]
    if h>>11==0b01001:
        t=((o+4)&~3)+(h&0xff)*4
        if t in lits: print('%08x ldr r%d,=%08x'%(B+o,(h>>8)&7,lits[t]))
    if h==0xf8df:
        h2=struct.unpack_from('<H',d,o+2)[0]; t=((o+4)&~3)+(h2&0xfff)
        if t in lits: print('%08x ldr.w r%d,=%08x'%(B+o,h2>>12,lits[t]))
