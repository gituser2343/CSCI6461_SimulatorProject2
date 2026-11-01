; ===========================================================================
; CSCI 6461 Section 12, Fall 2026 - Project 2, Program 1
; Robel Berhe
;
; Reads 20 signed integers from the keyboard, echoes them to the console
; printer, reads a 21st number, and prints the one of the 20 that is closest
; to it.  Numbers span -32768..32767.  Characters are read one at a time,
; validated as digits, and assembled into an integer; output integers are
; produced by repeated division by ten.
;
; ---------------------------------------------------------------------------
; WHY THE PROGRAM IS SHAPED THIS WAY
;
; The address field of an instruction is five bits, so a direct effective
; address can only name locations 0-31.  Every jump target beyond 31 must
; therefore come through an index register or an indirect pointer held in
; low memory.  The program uses that discipline consistently:
;
;   X3  globals base, set once to 0100 and never changed.  Every global is
;       addressed as offset(X3), e.g. LDR 0,3,1 loads ACC.
;   X2  base of the routine currently executing, reloaded from its low-memory
;       pointer on entry.  All local jumps are offset(X2).
;   X1  unused, left free for inspection at the front panel.
;
; Because each routine addresses its own code through X2, a routine must fit
; in a 32-word window.  Long operations are therefore split into several
; short routines chained by indirect JMA through the pointer table at 6-23.
;
; R3 is the link register: JSR writes the return address there and RFS
; returns through it.  READNUM and PRINTNUM never call anything, so R3 never
; needs saving; their continuations are reached by JMA, which leaves R3 alone.
; ===========================================================================


; --------------------------------------------------------------------------
; Pointer table.  These must live at 0-31 so that indirect jumps and LDX can
; reach them with a direct effective address.
; --------------------------------------------------------------------------
LOC 6
PGLOB:   Data 64          ; 6:  0100 - globals base
PARR:    Data 128         ; 7:  0200 - base of the 20-number array
PMAIN1:  Data MAIN1       ; 8
PMAIN2:  Data MAIN2       ; 9
PMAIN3:  Data MAIN3       ; 10
PRDNUM:  Data READNUM     ; 11
PPRNUM:  Data PRINTNUM    ; 12
PRDLOOP: Data RDLOOP      ; 13
PRDDONE: Data RDDONE      ; 14
PPRDIG:  Data PRDIG       ; 15
PPRNL:   Data PRNL        ; 16
PPREMIT: Data PREMIT      ; 17
PDIG:    Data 85          ; 18: 0125 - address of DIG[0] (globals offset 21)
DIGP:    Data 0           ; 19: moving digit-buffer pointer
PMAIN4:  Data MAIN4       ; 20
ARRCUR:  Data 0           ; 21: array cursor, used indirectly
PSEARCH: Data SEARCH      ; 22


; --------------------------------------------------------------------------
; Globals at 0100, addressed as offset(X3).
; --------------------------------------------------------------------------
LOC 64
G_N:     Data 20          ;  0: how many numbers to read
G_ACC:   Data 0           ;  1: integer being assembled / last read
G_NEG:   Data 0           ;  2: 1 if the number being read is negative
G_CH:    Data 0           ;  3: current input character
G_TEN:   Data 10          ;  4: the radix
G_ASC0:  Data 48          ;  5: ASCII '0'
G_ASCMI: Data 45          ;  6: ASCII '-'
G_T1:    Data 0           ;  7: scratch - candidate value
G_T2:    Data 0           ;  8: scratch
G_T3:    Data 0           ;  9: scratch - difference
G_TARG:  Data 0           ; 10: the number the user is searching for
G_BEST:  Data 0           ; 11: closest value found so far
G_BESTD: Data 0           ; 12: its absolute difference, -1 before any seen
G_CNT:   Data 0           ; 13: loop counter
G_VAL:   Data 0           ; 14: value PRINTNUM is to print
G_MAXD:  Data 32767       ; 15: largest biased difference, the search sentinel
G_NLCH:  Data 10          ; 16: newline
G_SPCH:  Data 32          ; 17: space
G_SP18:  Data 0           ; 18: spare
G_DIFF:  Data 0           ; 19: biased absolute difference for this candidate
G_BIAS:  Data 32768       ; 20: 0100000 - added to flip bit 15, see SEARCH
G_DIG:   Data 0           ; 21: digit buffer, 8 words
         Data 0           ; 22
         Data 0           ; 23
         Data 0           ; 24
         Data 0           ; 25
         Data 0           ; 26
         Data 0           ; 27
         Data 0           ; 28


