from machine import Pin, UART

uart = UART(
    1,
    tx = Pin(8),
    rx = Pin(9),
    baudrate = 9600,
    bits = 8,
    stop = 2,
    parity = None,
    )