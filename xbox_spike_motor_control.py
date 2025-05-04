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
SERIAL_TIMEOUT = 0.5 # Segundos de espera para respuesta del Hub

# Pygame / Xbox Controller
os.environ['SDL_VIDEODRIVER'] = 'dummy' # Para ejecución sin pantalla
AXIS_LEFT_TRIGGER = 5  # Ajusta según tu mapeo (a menudo 5 o 2 en Linux)
AXIS_RIGHT_TRIGGER = 4 # Ajusta según tu mapeo (a menudo 4 o 5 en Linux)
TRIGGER_THRESHOLD = 0.05 # Umbral mínimo para considerar un gatillo presionado (0.0 a 1.0)

# Motor Control
# Velocidades máximas típicas (grados/segundo): Medium=1110, Large=1050, Small=660
MAX_MOTOR_SPEED = 1000 # Ajusta según tu motor y preferencia
MOTOR_STOP_THRESHOLD_PERCENT = 2 # Porcentaje de MAX_MOTOR_SPEED por debajo del cual se considera 0
MOTOR_COMMAND_INTERVAL = 0.05 # Segundos - Intervalo mínimo entre comandos de velocidad al Spike
DEBOUNCE_THRESHOLD_PERCENT = 1 # Porcentaje de cambio mínimo para enviar nuevo comando

# --- Constantes Internas ---
MOTOR_STOP_THRESHOLD_SPEED = int(MAX_MOTOR_SPEED * (MOTOR_STOP_THRESHOLD_PERCENT / 100.0))
DEBOUNCE_THRESHOLD_SPEED = int(MAX_MOTOR_SPEED * (DEBOUNCE_THRESHOLD_PERCENT / 100.0))
REPL_PROMPT = b'>>> ' # Prompt de MicroPython que esperamos
ERROR_INDICATORS = [b'Traceback', b'Error:']

# --- Inicialización Pygame ---
print("Inicializando Pygame...")
pygame.init()
pygame.joystick.init()
pygame.display.set_mode((1, 1)) # Necesario para el bucle de eventos

print("Detectando control...")
joystick_count = pygame.joystick.get_count()
if (joystick_count == 0):
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
spike_serial = None
print(f"Conectando al Spike Hub en {SPIKE_SERIAL_PORT}...")
try:
    spike_serial = serial.Serial(SPIKE_SERIAL_PORT, SPIKE_BAUD_RATE, timeout=SERIAL_TIMEOUT)
    time.sleep(1) # Dar tiempo al puerto serial
    # Limpiar cualquier salida inicial del Hub (ej. banner de MicroPython)
    spike_serial.reset_input_buffer()
    # Leer hasta el prompt usando el timeout global del objeto Serial
    # Aumentamos temporalmente el timeout global para esta lectura inicial
    original_timeout = spike_serial.timeout
    spike_serial.timeout = SERIAL_TIMEOUT * 2
    initial_output = spike_serial.read_until(REPL_PROMPT)
    spike_serial.timeout = original_timeout # Restaurar timeout original
    #print(f"Initial Hub output: {initial_output.decode(errors='ignore')}") # Debug
    if REPL_PROMPT not in initial_output:
         print("Advertencia: No se detectó el prompt inicial del Hub. Puede haber problemas.")
    print("Conexión serial establecida.")
except serial.SerialException as e:
    print(f"Error al abrir el puerto serial: {e}")
    if spike_serial:
        spike_serial.close()
    pygame.quit()
    exit()

def send_spike_command(command, expect_prompt=True, timeout=SERIAL_TIMEOUT):
    """Envía un comando al Spike Hub y opcionalmente espera el prompt."""
    if not spike_serial or not spike_serial.is_open:
        print("Error: Puerto serial no está abierto.")
        return False, "Serial port closed"

    full_command = command + '\r\n' # Usar \r\n para asegurar compatibilidad REPL
    #print(f"Sending: {command}") # Debug

    try:
        spike_serial.reset_input_buffer() # Limpiar antes de enviar/esperar respuesta
        spike_serial.write(full_command.encode())
        spike_serial.flush() # Asegurar que se envía

        if not expect_prompt:
            time.sleep(0.05) # Pequeña pausa si no esperamos respuesta
            return True, ""

        # Leer respuesta hasta encontrar prompt o timeout
        response = b""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if spike_serial.in_waiting > 0:
                chunk = spike_serial.read(spike_serial.in_waiting)
                response += chunk
                #print(f"Read chunk: {chunk}") # Debug
                if REPL_PROMPT in response:
                    #print(f"Prompt detected. Full response: {response.decode(errors='ignore')}") # Debug
                    # Comprobar si hubo un error antes del prompt
                    for error_indicator in ERROR_INDICATORS:
                        if error_indicator in response.split(REPL_PROMPT)[0]: # Buscar error antes del prompt
                             print(f"Error detectado en respuesta del Hub:\n{response.decode(errors='ignore')}")
                             return False, response.decode(errors='ignore')
                    return True, response.decode(errors='ignore').split(REPL_PROMPT)[0].strip() # Devolver salida antes del prompt
            time.sleep(0.01) # Pequeña pausa para no saturar CPU

        print(f"Timeout esperando prompt para comando: {command}")
        print(f"Respuesta parcial recibida: {response.decode(errors='ignore')}")
        return False, response.decode(errors='ignore')

    except serial.SerialException as e:
        print(f"Error serial al enviar/recibir comando '{command}': {e}")
        return False, str(e)
    except Exception as e:
        print(f"Error inesperado en send_spike_command: {e}")
        return False, str(e)