; --------------------------------------------------------------------------
; MAIN1 - read 20 integers into the array at 0200.
; --------------------------------------------------------------------------
LOC 192
MAIN1:   LDX 3,6          ; X3 <- 0100, globals base, for the whole program
         LDR 0,0,7        ; R0 <- 0200
         STR 0,0,21       ; ARRCUR <- 0200
         LDR 0,3,0        ; R0 <- 20
         STR 0,3,13       ; CNT <- 20
M1L:     LDX 2,8          ; X2 <- MAIN1 (also restores it after the call below)
         JSR 0,11,1       ; READNUM: leaves the integer in ACC
         LDX 2,8          ; READNUM used X2 as its own base; restore ours
         LDR 0,3,1        ; R0 <- ACC
         STR 0,0,21,1     ; *ARRCUR <- R0
         LDR 0,0,21
         AIR 0,1
         STR 0,0,21       ; ARRCUR++
         LDR 0,3,13
         SIR 0,1
         STR 0,3,13       ; CNT--
         JNE 0,2,M1L-MAIN1
         JMA 0,9,1        ; -> MAIN2


; --------------------------------------------------------------------------
; MAIN2 - echo the 20 integers to the console printer.
; --------------------------------------------------------------------------
LOC 224
MAIN2:   LDR 0,0,7
         STR 0,0,21       ; ARRCUR <- 0200
         LDR 0,3,0
         STR 0,3,13       ; CNT <- 20
M2L:     LDX 2,9          ; X2 <- MAIN2
         LDR 0,0,21,1     ; R0 <- *ARRCUR
         STR 0,3,14       ; VAL <- R0
         JSR 0,12,1       ; PRINTNUM
         LDX 2,9          ; restore our base
         LDR 0,0,21
         AIR 0,1
         STR 0,0,21       ; ARRCUR++
         LDR 0,3,13
         SIR 0,1
         STR 0,3,13       ; CNT--
         JNE 0,2,M2L-MAIN2
         JMA 0,10,1       ; -> MAIN3


; --------------------------------------------------------------------------
; MAIN3 - read the target number and set up the search.
; --------------------------------------------------------------------------
LOC 256
MAIN3:   LDX 2,10         ; X2 <- MAIN3
         JSR 0,11,1       ; READNUM: target into ACC
         LDX 2,10
         LDR 0,3,1
         STR 0,3,10       ; TARGET <- ACC
         LDR 0,0,7
         STR 0,0,21       ; ARRCUR <- 0200
         LDR 0,3,0
         STR 0,3,13       ; CNT <- 20
         LDR 0,3,15
         STR 0,3,12       ; BESTD <- 32767, the largest biased difference
         LDR 0,0,21,1
         STR 0,3,11       ; BEST <- the first element.  The sentinel cannot be
                          ; beaten by a candidate whose own difference is the
                          ; maximum, which happens only when every element is
                          ; equidistant from the target; seeding BEST with the
                          ; first element gives a correct answer in that case.
         JMA 0,22,1       ; -> SEARCH


; --------------------------------------------------------------------------
; SEARCH - walk the array keeping the smallest absolute difference.
;
; THE DIFFERENCE DOES NOT FIT IN A SIGNED WORD.  Candidates and the target
; both span -32768..32767, so |candidate - target| reaches 65535, which needs
; seventeen bits.  Subtracting 0 from -32768 yields 32768, which wraps to
; -32768 and would make every later comparison nonsense.
;
; The magnitude does fit in sixteen UNSIGNED bits, so the loop keeps it as an
; unsigned pattern and compares with a bias.  Two steps make that work:
;
;   Sign of the true difference.  SMR records overflow in condition code 0 and
;   underflow in code 1.  Overflow means the true difference was positive and
;   too large; underflow means it was negative and too large.  When neither is
;   set the result fits and its own sign is the answer.
;
;   Comparison.  Adding 0100000 flips bit 15, mapping unsigned magnitudes
;   0..65535 onto signed -32768..32767 in the same order, so a plain signed
;   JGE then orders them correctly.  Every biased magnitude is negative, which
;   is why BESTD = 0 works as the "nothing seen yet" sentinel.
;
; A candidate replaces the incumbent only on a strictly smaller difference, so
; a tie keeps the earlier number.
; --------------------------------------------------------------------------
LOC 288
SEARCH:  LDX 2,22         ; X2 <- SEARCH
SL:      LDR 0,0,21,1     ; R0 <- *ARRCUR, the candidate
         STR 0,3,7        ; T1 <- candidate
         SMR 0,3,10       ; R0 <- candidate - TARGET, wrapped; sets CC 0 / CC 1
         STR 0,3,9        ; T3 <- the 16-bit pattern of the difference
         JCC 0,2,SPOS-SEARCH    ; overflow: true difference positive
         JCC 1,2,SNEG-SEARCH    ; underflow: true difference negative
         JGE 0,2,SPOS-SEARCH    ; fits: its own sign decides
