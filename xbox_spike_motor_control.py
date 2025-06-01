import pygame # type: ignore
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
INITIAL_HUB_WAIT_TIME = 2.5 # Segundos - Slightly reduced wait time (adjust if needed)
INITIAL_PROMPT_TIMEOUT = 5.0 # Segundos - Timeout específico para leer el prompt inicial
INITIAL_STOP_RETRIES = 3 # Número de intentos para el stop inicial
FINAL_STOP_RETRIES = 2 # Número de intentos para el stop final
STOP_RETRY_DELAY = 0.2 # Segundos - Pausa entre reintentos de stop
POST_IMPORT_DELAY = 0.2 # Segundos - Pause after import commands

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

# --- Definición de Funciones ---

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
            return True, "" # Return empty string for success message

        # Leer respuesta hasta encontrar prompt o timeout
        response = b""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if spike_serial.in_waiting > 0:
                try:
                    chunk = spike_serial.read(spike_serial.in_waiting)
                    if chunk: # Asegurarse que no es None o vacío si read devuelve eso
                         response += chunk
                except serial.SerialException as read_err:
                     # Error durante la lectura
                     print(f"Error serial durante la lectura para comando '{command}': {read_err}")
                     return False, f"Serial read error: {read_err}"
                except Exception as read_err:
                     # Otro error durante la lectura
                     print(f"Error inesperado durante la lectura para comando '{command}': {read_err}")
                     return False, f"Unexpected read error: {read_err}"

                #print(f"Read chunk: {chunk}") # Debug
                if REPL_PROMPT in response:
                    #print(f"Prompt detected. Full response: {response.decode(errors='ignore')}") # Debug
                    response_str = response.decode(errors='ignore')
                    output_before_prompt = response_str.split(REPL_PROMPT.decode())[0] # Split decoded string

                    # Comprobar si hubo un error antes del prompt
                    error_detected = False
                    for error_indicator_bytes in ERROR_INDICATORS:
                        # Comparar en bytes o decodificar indicador si es necesario
                        # Aquí asumimos que output_before_prompt (string) puede contener el error
                        # Decodificamos el indicador para buscarlo en la cadena
                        error_indicator_str = error_indicator_bytes.decode(errors='ignore')
                        if error_indicator_str in output_before_prompt:
                             print(f"Error detectado en respuesta del Hub:\n{response_str}")
                             # Devolver toda la respuesta decodificada como mensaje de error
                             return False, str(response_str) # Asegurar string
                    # Si no hubo error, devolver la salida antes del prompt
                    return True, str(output_before_prompt.strip()) # Asegurar string
            time.sleep(0.01) # Pequeña pausa para no saturar CPU

        # Timeout case:
        timeout_msg = response.decode(errors='ignore')
        print(f"Timeout esperando prompt para comando: {command}")
        print(f"Respuesta parcial recibida: {timeout_msg}")
        return False, str(timeout_msg) # Asegurar string

    except serial.SerialException as e:
        print(f"Error serial al enviar/recibir comando '{command}': {e}")
        return False, str(e) # str(e) es seguro
    except Exception as e:
        # Captura cualquier otra excepción, incluyendo el TypeError original si ocurre aquí
        error_details = f"Unexpected error type: {type(e)}, content: {e}"
        print(f"Error inesperado en send_spike_command ({command}): {error_details}")
        # Devolver un string formateado para asegurar que es un string
        return False, f"Caught Exception in send_spike_command: {error_details}"

def normalize_trigger(value):
    """Convierte valor de eje de gatillo Pygame (-1 a 1) a 0.0 a 1.0"""
    return (value + 1.0) / 2.0

