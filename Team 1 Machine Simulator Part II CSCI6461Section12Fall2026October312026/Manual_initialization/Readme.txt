# CSCI 6461 Section 12, Fall 2026 - Project 2

Team 1 - Robel Berhe
Instructor: Professor Morris Lancaster

## Contents

    CSCI6461Simulator.html      the revised simulator
    test files/program1.asm     Program 1 source
    test files/program1.load    Program 1 assembled, ready to load
    screenshots/                four test samples, full console transcripts
    tools/                      reference assembler, simulator and test suites
    Project2_Report.docx        report on the corrections and the program

## Running Program 1

1. Open `CSCI6461Simulator.html` in a browser.
2. Press `Load`, choose `test files/program1.load`.
3. Set PC to `0300` and press the adjacent `LD`.
4. Type 20 integers into Line Input, pressing Enter after each, then a 21st
   number to search for. Input may be typed ahead of the run or while it runs.
5. Press `Run`. The console prints the 20 numbers, then the number entered and
   the one of the 20 closest to it.

Values may be anywhere in -32768..32767, positive or negative.

## Simulator corrections

Three corrections were made, each marked in the source with a comment:

* Run executed one instruction per 120 ms tick. It now runs a burst per tick,
  yielding to the browser between bursts so keyboard input still arrives.
* `resetMachine()` called `resetCache()` once per memory word instead of once.
* The program file dialog's `accept` list omitted `.load`.

## Verification

`tools/asm.py` is a C6461 assembler and reference simulator mirroring the HTML
simulator's semantics. It is validated against the Part 0 test programs.
`tools/test_program1.py` runs Program 1 against it over eight hand-written
cases and 300 randomised trials. `tools/browser_test.js` drives the real
simulator through its user interface with Playwright and produced the
screenshots.

    python3 tools/test_program1.py
    node tools/browser_test.js
