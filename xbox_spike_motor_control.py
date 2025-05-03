import pygame
import time
import os
import serial
import math

# --- Configuraciones ---
# Serial
SPIKE_SERIAL_PORT = '/dev/ttyACM0' # Ajusta si es necesario
SPIKE_BAUD_RATE = 115200
MOTOR_PORT_LETTER = 'A' # Puerto del motor en el Spike Hub

# Pygame / Xbox Controller
os.environ['SDL_VIDEODRIVER'] = 'dummy' # Para ejecución sin pantalla
AXIS_LEFT_TRIGGER = 5  # Ajusta según tu mapeo (a menudo 5 o 2 en Linux)
AXIS_RIGHT_TRIGGER = 4 # Ajusta según tu mapeo (a menudo 4 o 5 en Linux)
TRIGGER_THRESHOLD = 0.05 # Umbral mínimo para considerar un gatillo presionado (0.0 a 1.0)

# Motor Control
# Velocidades máximas típicas (grados/segundo): Medium=1110, Large=1050, Small=660
MAX_MOTOR_SPEED = 1000 # Ajusta según tu motor y preferencia
MOTOR_STOP_THRESHOLD = 0.02 # Porcentaje de MAX_MOTOR_SPEED por debajo del cual se considera 0
MOTOR_COMMAND_INTERVAL = 0.05 # Segundos - Intervalo mínimo entre comandos de velocidad al Spike
# ------------------------

# --- Inicialización Pygame ---
print("Inicializando Pygame...")
pygame.init()
pygame.joystick.init()
pygame.display.set_mode((1, 1)) # Necesario para el bucle de eventos

print("Detectando control...")
joystick_count = pygame.joystick.get_count()
if joystick_count == 0:
    print("Error: No se detectaron controles.")
    pygame.quit()
    exit()

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"Usando control: {joystick.get_name()}")
if joystick.get_numaxes() <= max(AXIS_LEFT_TRIGGER, AXIS_RIGHT_TRIGGER):
    print(f"Error: El control no tiene suficientes ejes ({joystick.get_numaxes()}) para los gatillos configurados (LT:{AXIS_LEFT_TRIGGER}, RT:{AXIS_RIGHT_TRIGGER}).")
    pygame.quit()
    exit()

# --- Inicialización Serial ---
print(f"Conectando al Spike Hub en {SPIKE_SERIAL_PORT}...")
try:
    spike_serial = serial.Serial(SPIKE_SERIAL_PORT, SPIKE_BAUD_RATE, timeout=1)
    time.sleep(2) # Dar tiempo al puerto serial para establecerse
    print("Conexión serial establecida.")
except serial.SerialException as e:
    print(f"Error al abrir el puerto serial: {e}")
    pygame.quit()
    exit()

def send_spike_command(command):
    """Envía un comando al Spike Hub a través de serial."""
    #print(f"Sending: {command}") # Descomenta para depurar
    try:
        spike_serial.write((command + '\r').encode())
        time.sleep(0.05) # Pequeña pausa después de enviar
    except serial.SerialException as e:
        print(f"Error al enviar comando serial: {e}")
        # Podrías intentar reconectar o salir aquí

# Enviar comandos iniciales al Spike Hub
print("Configurando Spike Hub (importando módulos)...")
send_spike_command('import motor')
send_spike_command('from hub import port')
print("Spike Hub listo.")

# --- Helper Function ---
def normalize_trigger(value):
    """Convierte valor de eje de gatillo Pygame (-1 a 1) a 0.0 a 1.0"""
    return (value + 1.0) / 2.0

# --- Variables de Estado ---
last_sent_velocity = 0
last_command_time = 0

# --- Bucle Principal ---
print("Iniciando bucle de control. Presiona Ctrl+C para salir.")
running = True
try:
    while running:
        # --- Procesar eventos de Pygame ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Podrías añadir manejo de botones aquí si quieres (ej. botón para salir)

        # --- Leer Gatillos ---
        current_time = time.time()
        left_trigger_raw = joystick.get_axis(AXIS_LEFT_TRIGGER)
        right_trigger_raw = joystick.get_axis(AXIS_RIGHT_TRIGGER)

        left_trigger_norm = normalize_trigger(left_trigger_raw)
        right_trigger_norm = normalize_trigger(right_trigger_raw)

        # Aplicar umbral
        lt_val = left_trigger_norm if left_trigger_norm > TRIGGER_THRESHOLD else 0.0
        rt_val = right_trigger_norm if right_trigger_norm > TRIGGER_THRESHOLD else 0.0

        # --- Calcular Velocidad del Motor ---
        # RT controla velocidad positiva, LT controla velocidad negativa
        target_velocity = int((rt_val - lt_val) * MAX_MOTOR_SPEED)

        # --- Enviar Comando al Motor (si es necesario) ---
        velocity_changed = abs(target_velocity - last_sent_velocity) > (MAX_MOTOR_SPEED * MOTOR_STOP_THRESHOLD)
        time_since_last_command = current_time - last_command_time

        if velocity_changed and time_since_last_command >= MOTOR_COMMAND_INTERVAL:
            if abs(target_velocity) < (MAX_MOTOR_SPEED * MOTOR_STOP_THRESHOLD):
                # Si la velocidad es casi cero y no estaba ya detenido, detener
                if last_sent_velocity != 0:
                    print("Motor: STOP")
                    send_spike_command(f'motor.stop(port.{MOTOR_PORT_LETTER})')
                    last_sent_velocity = 0
                    last_command_time = current_time
            else:
                # Si la velocidad es significativa, establecerla
                print(f"Motor: RUN at {target_velocity} deg/s")
                send_spike_command(f'motor.run(port.{MOTOR_PORT_LETTER}, {target_velocity})')
                last_sent_velocity = target_velocity
                last_command_time = current_time
        elif abs(target_velocity) < (MAX_MOTOR_SPEED * MOTOR_STOP_THRESHOLD) and last_sent_velocity != 0 and time_since_last_command >= MOTOR_COMMAND_INTERVAL:
             # Asegurarse de que se detiene si los gatillos vuelven a cero lentamente
             print("Motor: STOP (returned to zero)")
             send_spike_command(f'motor.stop(port.{MOTOR_PORT_LETTER})')
             last_sent_velocity = 0
             last_command_time = current_time


        # Pequeña pausa para no consumir 100% CPU
        time.sleep(0.02)

except KeyboardInterrupt:
    print("\nInterrupción por teclado detectada. Deteniendo...")
finally:
    # --- Limpieza ---
    print("Deteniendo motor y cerrando conexiones...")
    if 'spike_serial' in locals() and spike_serial.is_open:
        try:
            # Intenta detener el motor antes de cerrar
            send_spike_command(f'motor.stop(port.{MOTOR_PORT_LETTER})')
            time.sleep(0.1)
            spike_serial.close()
            print("Puerto serial cerrado.")
        except serial.SerialException as e:
            print(f"Error al cerrar puerto serial: {e}")
    pygame.quit()
    print("Pygame cerrado.")
    print("Script finalizado.")
