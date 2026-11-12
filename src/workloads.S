#include "workload.h"

.section .text.workload_run, "ax"
.balign 64
.global workload_run
.type workload_run, %function
workload_run:
  mov x16, x0
  msr nzcv, x1
  mov x0, #0
  mov x1, #0x0f0f0f0f0f0f0f0f
  mov x2, #0x3333333333333333
  mov x3, #0xaaaaaaaaaaaaaaaa
  dsb sy
  ic iallu
  dsb sy
  mrs x4, sctlr_el2
  orr x4, x4, #(1 << 12)
  msr sctlr_el2, x4
  isb
  br x16
.size workload_run, . - workload_run

.section .rodata.workloads, "a"

.macro begin_workload name
  .balign 64
  .global workload_\name
  .type workload_\name, %object
workload_\name:
.endm

.macro end_workload name
  .if (. - workload_\name) != WORKLOAD_INSTRUCTIONS * 4
    .error "Incorrect workload instruction count"
  .endif
  b workload_\name
  .size workload_\name, . - workload_\name
.endm

.macro unary_workload name, instruction
  begin_workload \name
  .rept WORKLOAD_INSTRUCTIONS
    \instruction
  .endr
  end_workload \name
.endm

unary_workload idle, wfe
unary_workload nop, nop

begin_workload mov
  .rept WORKLOAD_INSTRUCTIONS / 2
    mov x0, x2
    mov x0, x3
  .endr
end_workload mov

begin_workload movz
  .rept WORKLOAD_INSTRUCTIONS / 2
    movz x0, #0x3333
    movz x0, #0xaaaa
  .endr
end_workload movz

.macro binary_workload name
  begin_workload \name
  .rept WORKLOAD_INSTRUCTIONS / 2
    \name x0, x1, x2
    \name x0, x1, x3
  .endr
  end_workload \name
.endm

binary_workload add
binary_workload adds
binary_workload sub
binary_workload and
binary_workload orr
binary_workload eor

.macro shift_workload name
  begin_workload \name
  .rept WORKLOAD_INSTRUCTIONS / 2
    \name x0, x2, #1
    \name x0, x3, #1
  .endr
  end_workload \name
.endm

shift_workload lsl
shift_workload lsr

.macro branch_workload name, instruction
  begin_workload \name
  .rept WORKLOAD_INSTRUCTIONS / 4
    \instruction 2f
1:      \instruction 3f
2:      \instruction 1b
3:      \instruction 4f
4:
  .endr
  end_workload \name
.endm

branch_workload b, b
branch_workload beq, b.eq
branch_workload bne, b.ne

.section .note.GNU-stack, "", %progbits
