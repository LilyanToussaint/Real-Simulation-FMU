import sys
import tkinter as tk
from tkinter import ttk
from fmpy import *
from fmpy.fmi2 import FMU2Slave
import shutil
import numpy as np
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading

def initialize_fmu(fmu_filename):
    # Extraire la FMU
    unzipdir = extract(fmu_filename)
    
    # Lire la description du modèle
    model_description = read_model_description(fmu_filename)
    
    # Obtenir les références des variables
    variable_names = [
        'inletFlowRate',
        'outletFlowRate',
        'tankLevel',
        'hydrostaticPressure'
    ]
    
    variables = {}
    for var_name in variable_names:
        try:
            var = [v for v in model_description.modelVariables if v.name == var_name][0]
            variables[var_name] = var
        except IndexError as e:
            print(f"Variable '{var_name}' non trouvée dans le modèle.")
            sys.exit(1)
    
    # Récupérer les références des variables
    vr = {var_name: variables[var_name].valueReference for var_name in variable_names}
    
    # Vérifier la causalité des variables d'entrée
    if variables['inletFlowRate'].causality != 'input' or variables['outletFlowRate'].causality != 'input':
        print("Les variables de débit ne sont pas des entrées.")
        sys.exit(1)
    
    # Initialiser le modèle
    fmu = FMU2Slave(guid=model_description.guid,
                    unzipDirectory=unzipdir,
                    modelIdentifier=model_description.coSimulation.modelIdentifier,
                    instanceName='instance1')
    
    fmu.instantiate()
    
    return fmu, vr, unzipdir

def setup_fmu(fmu, vr, start_time, initial_inlet_flow_rate, initial_outlet_flow_rate):
    fmu.setupExperiment(startTime=start_time)
    fmu.enterInitializationMode()
    # Vous pouvez définir des paramètres initiaux ici si nécessaire
    fmu.exitInitializationMode()
    
    # Définir les débits initiaux
    fmu.setReal([vr['inletFlowRate']], [initial_inlet_flow_rate])
    fmu.setReal([vr['outletFlowRate']], [initial_outlet_flow_rate])

def initialize_gui(initial_inlet_flow_rate, initial_outlet_flow_rate, tank_width, tank_height):
    # Création de l'interface tkinter
    root = tk.Tk()
    root.title("Simulation Interactive de la Cuve d'Eau Simplifiée")
    
    # Création des figures matplotlib pour les graphiques
    fig = Figure(figsize=(8, 6))
    ax1 = fig.add_subplot(311)
    ax2 = fig.add_subplot(312)
    ax3 = fig.add_subplot(313)
    
    # Tracés initiaux pour chaque graphique
    line_tank_level, = ax1.plot([], [], label='Niveau de la cuve (m)', color='blue')
    ax1.set_ylabel('Niveau (m)')
    ax1.set_title('Niveau de la cuve en fonction du temps')
    ax1.grid(True)
    
    line_inlet_flow, = ax2.plot([], [], label='Débit entrant (m³/s)', color='green')
    line_outlet_flow, = ax2.plot([], [], label='Débit sortant (m³/s)', color='red')
    ax2.set_ylabel('Débit (m³/s)')
    ax2.set_title('Débits entrant et sortant')
    ax2.legend()
    ax2.grid(True)
    
    line_pressure, = ax3.plot([], [], label='Pression hydrostatique (Pa)', color='purple')
    ax3.set_xlabel('Temps (s)')
    ax3.set_ylabel('Pression (Pa)')
    ax3.set_title('Pression hydrostatique en fonction du temps')
    ax3.grid(True)
    
    # Intégrer la figure matplotlib dans tkinter
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)
    
    # Création des sliders pour contrôler les débits
    slider_frame = tk.Frame(root)
    slider_frame.pack(side=tk.BOTTOM, fill=tk.X)
    
    # Slider pour le débit entrant
    label_inlet = tk.Label(slider_frame, text="Débit entrant (m³/s)")
    label_inlet.pack(side=tk.LEFT)
    
    inlet_flow_var = tk.DoubleVar(value=initial_inlet_flow_rate)
    
    slider_inlet = ttk.Scale(slider_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL,
                             variable=inlet_flow_var)
    slider_inlet.pack(side=tk.LEFT, fill=tk.X, expand=1)
    
    # Slider pour le débit sortant
    label_outlet = tk.Label(slider_frame, text="Débit sortant (m³/s)")
    label_outlet.pack(side=tk.LEFT)
    
    outlet_flow_var = tk.DoubleVar(value=initial_outlet_flow_rate)
    
    slider_outlet = ttk.Scale(slider_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL,
                              variable=outlet_flow_var)
    slider_outlet.pack(side=tk.LEFT, fill=tk.X, expand=1)
    
    # Création de la figure pour le schéma 2D
    schema_fig = Figure(figsize=(6, 6))
    schema_ax = schema_fig.add_subplot(111)
    schema_canvas = FigureCanvasTkAgg(schema_fig, master=root)
    schema_canvas.draw()
    schema_canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
    
    return (root, canvas, fig, ax1, ax2, ax3, line_tank_level, line_inlet_flow, line_outlet_flow,
            line_pressure, inlet_flow_var, outlet_flow_var, schema_canvas, schema_ax)

