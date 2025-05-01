# Monitor de Control Xbox

Un script de Python que monitorea y muestra en tiempo real la actividad de un control de Xbox conectado. Detecta y muestra las pulsaciones de botones, movimientos de sticks analógicos y presión de gatillos.

## Características

- Monitoreo en tiempo real de controles Xbox conectados
- Muestra nombres descriptivos de botones en español
- Detecta movimientos de sticks analógicos con coordenadas X/Y
- Monitorea la presión de gatillos LT/RT
- Optimizado para solo mostrar información cuando hay cambios significativos
- Salida limpia y legible en la consola

## Requisitos

- Python 3.x
- Paquete XInput-Python (`pip install XInput-Python`)
- Un control de Xbox conectado por USB o Bluetooth

## Instalación

1. Clona este repositorio o descarga el archivo `xbox_controller.py`
2. Instala las dependencias:
`pip install XInput-Python`
Si el comando anterior no funciona, prueba con:
`pip install pygame-xinput`

## Uso

1. Conecta un control de Xbox a tu computadora
2. Ejecuta el script: python `xbox_controller.py`
3. Mueve los sticks, presiona botones o gatillos para ver la información en tiempo real
4. Presiona Ctrl+C para salir

## Umbrales configurables

El script incluye umbrales configurables para determinar cuándo se consideran activos los controles:

```python
# Umbrales para detectar movimiento
STICK_THRESHOLD = 0.1  # Umbral para considerar movimiento en sticks
TRIGGER_THRESHOLD = 0.1  # Umbral para gatillos
```