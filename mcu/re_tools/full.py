import sys,capstone
d=open(sys.argv[1],'rb').read(); B=0x08004000
md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB|capstone.CS_MODE_MCLASS)
o=0x130; end=0x22000
out=open(sys.argv[2],'w')
while o<end:
    n=0
    for ins in md.disasm(d[o:min(o+4096,end)],B+o):
        out.write('%08x: %-10s %s %s\n'%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str)); o+=ins.size; n+=1
    if o<end and n==0 or (o<end and not any(True for _ in md.disasm(d[o:o+4],B+o))):
        out.write('%08x: .short %04x\n'%(B+o,int.from_bytes(d[o:o+2],'little'))); o+=2
