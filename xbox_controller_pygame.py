import pygame
import time
import os

# --- Pygame Configuration ---
# Center the Pygame window (optional, needed for event processing)
# os.environ['SDL_VIDEO_CENTERED'] = '1' # Not strictly necessary for console output
pygame.init()
pygame.joystick.init()

print("Monitoreando señales del control de Xbox (Ctrl+C para salir)")
print("Mueve los sticks y presiona botones para ver sus valores")

# --- Controller Detection ---
joystick_count = pygame.joystick.get_count()
if joystick_count == 0:
    print("No se detectaron controles. Verifica la conexión.")
    pygame.quit()
    exit()

# Use the first detected joystick
joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"Usando control: {joystick.get_name()}")
print(f"Número de ejes: {joystick.get_numaxes()}")
print(f"Número de botones: {joystick.get_numbuttons()}")
print(f"Número de hats (D-Pads): {joystick.get_numhats()}")


# --- Mappings (Adjust based on your controller/OS if needed) ---

# Map Pygame button indices to descriptive names
# This mapping might vary slightly depending on the controller model and OS
# Adjusted based on user feedback for specific Linux mapping:
button_map = {
    0: "A (Verde)",
    1: "B (Rojo)",
    2: "Back/Select",     # Was original X (2)
    3: "X (Azul)",        # Was original Y (3)
    4: "Y (Amarillo)",    # Was original LB (4)
    5: "Start",           # Was original RB (5)
    6: "LB",              # Was original Back/Select (6)
    7: "RB",              # Was original Start (7)
    # 8: "Xbox/Guide",    # Original index 8, now mapped to 12
    # Indices 9 is likely unused
    10: "Botón Vista",     # New mapping for index 10
    11: "Botón Menú",      # New mapping for index 11
    12: "Botón Xbox",      # New mapping for index 12 (replaces old index 8)
    13: "Stick Izq (presionado)",
    14: "Stick Der (presionado)",
    15: "Botón Compartir", # New mapping for index 15
}

# Map Pygame axis indices - Check these with your specific controller
# Common Linux mapping:
AXIS_LEFT_STICK_X = 0
AXIS_LEFT_STICK_Y = 1
# --- Potential Swap ---
# Original: AXIS_RIGHT_STICK_X = 3, AXIS_RIGHT_STICK_Y = 4
# Original: AXIS_LEFT_TRIGGER = 2, AXIS_RIGHT_TRIGGER = 5
# Swapped values:
AXIS_RIGHT_STICK_X = 2 # Often 2 or 3
AXIS_RIGHT_STICK_Y = 3 # Often 3 or 4
# Triggers might be axes 2 and 5. Value ranges from -1.0 (released) to 1.0 (fully pressed).
AXIS_LEFT_TRIGGER = 5  # Often 5 or 2
AXIS_RIGHT_TRIGGER = 4 # Often 4 or 5
# --- End Potential Swap ---

# Map Pygame hat indices (usually only one hat, index 0 for D-Pad)
HAT_DPAD = 0

# --- Thresholds ---
STICK_THRESHOLD = 0.2  # Threshold for considering stick movement
TRIGGER_THRESHOLD = 0.1 # Threshold for triggers (after normalization)

# --- State Variables ---
last_buttons_pressed = set()
last_dpad_state = (0, 0)
last_left_stick = (0.0, 0.0)
last_right_stick = (0.0, 0.0)
last_triggers = (0.0, 0.0) # Normalized 0.0 to 1.0

# --- Helper Function ---
def normalize_trigger(value):
    """Converts pygame trigger axis value (-1 to 1) to 0.0 to 1.0"""
    return (value + 1.0) / 2.0

