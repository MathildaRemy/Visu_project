import os
import random
import sys
import vtk
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QWidget, QCheckBox,QDialog,QSlider,QLineEdit,QFormLayout,QInputDialog, QMessageBox,QGraphicsScene, QGraphicsView, QGraphicsLineItem, QGraphicsItem
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt5.QtCore import Qt,QPointF
from PyQt5.QtGui import QPen,QPainter



def load_nifti_as_actor(filename, threshold, color, label):
    """Load a NIFTI file and create a VTK actor."""
    reader = vtk.vtkNIFTIImageReader()
    reader.SetFileName(filename)
    reader.Update()
    contour = vtk.vtkMarchingCubes()
    contour.SetInputConnection(reader.GetOutputPort())
    contour.ComputeNormalsOn()
    contour.ComputeGradientsOn()
    contour.SetValue(0, threshold)
    contour.Update()

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(contour.GetOutputPort())
    mapper.ScalarVisibilityOff()

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetDiffuseColor(color)
    actor.GetProperty().SetDiffuse(1.0)
    actor.GetProperty().SetSpecular(0.0)

    return actor, label


def generate_random_color():
    """Generate a random color (RGB)."""
    return random.random(), random.random(), random.random()


class MainWindow(QMainWindow):
    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.nifti_files = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.endswith('.nii.gz')
        ]
        self.selected_files = []

        self.init_ui()

    def init_ui(self):
        """Set up the UI."""
        self.setWindowTitle("NIFTI File Selector")
        self.resize(800, 600)

        # Layout for the main window
        central_widget = QWidget()
        layout = QVBoxLayout()

        # List of NIFTI files with checkboxes
        self.file_list = QListWidget()
        for nifti_file in self.nifti_files:
            item = QListWidgetItem(os.path.basename(nifti_file))
            item.setCheckState(0)
            self.file_list.addItem(item)
        layout.addWidget(self.file_list)

        # Buttons for interaction
        button_layout = QHBoxLayout()
        self.render_button = QPushButton("Rendu")
        self.render_button.clicked.connect(self.render_selected_files)
        self.quit_button = QPushButton("Quitter")
        self.quit_button.clicked.connect(self.close)
        button_layout.addWidget(self.render_button)
        button_layout.addWidget(self.quit_button)
        layout.addLayout(button_layout)

        # Finalize layout
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def render_selected_files(self):
        """Render the selected files."""
        self.selected_files = [
            self.nifti_files[i]
            for i in range(self.file_list.count())
            if self.file_list.item(i).checkState()
        ]

        if not self.selected_files:
            return  # No files selected, do nothing

        self.render_window = RenderWindow(self.selected_files)
        self.render_window.show()
        self.close()