# --- Enviar comandos iniciales al Spike Hub ---
print("Configurando Spike Hub (importando módulos)...")
success, _ = send_spike_command('import motor')
if not success: print("Error importando 'motor'")
success, _ = send_spike_command('from hub import port')
if not success: print("Error importando 'port'")
# Opcional: Detener el motor al inicio por si acaso
success, _ = send_spike_command(f'motor.stop(port.{MOTOR_PORT_LETTER})')
if not success: print("Error enviando stop inicial")

print("Spike Hub listo.")

# --- Helper Function ---
def normalize_trigger(value):
    """Convierte valor de eje de gatillo Pygame (-1 a 1) a 0.0 a 1.0"""
    return (value + 1.0) / 2.0

# --- Variables de Estado ---
last_sent_velocity = 0
last_command_time = 0
hub_comms_error = False # Flag para detener intentos si falla la comunicación

# --- Bucle Principal ---
print("Iniciando bucle de control. Presiona Ctrl+C para salir.")
running = True
try:
    while running:
        if hub_comms_error:
            print("Error de comunicación con el Hub. Deteniendo intentos.")
            running = False
            break

        # --- Procesar eventos de Pygame ---
        pygame.event.pump() # Procesar eventos internamente
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Podrías añadir manejo de botones aquí si quieres (ej. botón para salir)
            # O un botón para intentar reconectar si hub_comms_error es True

        # --- Leer Gatillos ---
        current_time = time.time()
        try:
            left_trigger_raw = joystick.get_axis(AXIS_LEFT_TRIGGER)
            right_trigger_raw = joystick.get_axis(AXIS_RIGHT_TRIGGER)
        except pygame.error as e:
             print(f"Error leyendo ejes del joystick: {e}. ¿Control desconectado?")
             running = False # Salir si el joystick falla
             break

        left_trigger_norm = normalize_trigger(left_trigger_raw)
        right_trigger_norm = normalize_trigger(right_trigger_raw)

        # Aplicar umbral
        lt_val = left_trigger_norm if left_trigger_norm > TRIGGER_THRESHOLD else 0.0
        rt_val = right_trigger_norm if right_trigger_norm > TRIGGER_THRESHOLD else 0.0

        # --- Calcular Velocidad del Motor ---
        target_velocity = int((rt_val - lt_val) * MAX_MOTOR_SPEED)

        # --- Enviar Comando al Motor (si es necesario) ---
        # Comprobar si el cambio es significativo o si ha pasado suficiente tiempo
        velocity_diff = abs(target_velocity - last_sent_velocity)
        time_since_last_command = current_time - last_command_time

        # Condiciones para enviar comando:
        # 1. La velocidad cambió significativamente Y ha pasado el intervalo mínimo
        # 2. La velocidad es CERO ahora, pero NO era cero antes (para asegurar el stop) Y ha pasado el intervalo
        should_send = False
        if time_since_last_command >= MOTOR_COMMAND_INTERVAL:
            if velocity_diff > DEBOUNCE_THRESHOLD_SPEED:
                 should_send = True
            elif abs(target_velocity) <= MOTOR_STOP_THRESHOLD_SPEED and last_sent_velocity != 0:
                 should_send = True # Asegurar que se envía el comando de parada

        if should_send:
            command_to_send = ""
            is_stop_command = False
            if abs(target_velocity) <= MOTOR_STOP_THRESHOLD_SPEED:
                 # Enviar comando STOP solo si no estábamos ya en velocidad 0
                 if last_sent_velocity != 0:
                      command_to_send = f'motor.stop(port.{MOTOR_PORT_LETTER})'
                      target_velocity = 0 # Asegurar que la velocidad objetivo es 0 para el estado
                      is_stop_command = True
                      print("Motor: STOP")
                 # else: No hacer nada si ya estábamos en 0 y el target sigue siendo 0
            else:
                 # Enviar comando RUN
                 command_to_send = f'motor.run(port.{MOTOR_PORT_LETTER}, {target_velocity})'
                 print(f"Motor: RUN at {target_velocity} deg/s")

            if command_to_send:
                 success, response = send_spike_command(command_to_send)
                 if success:
                      last_sent_velocity = target_velocity
                      last_command_time = current_time
                 else:
                      print(f"¡Fallo al enviar comando! Respuesta: {response}")
                      # Decidir qué hacer: reintentar, detener todo, etc.
                      # Por ahora, marcamos error y salimos del bucle.
                      hub_comms_error = True


        # Pequeña pausa para no consumir 100% CPU
        time.sleep(0.02)

except KeyboardInterrupt:
    print("\nInterrupción por teclado detectada. Deteniendo...")
finally:
    # --- Limpieza ---
    print("Deteniendo motor y cerrando conexiones...")
    if spike_serial and spike_serial.is_open:
        print("Enviando comando final motor.stop()...")
        # Intentar detener el motor de forma fiable
        success, _ = send_spike_command(f'motor.stop(port.{MOTOR_PORT_LETTER})', timeout=SERIAL_TIMEOUT*2)
        if not success:
             print("Advertencia: No se pudo confirmar el comando final de parada.")
        # Intentar un segundo stop por si acaso
        time.sleep(0.1)
        send_spike_command(f'motor.stop(port.{MOTOR_PORT_LETTER})', expect_prompt=False) # Enviar sin esperar
        time.sleep(0.1)
        spike_serial.close()
        print("Puerto serial cerrado.")
    else:
        print("Puerto serial ya estaba cerrado o no se inicializó.")

    pygame.quit()
    print("Pygame cerrado.")
    print("Script finalizado.")
