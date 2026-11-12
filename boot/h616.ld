OUTPUT_ARCH(aarch64)
ENTRY(_start)

MEMORY
{
    /* TF-A's default PRELOADED_BL33_BASE. */
    ram (rwx) : ORIGIN = 0x4a000000, LENGTH = 1M
}

PHDRS
{
    text PT_LOAD FLAGS(5);
    data PT_LOAD FLAGS(6);
}

SECTIONS
{
    .text : ALIGN(16)
    {
        KEEP(*(.text.boot))
        *(.text .text.*)
    } > ram :text

    .rodata : ALIGN(16)
    {
        *(.rodata .rodata.*)
        . = ALIGN(8);
    } > ram :text

    .data : ALIGN(8)
    {
        *(.data .data.*)
        . = ALIGN(8);
        __payload_size = ABSOLUTE(. - ORIGIN(ram));
    } > ram :data

    .dtb (NOLOAD) : ALIGN(8)
    {
        . += 64K;
    } > ram :data

    .bss (NOLOAD) : ALIGN(16)
    {
        __bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        . = ALIGN(16);
        __bss_end = .;
    } > ram :data

    .stack (NOLOAD) : ALIGN(16)
    {
        __stack_bottom = .;
        . += 16K;
        __stack_top = .;
    } > ram :data

    /DISCARD/ : { *(.comment .note.GNU-stack) }

    ASSERT(_start == ORIGIN(ram), "BL33 entry must be at the start of the raw binary")
}
