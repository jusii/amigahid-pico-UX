pico_generate_pio_header(amigahid-pico ${CMAKE_CURRENT_LIST_DIR}/keyboard.pio)
# real amiga keyboard input; compiled out by HAS_KBD_IN on boards without one
pico_generate_pio_header(amigahid-pico ${CMAKE_CURRENT_LIST_DIR}/keyboard_recv.pio)

target_sources(amigahid-pico PRIVATE keyboard_serial_io.c keyboard_recv.c quad_mouse.c)