# --- Inicialización Serial ---
spike_serial = None
print(f"Conectando al Spike Hub en {SPIKE_SERIAL_PORT}...")
try:
    spike_serial = serial.Serial(SPIKE_SERIAL_PORT, SPIKE_BAUD_RATE, timeout=SERIAL_TIMEOUT)
    print(f"Esperando {INITIAL_HUB_WAIT_TIME}s para que el Hub inicialice...")
    time.sleep(INITIAL_HUB_WAIT_TIME)

    spike_serial.reset_input_buffer()
    print(f"Intentando leer prompt inicial del Hub (timeout: {INITIAL_PROMPT_TIMEOUT}s)...")
    initial_output = b""
    start_time = time.time()
    prompt_detected = False
    while time.time() - start_time < INITIAL_PROMPT_TIMEOUT:
         if spike_serial.in_waiting > 0:
              try:
                   chunk = spike_serial.read(spike_serial.in_waiting)
                   if chunk: initial_output += chunk
              except Exception as read_err:
                   print(f"Error leyendo salida inicial: {read_err}")
                   break
              if REPL_PROMPT in initial_output:
                   print("Prompt inicial del Hub detectado.")
                   prompt_detected = True
                   break
         time.sleep(0.1)

    if not prompt_detected:
         print("Advertencia: No se detectó el prompt inicial del Hub. La comunicación puede ser inestable.")
    else:
         print("Conexión serial establecida y prompt detectado.")

    # --- Enviar comandos iniciales al Spike Hub ---
    print("Configurando Spike Hub (importando módulos)...")
    success_import_motor, _ = send_spike_command('import motor')
    if not success_import_motor: print("Advertencia: Fallo al importar 'motor'")
    success_import_hub, _ = send_spike_command('from hub import port')
    if not success_import_hub: print("Advertencia: Fallo al importar 'port'")

    # Add a small delay after imports before trying to stop
    print(f"Pausa de {POST_IMPORT_DELAY}s después de imports...")
    time.sleep(POST_IMPORT_DELAY)

    print(f"Intentando parada inicial del motor ({INITIAL_STOP_RETRIES} intentos)...")
    stopped_ok = False
    for i in range(INITIAL_STOP_RETRIES):
        print(f" Intento de parada inicial {i+1}/{INITIAL_STOP_RETRIES}...")
        success_stop, resp = send_spike_command(f'motor.stop(port.{MOTOR_PORT_LETTER})', timeout=SERIAL_TIMEOUT * 2)
        if success_stop:
            print(f"  -> Comando stop inicial {i+1} enviado OK.")
            stopped_ok = True
            # break # Optional: Stop retrying if successful
        else:
            print(f"  -> Comando stop inicial {i+1} falló. Respuesta: {resp}")
        if i < INITIAL_STOP_RETRIES - 1:
             time.sleep(STOP_RETRY_DELAY)

    if not stopped_ok:
        print("Advertencia: Fallaron los intentos iniciales de detener el motor.")
    else:
        print("Comando(s) de parada inicial enviados.")

    print("Spike Hub listo.")

except serial.SerialException as e:
    print(f"Error al abrir el puerto serial: {e}")
    if spike_serial:
        spike_serial.close()
    pygame.quit()
    exit()
except Exception as e: # Catch other potential init errors
    print(f"Error inesperado durante la inicialización: {e}")
    if spike_serial and spike_serial.is_open:
        spike_serial.close()
    pygame.quit()
    exit()

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
        print(f"Enviando comando final motor.stop() ({FINAL_STOP_RETRIES} intentos)...")
        # Use a longer timeout and retries for the final stop as well
        final_stop_success = False
        for i in range(FINAL_STOP_RETRIES):
             print(f" Intento de parada final {i+1}/{FINAL_STOP_RETRIES}...")
             # Use a significantly longer timeout for final stop
             success, resp = send_spike_command(f'motor.stop(port.{MOTOR_PORT_LETTER})', timeout=SERIAL_TIMEOUT * 3)
             if success:
                  print(f"  -> Comando stop final {i+1} enviado OK.")
                  final_stop_success = True
                  break # Stop trying if successful
             else:
                  print(f"  -> Comando stop final {i+1} falló. Respuesta: {resp}")
             if i < FINAL_STOP_RETRIES - 1:
                  time.sleep(STOP_RETRY_DELAY)

        if not final_stop_success:
             print("Advertencia: No se pudo confirmar el comando final de parada. Enviando una última vez sin esperar.")
             # Send one last time without waiting for response as a fallback
             try:
                  final_cmd = f'motor.stop(port.{MOTOR_PORT_LETTER})\r\n'
                  spike_serial.write(final_cmd.encode())
                  spike_serial.flush()
                  time.sleep(0.1) # Brief pause after sending
             except Exception as final_write_err:
                  print(f"Error en el último intento de envío de stop: {final_write_err}")

        time.sleep(0.1) # Wait a bit after sending stop attempts
        spike_serial.close()
        print("Puerto serial cerrado.")
    else:
        print("Puerto serial ya estaba cerrado o no se inicializó.")

    pygame.quit()
    print("Pygame cerrado.")
    print("Script finalizado.")