class RenderWindow(QWidget):
    def __init__(self, nifti_files):
        super().__init__()
        self.nifti_files = nifti_files
        self.labels = []  # Store actor labels for tooltip functionality
        self.text_actor = vtk.vtkTextActor()  # Text actor for displaying tooltips
        self.init_ui()

    def init_ui(self):
        """Set up the rendering UI."""
        self.setWindowTitle("VTK Rendering")
        self.resize(800, 600)

        # QVTKRenderWindowInteractor for embedding VTK in PyQt
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        self.vtk_widget.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self.vtk_renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.vtk_renderer)


        # Add a text actor for displaying the label
        self.text_actor.GetTextProperty().SetColor(1.0, 1.0, 1.0)  # White text
        self.text_actor.GetTextProperty().SetFontSize(20)
        self.text_actor.SetPosition(10, 10)  # Bottom-left corner
        self.vtk_renderer.AddActor2D(self.text_actor)

        self.vtk_renderer.SetBackground(0.1, 0.1, 0.1)  # Background color

        # # Add the axes (only orientation with big arrows) 
        # axes = vtk.vtkAxesActor()
        # axes.SetTotalLength(800, 800, 800)  # Adjust size
        # self.vtk_renderer.AddActor(axes)  # Add axes to renderer

        # Add axes 
        axes = vtk.vtkCubeAxesActor()
        bounds = self.get_bounds_from_first_nifti()
        axes.SetBounds(bounds)
        axes.SetCamera(self.vtk_renderer.GetActiveCamera())
        axes.SetFlyModeToOuterEdges()
        self.vtk_renderer.AddViewProp(axes)


        # Layout with "Retour" and "Rendu Volume" buttons
        layout = QVBoxLayout()
        layout.addWidget(self.vtk_widget)

        self.back_button = QPushButton("Retour")
        self.back_button.clicked.connect(self.go_back)
        layout.addWidget(self.back_button)

        self.volume_button = QPushButton("Rendu Volume")
        self.volume_button.clicked.connect(self.toggle_volume_rendering)
        layout.addWidget(self.volume_button)

        self.ray_button = QPushButton("Activer Simulation Rayons")
        self.ray_button.clicked.connect(self.toggle_ray_simulation)
        layout.addWidget(self.ray_button)

        self.setLayout(layout)

        # Initialize the rendering for surfaces and volumes
        self.surface_actors = []
        self.volume_actors = []
        self.is_volume_rendering = False
        self.ray_simulation_enabled = False
        self.ray_origin = None
        self.ray_length = None

        # Liste pour stocker les objets graphiques des rayons (lignes)
        self.ray_actors = []

        # Initialize the surface rendering actors
        for nifti_file in self.nifti_files:
            color = generate_random_color()
            actor, label = load_nifti_as_actor(
                nifti_file, threshold=0.5, color=color, label=os.path.basename(nifti_file)
            )
            self.vtk_renderer.AddActor(actor)
            self.surface_actors.append(actor)
            self.labels.append((actor, label))

        # Initialize the volume rendering actors
        for nifti_file in self.nifti_files:
            volume_actor = self.create_volume_actor(nifti_file)
            self.volume_actors.append(volume_actor)

        # Add mouse move functionality
        self.setup_mouse_move()

        # Initialize and start interaction
        self.vtk_widget.Initialize()
        self.vtk_widget.Start()

    def get_bounds_from_first_nifti(self):
        """Extract the bounds from the first NIFTI file."""
        reader = vtk.vtkNIFTIImageReader()
        reader.SetFileName(self.nifti_files[0])
        reader.Update()

        image_data = reader.GetOutput()
        bounds = image_data.GetBounds()
        return bounds

    def create_volume_actor(self, nifti_file):
        """Create and return a volume actor from the NIfTI file."""
        reader = vtk.vtkNIFTIImageReader()
        reader.SetFileName(nifti_file)
        reader.Update()

        # Volume mapper
        volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
        volume_mapper.SetInputConnection(reader.GetOutputPort())

        # Volume color transfer function
        color_func = vtk.vtkColorTransferFunction()
        color_func.AddRGBPoint(0, 0.0, 0.0, 0.0)
        color_func.AddRGBPoint(1000, 1.0, 0.0, 0.0)  # Red
        color_func.AddRGBPoint(2000, 0.0, 1.0, 0.0)  # Green
        color_func.AddRGBPoint(3000, 0.0, 0.0, 1.0)  # Blue

        # Volume opacity transfer function
        opacity_func = vtk.vtkPiecewiseFunction()
        opacity_func.AddPoint(0, 0.0)
        opacity_func.AddPoint(1000, 0.1)
        opacity_func.AddPoint(2000, 0.3)
        opacity_func.AddPoint(3000, 1.0)

        # Volume property
        volume_property = vtk.vtkVolumeProperty()
        volume_property.SetColor(color_func)
        volume_property.SetScalarOpacity(opacity_func)
        volume_property.SetInterpolationTypeToLinear()

        # Volume actor
        volume_actor = vtk.vtkVolume()
        volume_actor.SetMapper(volume_mapper)
        volume_actor.SetProperty(volume_property)

        return volume_actor

    def toggle_volume_rendering(self):
        """Toggle between surface rendering and volume rendering."""
        if self.is_volume_rendering:
            # Remove all volume actors and show surface actors
            for volume_actor in self.volume_actors:
                self.vtk_renderer.RemoveActor(volume_actor)
            for surface_actor in self.surface_actors:
                self.vtk_renderer.AddActor(surface_actor)
            self.is_volume_rendering = False
        else:
            # Remove all surface actors and show volume actors
            for surface_actor in self.surface_actors:
                self.vtk_renderer.RemoveActor(surface_actor)
            for volume_actor in self.volume_actors:
                self.vtk_renderer.AddActor(volume_actor)
            self.is_volume_rendering = True

        self.vtk_widget.GetRenderWindow().Render()

    def toggle_ray_simulation(self):
        """Active ou désactive la simulation des rayons"""
        if self.ray_simulation_enabled:
            # Désactive la simulation des rayons
            self.ray_simulation_enabled = False
            self.ray_button.setText("Activer Simulation Rayons")
            self.stop_ray_simulation()
        else:
            # Active la simulation des rayons
            self.ray_simulation_enabled = True
            self.ray_button.setText("Désactiver Simulation Rayons")
            self.start_ray_simulation()

    def start_ray_simulation(self):
        """Ouvre une boîte de dialogue pour choisir la position et la longueur des rayons."""
        # Demander la position de départ des rayons
        origin_x, ok_x = QInputDialog.getInt(self, "Position X", "Entrez la position X de départ des rayons:")
        origin_y, ok_y = QInputDialog.getInt(self, "Position Y", "Entrez la position Y de départ des rayons:")
        origin_z, ok_z = QInputDialog.getInt(self, "Position Z", "Entrez la position Z de départ des rayons:")
        
        if ok_x and ok_y and ok_z:
            self.ray_origin = (origin_x, origin_y, origin_z)
            ray_length, ok_length = QInputDialog.getInt(self, "Longueur des rayons", "Entrez la longueur des rayons:")
            
            if ok_length:
                self.ray_length = ray_length
                self.draw_ray(self.ray_origin, self.ray_length)  # Dessiner le rayon dans la scène 3D
                print(f"Rayons démarrés à ({origin_x}, {origin_y}, {origin_z}) avec une longueur de {ray_length}")
            else:
                QMessageBox.warning(self, "Erreur", "La longueur des rayons n'a pas été définie correctement.")
        else:
            QMessageBox.warning(self, "Erreur", "La position des rayons n'a pas été définie correctement.")


    def draw_ray(self, origin, length):
        """Dessine un rayon dans la scène 3D VTK."""
        if origin and length:
            x, y, z = origin
            # Le rayon va dans la direction X (ou toute autre logique selon le besoin)
            end_x = x + length
            end_y = y  # Garder la même position Y pour cet exemple
            end_z = z  # Garder la même position Z pour cet exemple

            # Créer une ligne (rayon) avec vtkLineSource
            line_source = vtk.vtkLineSource()
            line_source.SetPoint1(x, y, z)
            line_source.SetPoint2(end_x, end_y, end_z)
            line_source.Update()

            # Créer un mapper pour la ligne
            line_mapper = vtk.vtkPolyDataMapper()
            line_mapper.SetInputConnection(line_source.GetOutputPort())

            # Créer un acteur pour le rayon
            line_actor = vtk.vtkActor()
            line_actor.SetMapper(line_mapper)

            # Définir une couleur (par exemple, rouge) et une épaisseur pour le rayon
            line_actor.GetProperty().SetColor(1.0, 0.0, 0.0)  # Rouge
            line_actor.GetProperty().SetLineWidth(2)
            self.ray_actors.append(line_actor)
            # Ajouter l'acteur du rayon à la scène VTK
            self.vtk_renderer.AddActor(line_actor)

            # Stocker l'acteur dans la liste des rayons
            

    def stop_ray_simulation(self):
        """Désactive l'affichage des rayons dans la scène de rendu 3D et réinitialise les paramètres."""
        for ray_actor in self.ray_actors:
            self.vtk_renderer.RemoveActor(ray_actor)

        # Supprimer les sources associées aux rayons
       
        self.ray_actors.clear()

        # Réinitialiser les paramètres de simulation
        self.ray_origin = None
        self.ray_length = None
        
        # Mettre à jour l'état de l'interface utilisateur
        self.ray_button.setText("Activer Simulation Rayons")
        self.ray_simulation_enabled = False




    def setup_mouse_move(self):
        """Set up mouse move interactor for showing tooltips."""
        def on_mouse_move(interactor, event):
            x, y = interactor.GetEventPosition()
            picker = vtk.vtkPropPicker()
            picker.Pick(x, y, 0, self.vtk_renderer)
            actor = picker.GetActor()

            if actor:
                # Find the corresponding label for the actor
                for act, label in self.labels:
                    if act == actor:
                        self.text_actor.SetInput(f"Survol: {label}")
                        break
            else:
                self.text_actor.SetInput("")

            interactor.GetRenderWindow().Render()

        # Get the interactor and attach the event
        interactor = self.vtk_widget
        interactor.AddObserver("MouseMoveEvent", on_mouse_move)

        # Add mouse click functionality to open the popup window for organ controls
        interactor.AddObserver("LeftButtonPressEvent", self.on_left_click)

    def on_left_click(self, interactor, event):
        """Handle left mouse click to open popup for organ controls."""
        x, y = interactor.GetEventPosition()
        picker = vtk.vtkPropPicker()
        picker.Pick(x, y, 0, self.vtk_renderer)
        actor = picker.GetActor()

        if actor:
            # Find the corresponding label for the clicked actor
            for act, label in self.labels:
                if act == actor:
                    self.show_popup(actor, label)
                    break

        interactor.GetRenderWindow().Render()

    def show_popup(self, actor, label):
        """Display the popup window with controls for the selected organ."""
        dialog = OrganControlDialog(self, actor, label)
        dialog.exec_()

    def go_back(self):
        """Return to the file selection screen."""
        folder_path = os.path.dirname(self.nifti_files[0])  # Extract the folder path from the first file
        self.main_window = MainWindow(folder_path)  # Pass the folder path
        self.main_window.show()
        self.close()


