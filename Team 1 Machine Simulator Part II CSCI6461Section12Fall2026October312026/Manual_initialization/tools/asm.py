#!/usr/bin/env python3
"""C6461 assembler + reference simulator.

Mirrors the semantics of the team's CSCI6461Simulator.html exactly, including
the 5-bit address field, MLT/DVD register-pair behaviour, and the non-blocking
IN instruction. Used to debug Program 1 before running it in the browser.

Syntax follows the course assembler as established in Part 0:
    LOC n                   set assembly location
    Label:  Data value      a data word (value may be a number or a label)
    Label:  MNEM a,b,c[,1]  instruction; trailing ,1 sets the indirect bit
    ; comment
"""
import re
import sys

# opcode table (octal values), with operand shape
STANDARD = 'std'      # r, ix, addr [, i]
IMMED    = 'imm'      # r, immed
SHIFT    = 'shf'      # r, count, al, lr
REGREG   = 'rr'       # rx, ry
IO       = 'io'       # r, devid
TRAPF    = 'trap'     # code
NOARG    = 'noarg'
JUMPADDR = 'jaddr'    # ix, addr [, i]   (JMA/JSR take no r field)
INDEXOP  = 'xop'      # x, addr [, i]    (LDX/STX: register goes in the ix field)

OPS = {
    'HLT':  (0o00, NOARG),
    'LDR':  (0o01, STANDARD),
    'STR':  (0o02, STANDARD),
    'LDA':  (0o03, STANDARD),
    'AMR':  (0o04, STANDARD),
    'SMR':  (0o05, STANDARD),
    'AIR':  (0o06, IMMED),
    'SIR':  (0o07, IMMED),
    'JZ':   (0o10, STANDARD),
    'JNE':  (0o11, STANDARD),
    'JCC':  (0o12, STANDARD),
    'JMA':  (0o13, JUMPADDR),
    'JSR':  (0o14, JUMPADDR),
    'RFS':  (0o15, TRAPF),
    'SOB':  (0o16, STANDARD),
    'JGE':  (0o17, STANDARD),
    'TRAP': (0o30, TRAPF),
    'SRC':  (0o31, SHIFT),
    'RRC':  (0o32, SHIFT),
    'LDX':  (0o41, INDEXOP),
    'STX':  (0o42, INDEXOP),
    'IN':   (0o61, IO),
    'OUT':  (0o62, IO),
    'CHK':  (0o63, IO),
    'MLT':  (0o70, REGREG),
    'DVD':  (0o71, REGREG),
    'TRR':  (0o72, REGREG),
    'AND':  (0o73, REGREG),
    'ORR':  (0o74, REGREG),
    'NOT':  (0o75, REGREG),
}


def assemble(text):
    """Two-pass assembler. Returns {address: word} and the label table."""
    raw = []
    for lineno, line in enumerate(text.split('\n'), 1):
        line = line.split(';')[0].rstrip()
        if not line.strip():
            continue
        raw.append((lineno, line))

    # ---- pass 1: locations and labels ----
    labels, items, loc = {}, [], 0
    for lineno, line in raw:
        m = re.match(r'^(\w+):\s*(.*)$', line.strip())
        label, rest = (m.group(1), m.group(2).strip()) if m else (None, line.strip())

        if rest.upper().startswith('LOC'):
            if label:
                raise SyntaxError(f'line {lineno}: label on LOC')
            loc = int(rest.split()[1], 0)
            continue

        if label:
            if label in labels:
                raise SyntaxError(f'line {lineno}: duplicate label {label}')
            labels[label] = loc

        if not rest:
            continue
        items.append((lineno, loc, rest))
        loc += 1

    # ---- pass 2: encode ----
    def val(tok):
        tok = tok.strip()
        # Allow Label-Base so index-relative jump offsets can be written
        # symbolically. The emitted .load and the resolved listing contain
        # plain numbers, so the output stays portable.
        if '-' in tok[1:]:
            a, b = tok.rsplit('-', 1)
            return val(a) - val(b)
        if tok in labels:
            return labels[tok]
        return int(tok, 0)

    mem = {}
    for lineno, loc, rest in items:
        parts = rest.split(None, 1)
        mnem = parts[0].upper()
        args = [a.strip() for a in parts[1].split(',')] if len(parts) > 1 else []

        if mnem == 'DATA':
            mem[loc] = val(args[0]) & 0xFFFF
            continue

        if mnem not in OPS:
            raise SyntaxError(f'line {lineno}: unknown mnemonic {mnem}')
        op, shape = OPS[mnem]

        def chk(v, bits, what):
            if not (0 <= v < (1 << bits)):
                raise SyntaxError(
                    f'line {lineno}: {what}={v} does not fit in {bits} bits ({rest})')
            return v

        if shape == NOARG:
            word = op << 10
        elif shape == STANDARD:
            r = chk(val(args[0]), 2, 'r')
            ix = chk(val(args[1]), 2, 'ix') if len(args) > 1 else 0
            addr = chk(val(args[2]), 5, 'addr') if len(args) > 2 else 0
            i = chk(val(args[3]), 1, 'i') if len(args) > 3 else 0
            word = (op << 10) | (r << 8) | (ix << 6) | (i << 5) | addr
        elif shape in (JUMPADDR, INDEXOP):
            ix = chk(val(args[0]), 2, 'ix')
            a = chk(val(args[1]), 5, 'addr') if len(args) > 1 else 0
            i = chk(val(args[2]), 1, 'i') if len(args) > 2 else 0
            word = (op << 10) | (ix << 6) | (i << 5) | a
        elif shape == IMMED:
            r = chk(val(args[0]), 2, 'r')
            imm = chk(val(args[1]), 5, 'immed')
            word = (op << 10) | (r << 8) | imm
        elif shape == SHIFT:
            r = chk(val(args[0]), 2, 'r')
            count = chk(val(args[1]), 4, 'count')
            al = chk(val(args[2]), 1, 'al') if len(args) > 2 else 0
            lr = chk(val(args[3]), 1, 'lr') if len(args) > 3 else 0
            word = (op << 10) | (r << 8) | (al << 7) | (lr << 6) | count
        elif shape == REGREG:
            rx = chk(val(args[0]), 2, 'rx')
            ry = chk(val(args[1]), 2, 'ry') if len(args) > 1 else 0
            word = (op << 10) | (rx << 8) | (ry << 6)
        elif shape == IO:
            r = chk(val(args[0]), 2, 'r')
            dev = chk(val(args[1]), 5, 'devid')
            word = (op << 10) | (r << 8) | dev
        elif shape == TRAPF:
            code = chk(val(args[0]), 4, 'code')
            word = (op << 10) | code
        else:
            raise AssertionError(shape)

        if loc in mem:
            raise SyntaxError(f'line {lineno}: address {loc} written twice')
        mem[loc] = word & 0xFFFF

    return mem, labels