SNEG:    LDA 0,0,0
         SMR 0,3,9        ; R0 <- 0 - pattern, exact modulo 65536
         STR 0,3,9
SPOS:    LDR 0,3,9        ; R0 <- |difference| as an unsigned pattern
         AMR 0,3,20       ; bias by 0100000 so signed JGE orders magnitudes
         STR 0,3,19       ; DIFF <- biased magnitude
         SMR 0,3,12       ; R0 <- DIFF - BESTD, which overflows just as readily
         JCC 0,2,SNEXT-SEARCH   ; overflow: DIFF > BESTD, keep the incumbent
         JCC 1,2,STAKE-SEARCH   ; underflow: DIFF < BESTD, take the candidate
         JGE 0,2,SNEXT-SEARCH   ; fits: not strictly smaller, keep incumbent
STAKE:   LDR 0,3,19
         STR 0,3,12       ; BESTD <- DIFF
         LDR 0,3,7
         STR 0,3,11       ; BEST <- candidate
SNEXT:   LDR 0,0,21
         AIR 0,1
         STR 0,0,21       ; ARRCUR++
         LDR 0,3,13
         SIR 0,1
         STR 0,3,13       ; CNT--
         JNE 0,2,SL-SEARCH
         JMA 0,20,1       ; -> MAIN4


; --------------------------------------------------------------------------
; MAIN4 - print the target and the closest value, then halt.
; --------------------------------------------------------------------------
LOC 320
MAIN4:   LDX 2,20         ; X2 <- MAIN4
         LDR 0,3,10
         STR 0,3,14       ; VAL <- TARGET
         JSR 0,12,1       ; PRINTNUM
         LDX 2,20
         LDR 0,3,11
         STR 0,3,14       ; VAL <- BEST
         JSR 0,12,1       ; PRINTNUM
         HLT


; ===========================================================================
; READNUM - assemble one signed integer from the keyboard into ACC.
;
; IN does not block: it returns zero when the input queue is empty, so every
; read is preceded by a CHK poll.  A program that simply issued IN would read
; a stream of zeros and appear to work.
; ===========================================================================
LOC 352
READNUM: LDX 2,11         ; X2 <- READNUM
         LDA 0,0,0
         STR 0,3,1        ; ACC <- 0
         STR 0,3,2        ; NEG <- 0
RDW1:    CHK 0,0          ; wait for the first character
         JZ 0,2,RDW1-READNUM
         IN 1,0           ; R1 <- character
         STR 1,3,3        ; CH <- R1
         LDR 0,3,3
         SMR 0,3,6        ; R0 <- CH - '-'
         JNE 0,2,RDGO-READNUM
         LDA 0,0,1
         STR 0,3,2        ; NEG <- 1
RDW2:    CHK 0,0          ; read the character after the sign
         JZ 0,2,RDW2-READNUM
         IN 1,0
RDGO:    STR 1,3,3        ; CH <- R1 (harmless repeat on the not-'-' path)
         JMA 0,13,1       ; -> RDLOOP


; --------------------------------------------------------------------------
; RDLOOP - accumulate digits until a non-digit arrives.
;
; MLT writes its 32-bit product as a register pair: MLT 0,2 leaves the high
; word in R0 and the low word in R1.  Multiplying ACC by ten therefore does
; not leave the result where ACC was read from, and the low word has to be
; stored and re-added.  This is the most error-prone line in the program.
; --------------------------------------------------------------------------
LOC 384
RDLOOP:  LDX 2,13         ; X2 <- RDLOOP
RDL1:    LDR 0,3,3        ; R0 <- CH
         SMR 0,3,5        ; R0 <- CH - '0'
         JGE 0,2,RDL2-RDLOOP
