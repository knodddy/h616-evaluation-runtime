#ifndef H616_UART_H
#define H616_UART_H

void uart_init(void);
int uart_getc(void);
void uart_puts(const char *text);
void uart_drain(void);
void uart_disable(void);

#endif