# --- Main Loop ---
try:
    while True:
        # Process Pygame events to keep it responsive and update joystick state
        for event in pygame.event.get():
            if event.type == pygame.QUIT: # Allows quitting if a window were open
                raise KeyboardInterrupt
            # Optional: Handle joystick connection/disconnection events if needed
            # if event.type == pygame.JOYDEVICEADDED:
            #     print("Control conectado.")
            #     joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
            #     joystick = joysticks[0] # Re-assign if needed
            #     joystick.init()
            # if event.type == pygame.JOYDEVICEREMOVED:
            #     print("Control desconectado.")
            #     pygame.quit()
            #     exit()


        # --- Read Current State ---
        # Buttons
        current_buttons_pressed = set()
        # Adjust range if necessary, but typically get_numbuttons() is correct
        for i in range(joystick.get_numbuttons()):
            if joystick.get_button(i):
                # Use the updated map, provide default if index not in map
                current_buttons_pressed.add(button_map.get(i, f"Botón {i}"))

        # D-Pad (Hat)
        current_dpad_state = (0, 0)
        if joystick.get_numhats() > HAT_DPAD:
             current_dpad_state = joystick.get_hat(HAT_DPAD)

        # Sticks
        # Ensure axis indices are valid before reading
        current_left_stick = (0.0, 0.0)
        if joystick.get_numaxes() > AXIS_LEFT_STICK_X:
            current_left_stick_x = joystick.get_axis(AXIS_LEFT_STICK_X)
        else:
            current_left_stick_x = 0.0
        if joystick.get_numaxes() > AXIS_LEFT_STICK_Y:
            # Invert Y axis value
            current_left_stick_y = joystick.get_axis(AXIS_LEFT_STICK_Y) * -1.0
        else:
            current_left_stick_y = 0.0
        current_left_stick = (current_left_stick_x, current_left_stick_y)


        current_right_stick = (0.0, 0.0)
        if joystick.get_numaxes() > AXIS_RIGHT_STICK_X:
            current_right_stick_x = joystick.get_axis(AXIS_RIGHT_STICK_X)
        else:
            current_right_stick_x = 0.0
        if joystick.get_numaxes() > AXIS_RIGHT_STICK_Y:
            # Invert Y axis value
            current_right_stick_y = joystick.get_axis(AXIS_RIGHT_STICK_Y) * -1.0
        else:
            current_right_stick_y = 0.0
        current_right_stick = (current_right_stick_x, current_right_stick_y)

        # Triggers
        current_triggers = (0.0, 0.0)
        left_trigger_val = 0.0
        right_trigger_val = 0.0
        if joystick.get_numaxes() > AXIS_LEFT_TRIGGER:
            # Pygame triggers often rest at -1.0, normalize to 0.0 -> 1.0
            left_trigger_val = normalize_trigger(joystick.get_axis(AXIS_LEFT_TRIGGER))
        if joystick.get_numaxes() > AXIS_RIGHT_TRIGGER:
            right_trigger_val = normalize_trigger(joystick.get_axis(AXIS_RIGHT_TRIGGER))
        current_triggers = (left_trigger_val, right_trigger_val)


        # --- Check for Changes and Print ---

        # Buttons
        buttons_changed = last_buttons_pressed != current_buttons_pressed
        if buttons_changed:
            added = current_buttons_pressed - last_buttons_pressed
            removed = last_buttons_pressed - current_buttons_pressed
            if added:
                print(f"Botones presionados: {', '.join(sorted(list(added)))}")
            if removed:
                print(f"Botones soltados: {', '.join(sorted(list(removed)))}")
            last_buttons_pressed = current_buttons_pressed

        # D-Pad
        dpad_changed = last_dpad_state != current_dpad_state
        if dpad_changed:
            print(f"D-Pad: X={current_dpad_state[0]}, Y={current_dpad_state[1]}") # Y is often inverted (-1 up, 1 down)
            last_dpad_state = current_dpad_state

        # Left Stick
        left_stick_changed = last_left_stick != current_left_stick
        # Check if the current state is "active" (moved beyond threshold)
        left_stick_active = abs(current_left_stick[0]) > STICK_THRESHOLD or abs(current_left_stick[1]) > STICK_THRESHOLD

        if left_stick_changed:
            if left_stick_active:
                # Print only if changed AND active
                print(f"Stick Izq: X={current_left_stick[0]:>6.3f}, Y={current_left_stick[1]:>6.3f}")
            # Always update the last state if it changed, regardless of printing
            last_left_stick = current_left_stick


        # Right Stick
        right_stick_changed = last_right_stick != current_right_stick
        # Check if the current state is "active" (moved beyond threshold)
        right_stick_active = abs(current_right_stick[0]) > STICK_THRESHOLD or abs(current_right_stick[1]) > STICK_THRESHOLD

        if right_stick_changed:
            if right_stick_active:
                # Print only if changed AND active
                print(f"Stick Der: X={current_right_stick[0]:>6.3f}, Y={current_right_stick[1]:>6.3f}")
            # Always update the last state if it changed, regardless of printing
            last_right_stick = current_right_stick

        # Triggers
        triggers_changed = last_triggers != current_triggers
        # Check if the current state is "active" (pressed beyond threshold)
        triggers_active = current_triggers[0] > TRIGGER_THRESHOLD or current_triggers[1] > TRIGGER_THRESHOLD

        if triggers_changed:
            if triggers_active:
                 # Print only if changed AND active
                 print(f"Gatillos: LT={current_triggers[0]:>5.3f}, RT={current_triggers[1]:>5.3f}")
            # Always update the last state if it changed, regardless of printing
            last_triggers = current_triggers


        # Small delay to prevent high CPU usage
        time.sleep(0.02)

except KeyboardInterrupt:
    print("\nSaliendo del monitor.")
finally:
    pygame.quit() # Clean up pygame resources