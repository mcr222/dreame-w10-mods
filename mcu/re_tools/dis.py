import sys,capstone
d=open(sys.argv[1],'rb').read(); B=0x08004000
a=int(sys.argv[2],16); n=int(sys.argv[3])
md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB|capstone.CS_MODE_MCLASS)
o=a-B; c=0
while c<n and o<len(d):
    got=False
    for ins in md.disasm(d[o:o+64],B+o):
        print('%08x: %-12s %s %s'%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str)); o+=ins.size; c+=1; got=True
        if c>=n: break
    if not got: print('%08x: .word %08x'%(B+o,int.from_bytes(d[o:o+4],'little'))); o+=2; c+=1