def to_load(mem):
    return '\n'.join(f'{a:06o} {mem[a]:06o}' for a in sorted(mem)) + '\n'


# --------------------------------------------------------------------------
# reference simulator


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def u16(v):
    return v & 0xFFFF


class Machine:
    def __init__(self, mem, pc, stdin=''):
        self.m = [0] * 2048
        for a, w in mem.items():
            self.m[a] = w
        self.gpr = [0, 0, 0, 0]
        self.ixr = [0, 0, 0, 0]          # index 0 unused
        self.pc = pc
        self.cc = 0                      # bit 3-i is flag i
        self.mfr = 0
        self.halted = False
        self.inq = [ord(c) for c in stdin]
        self.out = []
        self.steps = 0

    # condition codes, numbered as the ISA numbers them (flag 0 = MSB)
    def set_cc(self, flag, on):
        mask = 1 << (3 - flag)
        self.cc = (self.cc | mask) if on else (self.cc & ~mask)

    def get_cc(self, flag):
        return bool(self.cc & (1 << (3 - flag)))

    def fault(self, mfr):
        self.mfr = mfr
        self.halted = True

    def ea(self, r, ix, i, addr, indexed=True):
        e = addr & 0x1F
        if indexed and ix:
            e = (e + self.ixr[ix]) & 0xFFF
        if e >= 2048:
            self.fault(0b1000)
            return None
        if i:
            e = self.m[e] & 0xFFF
            if e >= 2048:
                self.fault(0b1000)
                return None
        return e

    def step(self):
        if self.halted:
            return
        self.steps += 1
        instr = self.m[self.pc]
        self.pc = (self.pc + 1) & 0xFFF
        op = (instr >> 10) & 0x3F
        r = (instr >> 8) & 3
        ix = (instr >> 6) & 3
        i = (instr >> 5) & 1
        addr = instr & 0x1F
        rx, ry = r, ix
        al = (instr >> 7) & 1
        lr = (instr >> 6) & 1
        count = instr & 0xF
        dev = instr & 0x1F
        code = instr & 0xF

        if op == 0o00:
            self.halted = True
        elif op == 0o01:
            e = self.ea(r, ix, i, addr)
            if e is not None:
                self.gpr[r] = self.m[e]
        elif op == 0o02:
            e = self.ea(r, ix, i, addr)
            if e is not None:
                self.m[e] = self.gpr[r]
        elif op == 0o03:
            e = self.ea(r, ix, i, addr)
            if e is not None:
                self.gpr[r] = e
        elif op == 0o04:
            e = self.ea(r, ix, i, addr)
            if e is not None:
                res = s16(self.gpr[r]) + s16(self.m[e])
                self.arith_cc(res)
                self.gpr[r] = u16(res)
        elif op == 0o05:
            e = self.ea(r, ix, i, addr)
            if e is not None:
                res = s16(self.gpr[r]) - s16(self.m[e])
                self.arith_cc(res)
                self.gpr[r] = u16(res)
        elif op == 0o06:
            res = s16(self.gpr[r]) + addr
            self.arith_cc(res)
            self.gpr[r] = u16(res)
        elif op == 0o07:
            res = s16(self.gpr[r]) - addr
            self.arith_cc(res)
            self.gpr[r] = u16(res)
        elif op == 0o10:
            e = self.ea(r, ix, i, addr)
            if e is not None and self.gpr[r] == 0:
                self.pc = e
        elif op == 0o11:
            e = self.ea(r, ix, i, addr)
            if e is not None and self.gpr[r] != 0:
                self.pc = e
        elif op == 0o12:
            e = self.ea(r, ix, i, addr)
            if e is not None and self.get_cc(r):
                self.pc = e
        elif op == 0o13:
            e = self.ea(r, ix, i, addr)
            if e is not None:
                self.pc = e
        elif op == 0o14:
            e = self.ea(r, ix, i, addr)
            if e is not None:
                self.gpr[3] = self.pc
                self.pc = e
        elif op == 0o15:
            self.gpr[0] = code
            self.pc = self.gpr[3] & 0xFFF
        elif op == 0o16:
            res = s16(self.gpr[r]) - 1
            self.gpr[r] = u16(res)
            e = self.ea(r, ix, i, addr)
            if e is not None and res > 0:
                self.pc = e
        elif op == 0o17:
            e = self.ea(r, ix, i, addr)
            if e is not None and s16(self.gpr[r]) >= 0:
                self.pc = e
        elif op == 0o41:
            e = self.ea(r, ix, i, addr, indexed=False)
            if e is not None:
                if not 1 <= ix <= 3:
                    self.fault(0b0100)
                else:
                    self.ixr[ix] = self.m[e]
        elif op == 0o42:
            e = self.ea(r, ix, i, addr, indexed=False)
            if e is not None:
                if not 1 <= ix <= 3:
                    self.fault(0b0100)
                else:
                    self.m[e] = self.ixr[ix]
        elif op == 0o31:
            v = self.gpr[r]
            if count:
                if lr == 1:
                    v = (v << count) & 0xFFFF
                else:
                    v = (s16(v) >> count) & 0xFFFF if al == 0 else (v >> count)
            self.gpr[r] = v & 0xFFFF
        elif op == 0o32:
            v = self.gpr[r]
            if count:
                if lr == 1:
                    v = ((v << count) | (v >> (16 - count))) & 0xFFFF
                else:
                    v = ((v >> count) | (v << (16 - count))) & 0xFFFF
            self.gpr[r] = v
        elif op == 0o61:
            if dev not in (0, 2):
                self.fault(0b0100)
            else:
                self.gpr[r] = (self.inq.pop(0) if self.inq else 0) & 0xFF
        elif op == 0o62:
            if dev != 1:
                self.fault(0b0100)
            else:
                self.out.append(chr(self.gpr[r] & 0xFF))
        elif op == 0o63:
            if dev in (0, 2):
                self.gpr[r] = 1 if self.inq else 0
            elif dev == 1:
                self.gpr[r] = 1
            else:
                self.gpr[r] = 0
        elif op == 0o70:
            if rx not in (0, 2) or ry not in (0, 2):
                self.fault(0b0100)
            else:
                prod = s16(self.gpr[rx]) * s16(self.gpr[ry])
                un = prod & 0xFFFFFFFF
                self.gpr[rx] = (un >> 16) & 0xFFFF
                self.gpr[rx + 1] = un & 0xFFFF
                self.set_cc(0, prod > 0x7FFFFFFF or prod < -0x80000000)
        elif op == 0o71:
            if rx not in (0, 2) or ry not in (0, 2):
                self.fault(0b0100)
            else:
                d = s16(self.gpr[ry])
                if d == 0:
                    self.set_cc(2, True)
                else:
                    n = s16(self.gpr[rx])
                    q = int(n / d)                 # truncate toward zero
                    self.gpr[rx] = u16(q)
                    self.gpr[rx + 1] = u16(n - q * d)
                    self.set_cc(2, False)
        elif op == 0o72:
            self.set_cc(3, self.gpr[rx] == self.gpr[ry])
        elif op == 0o73:
            self.gpr[rx] &= self.gpr[ry]
        elif op == 0o74:
            self.gpr[rx] |= self.gpr[ry]
        elif op == 0o75:
            self.gpr[rx] = (~self.gpr[rx]) & 0xFFFF
        elif op == 0o30:
            self.halted = True           # not exercised by Program 1
        else:
            self.fault(0b0100)

    def arith_cc(self, res):
        self.set_cc(0, False)
        self.set_cc(1, False)
        self.set_cc(2, False)
        if res > 32767:
            self.set_cc(0, True)
        if res < -32768:
            self.set_cc(1, True)

    def run(self, limit=2_000_000):
        while not self.halted and self.steps < limit:
            self.step()
        return self

    def printed(self):
        return ''.join(self.out)


if __name__ == '__main__':
    src = open(sys.argv[1]).read()
    mem, labels = assemble(src)
    out = sys.argv[2] if len(sys.argv) > 2 else None
    if out:
        open(out, 'w').write(to_load(mem))
        print(f'wrote {out} ({len(mem)} words)')
    for name in sorted(labels, key=lambda k: labels[k]):
        print(f'  {name:12} {labels[name]:06o}  ({labels[name]})')
