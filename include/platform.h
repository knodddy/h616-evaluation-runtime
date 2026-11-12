#ifndef H616_PLATFORM_H
#define H616_PLATFORM_H

#include <stdbool.h>

bool platform_init(void);
void platform_disconnect_grace(void);
void platform_quiet(void);
_Noreturn void platform_halt(void);

#endif
