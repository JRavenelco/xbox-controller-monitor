import XInput
import time

print("Monitoreando señales del control de Xbox (Ctrl+C para salir)")
print("Mueve los sticks y presiona botones para ver sus valores")

# Mapeo de botones para mejor comprensión
button_names = {
    "DPAD_UP": "D-Pad Arriba",
    "DPAD_DOWN": "D-Pad Abajo",
    "DPAD_LEFT": "D-Pad Izquierda", 
    "DPAD_RIGHT": "D-Pad Derecha",
    "START": "Start",
    "BACK": "Back/Select",
    "LEFT_THUMB": "Stick Izq (presionado)",
    "RIGHT_THUMB": "Stick Der (presionado)",
    "LEFT_SHOULDER": "LB",
    "RIGHT_SHOULDER": "RB",
    "A": "A (Verde)",
    "B": "B (Rojo)", 
    "X": "X (Azul)",
    "Y": "Y (Amarillo)"
}

# Umbrales para detectar movimiento
STICK_THRESHOLD = 0.1  # Umbral para considerar movimiento en sticks
TRIGGER_THRESHOLD = 0.1  # Umbral para gatillos

try:
    # Verificar controles conectados
    connected = XInput.get_connected()
    if not any(connected):
        print("No se detectaron controles de Xbox. Verifica la conexión Bluetooth.")
        exit()
    
    print(f"Controles conectados: {connected}")
    
    # Identificar el primer control conectado
    controller_index = connected.index(True)
    print(f"Usando control #{controller_index}")
    
    last_state = None
    last_buttons = {}
    last_left_stick = (0.0, 0.0)
    last_right_stick = (0.0, 0.0)
    last_triggers = (0.0, 0.0)
    # Track previous active state
    was_left_stick_active = False
    was_right_stick_active = False
    was_triggers_active = False

    while True:
        state = XInput.get_state(controller_index)
        
        # Obtener valores actuales
        current_buttons = XInput.get_button_values(state)
        current_triggers = XInput.get_trigger_values(state)
        current_left_stick = XInput.get_thumb_values(state)[0]
        current_right_stick = XInput.get_thumb_values(state)[1]
        
        # --- Check for Changes and Print ---

        # Buttons
        buttons_changed = last_buttons != current_buttons if last_buttons else True
        if buttons_changed:
            pressed_now = {name: friendly for name, friendly in button_names.items() if current_buttons[name]}
            released_now = {name: friendly for name, friendly in button_names.items() if last_buttons.get(name) and not current_buttons[name]}

            if pressed_now:
                 # Print newly pressed buttons
                 newly_pressed = {name: friendly for name, friendly in pressed_now.items() if not last_buttons.get(name)}
                 if newly_pressed:
                     print(f"Botones presionados: {', '.join(newly_pressed.values())}")

            if released_now:
                 print(f"Botones soltados: {', '.join(released_now.values())}")

            last_buttons = current_buttons.copy() # Update last state for buttons

        # Triggers
        triggers_changed = last_triggers != current_triggers
        current_triggers_active = abs(current_triggers[0]) > TRIGGER_THRESHOLD or abs(current_triggers[1]) > TRIGGER_THRESHOLD

        if triggers_changed:
            if current_triggers_active:
                print(f"Gatillos: L={current_triggers[0]:.2f}, R={current_triggers[1]:.2f}")
                was_triggers_active = True
            elif was_triggers_active: # Print return-to-zero only if previously active
                # Print explicit zero state when returning to inactive
                print(f"Gatillos: L={0.0:.2f}, R={0.0:.2f}")
                was_triggers_active = False
            last_triggers = current_triggers # Update last state for triggers

        # Left Stick
        left_stick_changed = last_left_stick != current_left_stick
        current_left_stick_active = abs(current_left_stick[0]) > STICK_THRESHOLD or abs(current_left_stick[1]) > STICK_THRESHOLD

        if left_stick_changed:
            if current_left_stick_active:
                print(f"Stick izquierdo: X={current_left_stick[0]:.2f}, Y={current_left_stick[1]:.2f}")
                was_left_stick_active = True
            elif was_left_stick_active: # Print return-to-zero only if previously active
                # Print explicit zero state when returning to inactive
                print(f"Stick izquierdo: X={0.0:.2f}, Y={0.0:.2f}")
                was_left_stick_active = False
            last_left_stick = current_left_stick # Update last state for left stick

        # Right Stick
        right_stick_changed = last_right_stick != current_right_stick
        current_right_stick_active = abs(current_right_stick[0]) > STICK_THRESHOLD or abs(current_right_stick[1]) > STICK_THRESHOLD

        if right_stick_changed:
            if current_right_stick_active:
                print(f"Stick derecho: X={current_right_stick[0]:.2f}, Y={current_right_stick[1]:.2f}")
                was_right_stick_active = True
            elif was_right_stick_active: # Print return-to-zero only if previously active
                 # Print explicit zero state when returning to inactive
                print(f"Stick derecho: X={0.0:.2f}, Y={0.0:.2f}")
                was_right_stick_active = False
            last_right_stick = current_right_stick # Update last state for right stick

        # Update overall last state if needed elsewhere (currently not used after individual updates)
        last_state = state

        time.sleep(0.05)
except KeyboardInterrupt:
    print("\nPrograma terminado")
except Exception as e:
    print(f"Error: {e}")
