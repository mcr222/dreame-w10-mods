import sys,struct
d=open(sys.argv[1],'rb').read(); B=0x08004000
def cstr(o):
    e=d.index(b'\0',o); return d[o:e].decode('latin1')
for name in sys.argv[2:]:
    o=d.index(name.encode()+b'\0')
    while d[o-1]!=0: o=d.index(name.encode()+b'\0',o+1)
    a=B+o
    refs=[i for i in range(0,len(d)-3,4) if struct.unpack_from('<I',d,i)[0]==a]
    print(name,hex(a),'refs',[hex(B+r) for r in refs])
    for r in refs:
        w=struct.unpack_from('<8I',d,r-8)
        print('   ctx', ' '.join('%08x'%x for x in w))
