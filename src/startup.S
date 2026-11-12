.section .text.boot, "ax"
.balign 16
.global _start
.type _start, %function
_start:
    b .Lentry
    .balign 8
    .quad _start
    .quad __payload_size
.Lentry:
    msr daifset, #0xf
    mrs x0, CurrentEL
    cmp x0, #0x8
    b.ne .Lpark

    // Only the primary core owns this stack and initializes shared memory.
    mrs x0, mpidr_el1
    and x0, x0, #0xff
    cbnz x0, .Lpark

    // The loader must disable the MMU and both caches before entry.
    mrs x0, sctlr_el2
    tbnz x0, #0, .Lpark
    tbnz x0, #2, .Lpark
    tbnz x0, #12, .Lpark

    msr spsel, #1
    ldr x0, =__stack_top
    mov sp, x0
    adr x0, .Lvectors
    msr vbar_el2, x0
    isb

    ldr x0, =__bss_start
    ldr x1, =__bss_end
.Lclear_bss:
    cmp x0, x1
    b.hs .Lenter_c
    str xzr, [x0], #8
    b .Lclear_bss
.Lenter_c:
    bl runtime_main
.Lpark:
    wfe
    b .Lpark
.size _start, . - _start

.section .text.vectors, "ax"
.balign 2048
.Lvectors:
    .rept 16
    b .Lpark
    .balign 128
    .endr

.section .note.GNU-stack, "", %progbits
