.section .text.workload_idle, "ax"
.balign 16
.global workload_idle
.type workload_idle, %function
workload_idle:
    // Bring-up placeholder; this is not a measurement workload.
    wfe
    b workload_idle
.size workload_idle, . - workload_idle

.section .note.GNU-stack, "", %progbits
