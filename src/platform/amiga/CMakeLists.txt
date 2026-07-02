pico_generate_pio_header(amigahid-pico ${CMAKE_CURRENT_LIST_DIR}/keyboard.pio)

target_sources(amigahid-pico PRIVATE keyboard_serial_io.c quad_mouse.c)

# real amiga keyboard input on controller port 2 (PORT2_ROLE=KEYBOARD)
if (PORT2_ROLE STREQUAL "KEYBOARD")
	pico_generate_pio_header(amigahid-pico ${CMAKE_CURRENT_LIST_DIR}/keyboard_recv.pio)
	target_sources(amigahid-pico PRIVATE keyboard_recv.c)
endif ()