class OrganControlDialog(QDialog):
    def __init__(self, parent, actor, label):
        super().__init__(parent)
        self.actor = actor
        self.label = label
        self.setWindowTitle(f"Contrôles pour {label}")
        self.setGeometry(300, 300, 300, 200)

        # Layout for the dialog
        layout = QFormLayout()

        # Add slider for opacity
        self.opacity_slider = QSlider()
        self.opacity_slider.setOrientation(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.update_opacity)
        layout.addRow("Opacité:", self.opacity_slider)

        # Add checkbox for visibility toggle
        self.visibility_checkbox = QCheckBox("Afficher")
        self.visibility_checkbox.setChecked(True)
        self.visibility_checkbox.toggled.connect(self.toggle_visibility)
        layout.addRow("Visible:", self.visibility_checkbox)

        # # Add checkbox for section plane toggle
        # self.section_checkbox = QCheckBox("Activer Plan de Section")
        # self.section_checkbox.setChecked(False)
        # layout.addRow("Plan de Section:", self.section_checkbox)

        # Add a "Valider" button to apply changes
        self.validate_button = QPushButton("Valider")
        self.validate_button.clicked.connect(self.apply_changes)
        layout.addRow(self.validate_button)

        self.setLayout(layout)

        # Initialize the plane actor for section if needed
        self.section_plane_actor = None

    def update_opacity(self):
        """Update the opacity of the organ."""
        opacity = self.opacity_slider.value() / 100.0
        self.actor.GetProperty().SetOpacity(opacity)

    def toggle_visibility(self):
        """Toggle the visibility of the organ."""
        is_visible = self.visibility_checkbox.isChecked()
        self.actor.SetVisibility(is_visible)

    def apply_changes(self):
        """Apply the changes when the 'Valider' button is clicked."""
        # Toggle section plane visibility based on the checkbox
        # Optionally, apply more changes here (for instance, save settings)
        self.accept()  # Close the dialog when done



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_folder_with_nii_files>")
        sys.exit(1)

    folder = sys.argv[1]
    app = QApplication(sys.argv)
    main_window = MainWindow(folder)
    main_window.show()
    sys.exit(app.exec_())