RDEND:   JMA 0,14,1       ; below '0': not a digit -> RDDONE
RDL2:    STR 0,3,7        ; T1 <- digit value
         SIR 0,10
         JGE 0,2,RDEND-RDLOOP   ; above '9': not a digit -> RDDONE
         LDR 0,3,1        ; R0 <- ACC
         LDR 2,3,4        ; R2 <- 10   (GPR R2; the index register X2 is separate)
         MLT 0,2          ; R0:R1 <- ACC * 10
         STR 1,3,8        ; T2 <- low word of ACC*10
         LDR 0,3,7        ; R0 <- digit
         AMR 0,3,8        ; R0 <- digit + ACC*10
         STR 0,3,1        ; ACC <- R0
RDW3:    CHK 0,0          ; next character
         JZ 0,2,RDW3-RDLOOP
         IN 1,0
         STR 1,3,3        ; CH <- R1
         JMA 2,RDL1-RDLOOP


; --------------------------------------------------------------------------
; RDDONE - apply the sign and return.  R3 still holds the caller's return
; address because READNUM and RDLOOP were reached by JMA, not JSR.
; --------------------------------------------------------------------------
LOC 416
RDDONE:  LDX 2,14         ; X2 <- RDDONE
         LDR 0,3,2        ; R0 <- NEG
         JZ 0,2,RDRET-RDDONE
         LDA 0,0,0
         SMR 0,3,1        ; R0 <- 0 - ACC
         STR 0,3,1        ; ACC <- -ACC
RDRET:   RFS 0


; ===========================================================================
; PRINTNUM - print the signed integer in VAL, followed by a newline.
;
; Negative values are NOT negated before digit extraction.  Negating -32768
; would overflow, and -32768 is inside the range the assignment requires.
; Instead the sign is printed and the digits are taken from the negative
; value, each remainder being negated as it is produced.
; ===========================================================================
LOC 448
PRINTNUM: LDX 2,12        ; X2 <- PRINTNUM
         LDR 0,3,14       ; R0 <- VAL
         JNE 0,2,PRSGN-PRINTNUM
         LDR 0,3,5        ; VAL is zero: print '0'
         OUT 0,1
         JMA 0,16,1       ; -> PRNL
PRSGN:   LDR 0,3,14
         JGE 0,2,PRDGO-PRINTNUM
         LDR 0,3,6        ; R0 <- '-'
         OUT 0,1
PRDGO:   JMA 0,15,1       ; -> PRDIG


; --------------------------------------------------------------------------
; PRDIG - extract decimal digits least-significant first into DIG.
; --------------------------------------------------------------------------
LOC 480
PRDIG:   LDX 2,15         ; X2 <- PRDIG
         LDR 0,0,18       ; R0 <- PDIG
         STR 0,0,19       ; DIGP <- PDIG
PD1:     LDR 0,3,14       ; R0 <- VAL
         LDR 2,3,4        ; R2 <- 10
         DVD 0,2          ; R0 <- VAL/10, R1 <- VAL%10
         STR 0,3,14       ; VAL <- quotient
         STR 1,3,9        ; T3 <- remainder, negative if VAL was negative
         LDA 0,0,0
         SMR 0,3,9        ; R0 <- -remainder
         JGE 0,2,PD2-PRDIG
         LDR 0,3,9        ; remainder was already positive
PD2:     AMR 0,3,5        ; R0 <- digit + '0'
         STR 0,0,19,1     ; *DIGP <- digit character
         LDR 0,0,19
         AIR 0,1
         STR 0,0,19       ; DIGP++
         LDR 0,3,14
         JNE 0,2,PD1-PRDIG
         JMA 0,17,1       ; -> PREMIT


; --------------------------------------------------------------------------
; PREMIT - walk the buffer back down, printing the digits in order.
; --------------------------------------------------------------------------
LOC 512
PREMIT:  LDX 2,17         ; X2 <- PREMIT
PE1:     LDR 0,0,19
         SIR 0,1
         STR 0,0,19       ; DIGP--
         LDR 0,0,19,1     ; R0 <- *DIGP
         OUT 0,1
         LDR 0,0,19
         SMR 0,0,18       ; R0 <- DIGP - PDIG
         JNE 0,2,PE1-PREMIT
         JMA 0,16,1       ; -> PRNL


; --------------------------------------------------------------------------
; PRNL - newline, then return to whoever called PRINTNUM.
; --------------------------------------------------------------------------
LOC 544
PRNL:    LDR 0,3,16       ; R0 <- newline
         OUT 0,1
         RFS 0