def draw_initial_schema(schema_ax, tank_width, tank_height):
    schema_ax.clear()
    # Dessiner la cuve
    tank_rect = matplotlib.patches.Rectangle((2, 0), tank_width, tank_height, linewidth=1, edgecolor='black', facecolor='none')
    schema_ax.add_patch(tank_rect)
    # Définir les limites de l'axe
    schema_ax.set_xlim(0, 6)
    schema_ax.set_ylim(-1, tank_height + 2)
    schema_ax.set_aspect('equal')
    schema_ax.axis('off')

def update_schema(schema_ax, schema_canvas, tank_level, inlet_flow_rate, outlet_flow_rate, hydrostatic_pressure, tank_width, tank_height):
    schema_ax.clear()
    # Dessiner la cuve
    tank_rect = matplotlib.patches.Rectangle((2, 0), tank_width, tank_height,
                                             linewidth=1, edgecolor='black', facecolor='none')
    schema_ax.add_patch(tank_rect)
    # Dessiner le niveau d'eau
    water_rect = matplotlib.patches.Rectangle((2, 0), tank_width, tank_level,
                                              linewidth=0, edgecolor='blue', facecolor='blue', alpha=0.6)
    schema_ax.add_patch(water_rect)

    # Positions pour les débits
    inlet_x = 1
    inlet_y = tank_height - 1.5
    outlet_x = 4
    outlet_y = 1.5

    # Dessiner les flèches de débit
    # Débit entrant
    schema_ax.annotate('', xy=(2, inlet_y), xytext=(inlet_x, inlet_y),
                       arrowprops=dict(arrowstyle='->', color='green', linewidth=2))
    schema_ax.text(inlet_x - 0.1, inlet_y, f"Débit entrant: {inlet_flow_rate:.2f} m³/s",
                   fontsize=12, color='green', ha='right', va='center')
    # Débit sortant
    schema_ax.annotate('', xy=(3 + tank_width, outlet_y), xytext=(outlet_x, outlet_y),
                       arrowprops=dict(arrowstyle='->', color='red', linewidth=2))
    schema_ax.text(outlet_x + 1, outlet_y, f"Débit sortant: {outlet_flow_rate:.2f} m³/s",
                   fontsize=12, color='red', ha='left', va='center')

    # Afficher la pression hydrostatique au fond de la cuve
    schema_ax.text(3, -0.5, f"Pression hydrostatique: {hydrostatic_pressure / 1e5:.2f} bar",
                   fontsize=12, color='purple', ha='center')

    # Ajuster les limites de l'axe pour tout rendre visible
    schema_ax.set_xlim(0, 6)
    schema_ax.set_ylim(-1, tank_height + 2)
    schema_ax.set_aspect('equal')
    schema_ax.axis('off')

    # Rafraîchir le canvas pour mettre à jour l'affichage
    schema_canvas.draw()

