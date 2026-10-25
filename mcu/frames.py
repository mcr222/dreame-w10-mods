import sys,struct,collections
raw=bytes.fromhex(open(sys.argv[1]).read().strip())
frames=[];cur=None;esc=False
for b in raw:
    if cur is None:
        if b==0x3c: cur=bytearray()
        continue
    if esc: cur.append(b); esc=False; continue
    if b==0x3f: esc=True; continue
    if b==0x3e: frames.append(bytes(cur)); cur=None; continue
    if b==0x3c: cur=bytearray(); continue
    cur.append(b)
by=collections.defaultdict(list)
for f in frames:
    if len(f)>=2: by[(f[0],len(f))].append(f)
for (t,l),fs in sorted(by.items()):
    f=fs[-1]
    print('type 0x%02x len %3d count %3d  %s'%(t,l,len(fs),f.hex(' ')[:150]))

print('--- type 0x00 status frames (payload = 0x20000F22..F28) ---')
c=collections.Counter(f[2:2+f[0]].hex(' ') for f in frames if len(f)>=2 and f[1]==0x00 and len(f)==f[0]+4)
for p,n in c.items():
    b=bytes.fromhex(p.replace(' ',''))
    bits=b[1]; s=[n for i,n in enumerate(['ML','L','R','MR','BL','BR']) if bits>>i&1]
    print(n,'x',p,' cliff byte=0x%02x'%bits, 'sensors reporting cliff:', s or 'none')
