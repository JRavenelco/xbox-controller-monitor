# Monitor de Control Xbox (Windows y Linux)

Este repositorio contiene scripts de Python para monitorear y mostrar en tiempo real la actividad de un control (como el de Xbox) conectado a tu computadora.

Se proporcionan dos versiones del script debido a las diferencias en cómo los sistemas operativos manejan la entrada del control:

1.  **`xbox_controller_XInput.py`**: Utiliza la biblioteca `XInput`, que es específica para **Windows**.
2.  **`xbox_controller_pygame.py`**: Utiliza la biblioteca `Pygame`, que es multiplataforma y funciona bien en **Linux (Ubuntu, etc.)** y otros sistemas operativos.

Ambos scripts detectan y muestran las pulsaciones de botones, movimientos de sticks analógicos, D-Pad y presión de gatillos.

## Características Comunes

- Monitoreo en tiempo real de controles conectados.
- Muestra nombres descriptivos de botones en español (configurable).
- Detecta movimientos de sticks analógicos con coordenadas X/Y.
- Monitorea la presión de gatillos LT/RT.
- Detecta movimientos del D-Pad.
- Optimizado para solo mostrar información cuando hay cambios significativos.
- Salida limpia y legible en la consola.

---

## Versión para Windows (`xbox_controller_XInput.py` con XInput)

Esta versión está diseñada específicamente para Windows y utiliza la API XInput de Microsoft.

### Requisitos (Windows)

- Python 3.x
- Biblioteca `XInput-Python`
- Un control compatible con XInput (la mayoría de los controles Xbox modernos) conectado.

### Instalación (Windows)

1.  Asegúrate de tener Python instalado.
2.  Instala la biblioteca `XInput-Python`:
    ```bash
    pip install XInput-Python
    ```

### Uso (Windows)

1.  Conecta tu control a la computadora.
2.  Ejecuta el script:
    ```bash
    python xbox_controller_XInput.py
    ```
3.  Mueve los sticks, presiona botones, D-Pad o gatillos para ver la información.
4.  Presiona Ctrl+C para salir.

### Configuración (Windows)

El script `xbox_controller_XInput.py` tiene umbrales configurables para la sensibilidad de los sticks y gatillos.

---

## Versión para Linux/Multiplataforma (`xbox_controller_pygame.py` con Pygame)

Esta versión utiliza Pygame y es adecuada para Linux (Ubuntu, Debian, etc.) y potencialmente otros sistemas operativos como macOS.

### Requisitos (Linux/Multiplataforma)

- Python 3.x
- Biblioteca `Pygame`
- Un control compatible con Pygame (Xbox, PlayStation, genéricos, etc.) conectado.

### Instalación (Linux/Multiplataforma)

1.  Asegúrate de tener Python instalado.
2.  Instala Pygame:

    *   **Usando pip (recomendado si usas entornos virtuales o quieres la última versión):**
        ```bash
        pip install pygame
        ```
        o si usas `pip3`:
        ```bash
        pip3 install pygame
        ```
    *   **Usando apt en Ubuntu/Debian (si prefieres usar el gestor de paquetes del sistema):**
        ```bash
        sudo apt update
        sudo apt install python3-pygame
        ```

### Uso (Linux/Multiplataforma)

1.  Conecta tu control a la computadora.
2.  Ejecuta el script:
    ```bash
    python3 xbox_controller_pygame.py
    ```
    o si `python` apunta a Python 3:
    ```bash
    python xbox_controller_pygame.py
    ```
3.  Mueve los sticks, presiona botones, D-Pad o gatillos para ver la información.
4.  Presiona Ctrl+C para salir.

### Mapeo y Umbrales Configurables (Pygame)

El script [xbox_controller_pygame.py](http://_vscodecontentref_/0) incluye mapeos y umbrales configurables que podrías necesitar ajustar según tu control específico y sistema operativo:

```python
# filepath: /home/neatgamer23/WRO_2025/xbox-controller-monitor/xbox_controller_pygame.py
# --- Mappings (Adjust based on your controller/OS if needed) ---
# ... (button_map, AXIS_*, HAT_DPAD) ...

# --- Thresholds ---
STICK_THRESHOLD = 0.2  # Threshold for considering stick movement
TRIGGER_THRESHOLD = 0.1 # Threshold for triggers (after normalization)
```