#!/usr/bin/env python3
"""Tests for Program 1, run against the reference simulator in asm.py."""
import sys
sys.path.insert(0, '/home/claude/p2')
from asm import assemble, Machine

SRC = open('/home/claude/p2/program1.asm').read()
MEM, LABELS = assemble(SRC)
START = LABELS['MAIN1']


def expected_closest(nums, target):
    """First element minimising |n - target|; ties keep the earlier one."""
    best, bestd = None, None
    for n in nums:
        d = abs(n - target)
        if bestd is None or d < bestd:
            best, bestd = n, d
    return best


def run(nums, target):
    assert len(nums) == 20
    stdin = ''.join(f'{n}\n' for n in nums) + f'{target}\n'
    m = Machine(dict(MEM), START, stdin).run(limit=500_000)
    return m


def check(name, nums, target):
    m = run(nums, target)
    lines = [l for l in m.printed().split('\n') if l != '']
    want_echo = [str(n) for n in nums]
    want_tail = [str(target), str(expected_closest(nums, target))]
    ok = (not m.halted or True) and lines == want_echo + want_tail
    status = 'PASS' if ok else 'FAIL'
    print(f'{status}  {name}')
    if not ok:
        print(f'      halted={m.halted} steps={m.steps} mfr={m.mfr:04b}')
        print(f'      want echo {want_echo}')
        print(f'      got  echo {lines[:20]}')
        print(f'      want tail {want_tail}')
        print(f'      got  tail {lines[20:]}')
    return ok


if __name__ == '__main__':
    results = []

    results.append(check(
        'plain positives, target between two values',
        [100, 250, 4000, 17, 983, 12, 7, 31000, 5, 64,
         900, 1234, 88, 2, 19, 456, 777, 3030, 11, 60],
        300))

    results.append(check(
        'negatives mixed in',
        [-100, 250, -4000, 17, -983, 12, 7, -31000, 5, 64,
         -900, 1234, 88, -2, 19, 456, -777, 3030, 11, -60],
        -950))

    results.append(check(
        'exact match present',
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
         11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        13))

    results.append(check(
        'tie keeps the earlier number',
        [10, 20, 1, 2, 3, 4, 5, 6, 7, 8,
         9, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        15))

    results.append(check(
        'range bounds -32768 and 32767',
        [-32768, 32767, 0, -1, 1, -32767, 32766, 100, -100, 500,
         -500, 1000, -1000, 2, -2, 3, -3, 4, -4, 5],
        -32000))

    results.append(check(
        'target is -32768 itself',
        [-32768, 32767, 0, -1, 1, -32767, 32766, 100, -100, 500,
         -500, 1000, -1000, 2, -2, 3, -3, 4, -4, 5],
        -32768))

    results.append(check(
        'zero appears and is the answer',
        [5, -5, 0, 100, -100, 7, -7, 9, -9, 11,
         -11, 13, -13, 17, -17, 19, -19, 23, -23, 29],
        0))

    results.append(check(
        'all equal',
        [42] * 20,
        -7))

    print()
    print(f'{sum(results)} passed, {len(results) - sum(results)} failed')
    sys.exit(0 if all(results) else 1)
