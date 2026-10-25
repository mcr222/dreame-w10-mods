import sys,struct
d=open(sys.argv[1],'rb').read(); B=0x08004000
src=0x8026434-B; size=0x1ad8; out=bytearray()
i=src
while len(out)<size:
    b=d[i]; i+=1
    n=b&7
    if n==0: n=d[i]; i+=1
    m=b>>4
    if m==0: m=d[i]; i+=1
    out+=d[i:i+n-1]; i+=n-1
    if b&8:
        off=d[i]; i+=1; s=len(out)-off
        for k in range(m+2): out.append(out[s+k])
    else:
        out+=bytes(m)
open(sys.argv[2],'wb').write(out[:size])
print('decompressed',len(out),'consumed until',hex(B+i))