def run_simulation():
    global current_time, end_time, step_size
    global fmu, vr
    global times, tank_levels, inlet_flow_rates, outlet_flow_rates, hydrostatic_pressures
    global inlet_flow_var, outlet_flow_var
    global line_tank_level, line_inlet_flow, line_outlet_flow, line_pressure
    global ax1, ax2, ax3
    global canvas
    global schema_ax, schema_canvas, tank_width, tank_height
    while current_time <= end_time:
        # Obtenir les valeurs actuelles des sliders pour les débits
        inlet_flow_rate = inlet_flow_var.get()
        outlet_flow_rate = outlet_flow_var.get()
        # Mettre à jour les valeurs dans le modèle
        fmu.setReal([vr['inletFlowRate']], [inlet_flow_rate])
        fmu.setReal([vr['outletFlowRate']], [outlet_flow_rate])

        # Avancer la simulation
        try:
            fmu.doStep(currentCommunicationPoint=current_time, communicationStepSize=step_size)
        except Exception as e:
            print(f"Erreur lors de l'avancement de la simulation au temps {current_time}: {e}")
            break  # Sortir de la boucle en cas d'erreur

        # Récupérer les résultats
        tank_level = fmu.getReal([vr['tankLevel']])[0]
        hydrostatic_pressure = fmu.getReal([vr['hydrostaticPressure']])[0]

        # Enregistrer les résultats
        times.append(current_time)
        tank_levels.append(tank_level)
        inlet_flow_rates.append(inlet_flow_rate)
        outlet_flow_rates.append(outlet_flow_rate)
        hydrostatic_pressures.append(hydrostatic_pressure)

        # Mettre à jour les données des tracés
        line_tank_level.set_data(times, tank_levels)
        line_inlet_flow.set_data(times, inlet_flow_rates)
        line_outlet_flow.set_data(times, outlet_flow_rates)
        line_pressure.set_data(times, hydrostatic_pressures)

        # Ajuster les limites des axes pour chaque graphique
        ax1.relim()
        ax1.autoscale_view()
        ax2.relim()
        ax2.autoscale_view()
        ax3.relim()
        ax3.autoscale_view()

        # Mettre à jour le schéma 2D
        update_schema(schema_ax, schema_canvas, tank_level, inlet_flow_rate, outlet_flow_rate, hydrostatic_pressure, tank_width, tank_height)

        # Rafraîchir les tracés
        canvas.draw()

        # Avancer le temps
        current_time += step_size

    # Terminer la simulation
    fmu.terminate()
    fmu.freeInstance()

    # Nettoyer les fichiers temporaires
    shutil.rmtree(unzipdir)

# Code principal
if __name__ == '__main__':
    # Chemin du fichier FMU (mettez à jour le chemin si nécessaire)
    fmu_filename = r'SimpleWaterTank.fmu'
    
    # Initialiser la FMU
    fmu, vr, unzipdir = initialize_fmu(fmu_filename)
    
    # Paramètres de simulation
    start_time = 0.0
    end_time = 60.0  # Durée de la simulation (ajustez si nécessaire)
    step_size = 0.1
    current_time = start_time

    # Valeurs initiales des débits
    initial_inlet_flow_rate = 0.5
    initial_outlet_flow_rate = 0.5

    # Configurer la FMU
    setup_fmu(fmu, vr, start_time, initial_inlet_flow_rate, initial_outlet_flow_rate)

    # Initialisation des listes pour stocker les résultats
    times = []
    tank_levels = []
    inlet_flow_rates = []
    outlet_flow_rates = []
    hydrostatic_pressures = []

    # Dimensions de la cuve pour le schéma
    tank_width = 2
    tank_height = 10  # Hauteur maximale de la cuve

    # Initialiser l'interface graphique
    (root, canvas, fig, ax1, ax2, ax3, line_tank_level, line_inlet_flow, line_outlet_flow,
     line_pressure, inlet_flow_var, outlet_flow_var, schema_canvas, schema_ax) = initialize_gui(initial_inlet_flow_rate, initial_outlet_flow_rate, tank_width, tank_height)

    # Dessiner le schéma initial
    draw_initial_schema(schema_ax, tank_width, tank_height)
    schema_canvas.draw()

    # Exécuter la simulation dans un thread séparé pour éviter de bloquer l'interface graphique
    simulation_thread = threading.Thread(target=run_simulation)
    simulation_thread.start()

    # Lancer la boucle principale de tkinter
    root.mainloop()
