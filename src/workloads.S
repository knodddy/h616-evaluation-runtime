.section .text.workload_idle, "ax"
.balign 16
.global workload_idle
.type workload_idle, %function
workload_idle:
    wfe
    b workload_idle
.size workload_idle, . - workload_idle

.section .note.GNU-stack, "", %progbits
