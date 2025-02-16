import tkinter as tk
from tkinter import ttk
import serial
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

# Configurar la conexión serial con el Arduino
try:
    arduino = serial.Serial('COM12', 1000000, timeout=1)
    time.sleep(2)  # Esperar a que Arduino inicialice
except serial.SerialException:
    print("No se pudo abrir el puerto COM seleccionado.")
    arduino = None
    exit()

# Listas para almacenar los datos de tiempo y posición
tiempo_datos = []
pos1_datos = []
pos2_datos = []

PPR = 8000 # Pulsos por revolucion de los encoders 

def send_data(vueltas, velocidad, distancia, modo):
    if arduino:
        data = f"{vueltas},{velocidad},{distancia:.2f},{modo}\n"
        arduino.write(data.encode())
        print(f"Datos enviados: {data.strip()}")

def read_arduino():
    """Lee datos desde Arduino en segundo plano y los almacena."""
    while True:
        if arduino and arduino.in_waiting > 0:
            try:
                # Leer datos binarios, no como texto
                data = arduino.read(12)  # Leer 12 bytes
                if len(data) == 12:  # Asegurarse de que se recibieron todos los bytes
                    # Convertir los bytes a enteros
                    position1 = int.from_bytes(data[0:4], 'little')
                    position2 = int.from_bytes(data[4:8], 'little')
                    timestamp = int.from_bytes(data[8:], 'little')
                    root.after(0, lambda: almacenar_datos(timestamp, position1, position2))
            except Exception as e:
                print(f"Error al leer datos: {e}")


def almacenar_datos(tiempo, pos1, pos2):
    """Almacena los datos de tiempo y posición de los encoders."""
    tiempo_datos.append(tiempo)
    pos1_datos.append(pos1)
    pos2_datos.append(pos2)

def crear_graficas():
    """Procesa y grafica los datos almacenados."""
    if not tiempo_datos:
        print("No hay datos para graficar.")
        return

    tiempo_inicial = tiempo_datos[0]
    posicion_inicial_1 = pos1_datos[0]
    posicion_inicial_2 = pos2_datos[0]

    tiempos = [(t - tiempo_inicial) / 1e6 for t in tiempo_datos]  # Convertir microsegundos a segundos
    posiciones1 = [(p - posicion_inicial_1) * 360 / PPR for p in pos1_datos]
    posiciones2 = [(p - posicion_inicial_2) * 360 / PPR for p in pos2_datos]

    velocidades1 = np.diff(posiciones1) / np.diff(tiempos) if len(tiempos) > 1 else [0]
    velocidades2 = np.diff(posiciones2) / np.diff(tiempos) if len(tiempos) > 1 else [0]

    fig, axs = plt.subplots(2, 1, figsize=(8, 6))

    axs[0].plot(tiempos, posiciones1, label="Posición Encoder 1 (°)", color='b')
    axs[0].plot(tiempos, posiciones2, label="Posición Encoder 2 (°)", color='r')
    axs[0].set_title("Posición Angular vs Tiempo")
    axs[0].set_xlabel("Tiempo (s)")
    axs[0].set_ylabel("Posición (°)")
    axs[0].legend()
    axs[0].grid(True)

    axs[1].plot(tiempos[:-1], velocidades1, label="Velocidad Angular Encoder 1 (°/s)", color='b')
    axs[1].plot(tiempos[:-1], velocidades2, label="Velocidad Angular Encoder 2 (°/s)", color='r')
    axs[1].set_title("Velocidad Angular vs Tiempo")
    axs[1].set_xlabel("Tiempo (s)")
    axs[1].set_ylabel("Velocidad Angular (°/s)")
    axs[1].legend()
    axs[1].grid(True)

    for widget in procesado_frame.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(fig, master=procesado_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

def enviar_distancia():
    distancia = float(distancia_entry.get())
    send_data(0, 0, distancia, 1)

def enviar_velocidad_y_vueltas():
    vueltas = int(vueltas_entry.get())
    velocidad = int(velocidad_entry.get())
    send_data(vueltas, velocidad, 0, 0)

def salir():
    if arduino:
        arduino.close()
    root.quit()

# Iniciar hilo para lectura de datos
t = threading.Thread(target=read_arduino, daemon=True)
t.start()

# Crear la ventana principal
root = tk.Tk()
root.title("Control Arduino")
root.geometry("400x300")
root.configure(bg="#f0f0f0")

# Configurar estilo
style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", padding=6, relief="flat", background="#4CAF50", foreground="white", font=("Arial", 12))
style.configure("TEntry", font=("Arial", 12), padding=5)
style.configure("TLabel", font=("Arial", 12, "bold"), background="#f0f0f0", anchor="w")

# Crear un notebook (pestañas)
notebook = ttk.Notebook(root)
notebook.pack(padx=10, pady=10, fill="both", expand=True)

# Pestaña de control
tab_control = ttk.Frame(notebook)
notebook.add(tab_control, text="Control Motor")

frame = ttk.Frame(tab_control, padding=10)
frame.pack(fill="both", expand=True)

def crear_fila(label_text, row):
    label = ttk.Label(frame, text=label_text, width=15)
    label.grid(row=row, column=0, padx=5, pady=5, sticky="ew")
    entry = ttk.Entry(frame)
    entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
    return entry

vueltas_entry = crear_fila("Vueltas:", 0)
velocidad_entry = crear_fila("Velocidad:", 1)
distancia_entry = crear_fila("Distancia (mm):", 2)

boton_distancia = ttk.Button(frame, text="Enviar Distancia", command=enviar_distancia)
boton_distancia.grid(row=3, column=0, columnspan=2, pady=10, sticky="ew")

boton_vueltas_velocidad = ttk.Button(frame, text="Enviar Velocidad y Vueltas", command=enviar_velocidad_y_vueltas)
boton_vueltas_velocidad.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")

boton_salir = ttk.Button(frame, text="Salir", command=salir)
boton_salir.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")

# Pestaña para procesar datos
tab_processing = ttk.Frame(notebook)
notebook.add(tab_processing, text="Procesar Datos")

procesado_frame = ttk.Frame(tab_processing, padding=10)
procesado_frame.pack(fill="both", expand=True)

# Botón para generar las gráficas
boton_graficas = ttk.Button(procesado_frame, text="Generar Gráficas", command=crear_graficas)
boton_graficas.pack(pady=10)

# Vincular el cierre de la ventana a la función salir
root.protocol("WM_DELETE_WINDOW", salir)

# Iniciar la interfaz gráfica
root.mainloop()