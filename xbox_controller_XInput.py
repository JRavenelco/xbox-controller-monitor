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
    
    while True:
        state = XInput.get_state(controller_index)
        
        # Obtener valores actuales
        current_buttons = XInput.get_button_values(state)
        current_triggers = XInput.get_trigger_values(state)
        current_left_stick = XInput.get_thumb_values(state)[0]
        current_right_stick = XInput.get_thumb_values(state)[1]
        
        # Verificar si hay cambios significativos
        buttons_changed = last_buttons != current_buttons if last_buttons else True
        
        left_stick_moved = (
            abs(current_left_stick[0]) > STICK_THRESHOLD or 
            abs(current_left_stick[1]) > STICK_THRESHOLD or
            abs(current_left_stick[0] - last_left_stick[0]) > STICK_THRESHOLD or
            abs(current_left_stick[1] - last_left_stick[1]) > STICK_THRESHOLD
        )
        
        right_stick_moved = (
            abs(current_right_stick[0]) > STICK_THRESHOLD or 
            abs(current_right_stick[1]) > STICK_THRESHOLD or
            abs(current_right_stick[0] - last_right_stick[0]) > STICK_THRESHOLD or
            abs(current_right_stick[1] - last_right_stick[1]) > STICK_THRESHOLD
        )
        
        triggers_changed = (
            abs(current_triggers[0]) > TRIGGER_THRESHOLD or
            abs(current_triggers[1]) > TRIGGER_THRESHOLD or
            abs(current_triggers[0] - last_triggers[0]) > TRIGGER_THRESHOLD or
            abs(current_triggers[1] - last_triggers[1]) > TRIGGER_THRESHOLD
        )
        
        if buttons_changed or left_stick_moved or right_stick_moved or triggers_changed:
            # Mostrar botones presionados
            buttons_pressed = False
            for button_name, friendly_name in button_names.items():
                if current_buttons[button_name]:
                    if not buttons_pressed:
                        print("\nBotones presionados:")
                        buttons_pressed = True
                    print(f"  {friendly_name}")
            
            # Mostrar valores de los sticks analógicos y gatillos solo si hay cambios
            if triggers_changed:
                print(f"Gatillos: L={current_triggers[0]:.2f}, R={current_triggers[1]:.2f}")
            
            if left_stick_moved:
                print(f"Stick izquierdo: X={current_left_stick[0]:.2f}, Y={current_left_stick[1]:.2f}")
                
            if right_stick_moved:
                print(f"Stick derecho: X={current_right_stick[0]:.2f}, Y={current_right_stick[1]:.2f}")
            
            # Actualizar valores anteriores
            last_buttons = current_buttons.copy()
            last_triggers = current_triggers
            last_left_stick = current_left_stick
            last_right_stick = current_right_stick
            last_state = state
            
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\nPrograma terminado")
except Exception as e:
    print(f"Error: {e}")
