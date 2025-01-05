import os
import random
import sys
import vtk
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, 
                             QWidget, QCheckBox, QDialog, QSlider, QFormLayout, QLabel, QGroupBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import math



def load_nifti_as_actor(filename, threshold, color, label):
    """Load a NIFTI file and create a VTK actor with contours."""

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






#########################     MAIN WINDOW      ##########################

class MainWindow(QMainWindow):
    """Main window for NIFTI file selection and rendering."""

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.nifti_files = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.endswith('.nii.gz')
        ]
        self.selected_files = []
        self.render_window = None  
        self.init_ui()


    def init_ui(self):
        """Set up the user interface for file selection."""
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
        self.render_button = QPushButton("Render")
        self.render_button.clicked.connect(self.render_selected_files)
        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)
        self.is_stereo_rendering = False 
        self.stereo_button = QPushButton("Activate Stereo")
        self.stereo_button.clicked.connect(self.toggle_stereo)
        button_layout.addWidget(self.render_button)
        button_layout.addWidget(self.quit_button)
        button_layout.addWidget(self.stereo_button)
        layout.addLayout(button_layout)

        # Finalize layout
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)


    def render_selected_files(self):
        """Render the selected files based on the stereo rendering state."""
        self.selected_files = [
            self.nifti_files[i]
            for i in range(self.file_list.count())
            if self.file_list.item(i).checkState()
        ]

        if not self.selected_files:
            return 

        # Initialize
        self.render_window = RenderWindow(self.selected_files)
        render_window = self.render_window.vtk_widget.GetRenderWindow()

        # Check if stereo rendering is enabled or not and change text accordingly 
        if self.is_stereo_rendering:
            render_window.SetStereoTypeToCrystalEyes()  
            self.stereo_button.setText("Deactivate Stereo")  
        else:
            render_window.SetStereoTypeToDresden() 
            self.stereo_button.setText("Activate Stereo")  
        
        # Render and show the scene 
        render_window.Render()
        self.render_window.show()

        # Close the main window after launching render
        self.close()


    def toggle_stereo(self):
        """Toggle between stereo and normal rendering."""

        print("Stereo button clicked.")

        # Toggle the stereo rendering state
        self.is_stereo_rendering = not self.is_stereo_rendering

        # Update the button text 
        if self.is_stereo_rendering:
            self.stereo_button.setText("Deactivate Stereo")
        else:
            self.stereo_button.setText("Activate Stereo")









#########################     RENDERING WINDOW      ##########################

class RenderWindow(QWidget):
    """Rendering window for 3D visualization of NIFTI files."""

    def __init__(self, nifti_files):
        super().__init__()
        self.nifti_files = nifti_files
        self.labels = [] 
        self.text_actor = vtk.vtkTextActor() 
        self.default_view_position = (-1000, -1000, 400) 
        # Default focal point is the center of the brain
        self.default_view_focal_point = self.get_center_of_brain()
        self.default_view_up = (0, 0, 1)
        self.intersection_markers = []
        self.ray_direction = (1, 0, 0) 
        self.marker_radius = 3.0
        self.init_ui()

    def init_ui(self):
        """Set up the rendering UI."""

        self.setWindowTitle("VTK Rendering")
        self.resize(1280, 720)

        # QVTKRenderWindowInteractor for embedding VTK in PyQt
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        self.vtk_widget.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self.vtk_renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.vtk_renderer)

        # Text actor for displaying the label
        self.text_actor.GetTextProperty().SetColor(1.0, 1.0, 1.0)  # White text
        self.text_actor.GetTextProperty().SetFontSize(20)
        self.text_actor.SetPosition(10, 10)  # Bottom-left corner
        self.vtk_renderer.AddActor2D(self.text_actor)

        # Adjust widget positions
        self.file_list_widget = QListWidget(self)
        self.file_list_widget.setGeometry(10, 10, 200, 100)  
        self.file_list_widget.setVisible(False)
        self.populate_file_list()  # Populate the list with the loaded files

        self.vtk_renderer.SetBackground(0.1, 0.1, 0.1) 
        self.setup_key_event()
        self.is_full_screen = False

        # Add axes
        axes = vtk.vtkCubeAxesActor()
        bounds = self.get_bounds_from_first_nifti()
        axes.SetBounds(bounds)
        axes.SetCamera(self.vtk_renderer.GetActiveCamera())
        axes.SetFlyModeToOuterEdges()
        self.vtk_renderer.AddViewProp(axes)

        # Layout for the camera information
        info_layout = QVBoxLayout()

        # QLabel to show camera position
        self.camera_position_label = QLabel("Position : (0, 0, 0)")
        info_layout.addWidget(self.camera_position_label)

        # QLabel to show focal point
        self.camera_focal_point_label = QLabel("Focal Point  : (0, 0, 0)")
        info_layout.addWidget(self.camera_focal_point_label)

        # QLabel to show up view
        self.camera_view_up_label = QLabel("Top view  : (0, 0, 1)")
        info_layout.addWidget(self.camera_view_up_label)

        # Main layout for VTK render window
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.vtk_widget)

        # Add camera information layout to the main layout
        main_layout.addLayout(info_layout)

        # Add buttons
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_back)
        main_layout.addWidget(self.back_button)

        self.volume_button = QPushButton("Volume Rendering")
        self.volume_button.clicked.connect(self.toggle_volume_rendering)
        main_layout.addWidget(self.volume_button)

        self.ray_button = QPushButton("Activate Ray Simulation")
        self.ray_button.clicked.connect(self.toggle_ray_simulation)
        main_layout.addWidget(self.ray_button)

        self.default_view_button = QPushButton("Return to default viewpoint")
        self.default_view_button.clicked.connect(self.reset_camera_to_default)
        main_layout.addWidget(self.default_view_button)

        # Create a new widget for the sliders layout
        sliders_widget = QWidget(self)
        sliders_layout = QHBoxLayout(sliders_widget)

        # Sliders for controlling ray parameters (hidden initially)
        self.x_slider = self.create_x_slider(self.on_x_changed)
        self.y_slider = self.create_y_slider(self.on_y_changed)
        self.z_slider = self.create_z_slider(self.on_z_changed)
        self.length_slider = self.create_length_slider(self.on_length_changed)
        self.radius_slider = self.create_radius_slider(self.on_radius_changed)
        self.azimuth_slider = self.create_azimuth_slider(self.on_azimuth_changed)
        self.elevation_slider = self.create_elevation_slider(self.on_elevation_changed)

        # Add labels to display slider values
        self.x_label = QLabel("X: 0")
        self.y_label = QLabel("Y: 300")
        self.z_label = QLabel("Z: 260")
        self.radius_label = QLabel("Radius : 3")
        self.length_label = QLabel("Length: 500")
        self.elevation_label = QLabel("Elevation: 30°")
        self.azimuth_label = QLabel("Azimuth: 45°")

        self.x_slider.hide()
        self.y_slider.hide()
        self.z_slider.hide()
        self.length_slider.hide()
        self.azimuth_slider.hide()
        self.elevation_slider.hide()
        self.radius_slider.hide()
        self.x_label.hide()
        self.y_label.hide()
        self.z_label.hide()
        self.length_label.hide()
        self.azimuth_label.hide()
        self.elevation_label.hide()
        self.radius_label.hide()

        # Add the labels and sliders to the sliders layout
        sliders_layout.addWidget(self.x_label)
        sliders_layout.addWidget(self.x_slider)
        sliders_layout.addWidget(self.y_label)
        sliders_layout.addWidget(self.y_slider)
        sliders_layout.addWidget(self.z_label)
        sliders_layout.addWidget(self.z_slider)
        sliders_layout.addWidget(self.length_label)
        sliders_layout.addWidget(self.length_slider)
        sliders_layout.addWidget(self.radius_label)
        sliders_layout.addWidget(self.radius_slider)
        sliders_layout.addWidget(self.azimuth_label)
        sliders_layout.addWidget(self.azimuth_slider)
        sliders_layout.addWidget(self.elevation_label)
        sliders_layout.addWidget(self.elevation_slider)

        sliders_widget.setGeometry(1000, 1000, 200, 200) 

        # Add sliders widget to the main layout
        main_layout.addWidget(sliders_widget)
        self.setLayout(main_layout)

        # Initialize the rendering for surfaces and volumes
        self.surface_actors = []
        self.volume_actors = []
        self.is_volume_rendering = False
        self.ray_simulation_enabled = False
        self.ray_origin = (0, 300, 250) 
        self.ray_length = 500  

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

        # Set the camera
        self.reset_camera_to_default()
        self.observe_camera()
        self.vtk_renderer.ResetCamera()  

        # Initialize and start interaction
        self.vtk_widget.Initialize()
        self.vtk_widget.Start()


    ####################    SLIDERS CREATION    ###################
   
    def create_x_slider(self, callback):
        """Create a slider for the X coordinate."""
        slider_group = QGroupBox("X")
        slider_layout = QVBoxLayout()
        
        # Get the bounds from the first NIFTI file to set the slider range
        bounds = self.get_bounds_from_first_nifti()
        
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(int(bounds[0]))
        slider.setMaximum(int(bounds[1]))
        slider.setValue(0)
        slider.valueChanged.connect(callback)
        
        slider_layout.addWidget(slider)
        slider_group.setLayout(slider_layout)
        
        return slider_group

    def create_y_slider(self, callback):
        """Create a slider for the Y coordinate."""
        slider_group = QGroupBox("Y")
        slider_layout = QVBoxLayout()
        
        bounds = self.get_bounds_from_first_nifti()
        
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(int(bounds[2]))
        slider.setMaximum(int(bounds[3]))
        slider.setValue(300)
        slider.valueChanged.connect(callback)
        
        slider_layout.addWidget(slider)
        slider_group.setLayout(slider_layout)
        
        return slider_group

    def create_z_slider(self, callback):
        """Create a slider for the Z coordinate."""
        slider_group = QGroupBox("Z")
        slider_layout = QVBoxLayout()
        
        bounds = self.get_bounds_from_first_nifti()
        
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(int(bounds[4]))
        slider.setMaximum(int(bounds[5]))
        slider.setValue(260)
        slider.valueChanged.connect(callback)
        
        slider_layout.addWidget(slider)
        slider_group.setLayout(slider_layout)
        
        return slider_group

    def create_length_slider(self, callback):
        """Create a slider for controlling the length of the ray."""
        slider_group = QGroupBox("Length")
        slider_layout = QVBoxLayout()
        
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(1500)
        slider.setValue(500)
        slider.valueChanged.connect(callback)
        
        slider_layout.addWidget(slider)
        slider_group.setLayout(slider_layout)
        
        return slider_group
    
    def create_azimuth_slider(self, callback):
        """Create a slider for the Azimuth angle."""
        slider_group = QGroupBox("Azimuth")
        slider_layout = QVBoxLayout()

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(-90)
        slider.setMaximum(90)
        slider.setValue(0)
        slider.valueChanged.connect(callback)
        
        slider_layout.addWidget(slider)
        slider_group.setLayout(slider_layout)
        
        return slider_group

    def create_elevation_slider(self, callback):
        """Create a slider for the Elevation angle (-90° to 90°)."""
        slider_group = QGroupBox("Elevation")
        slider_layout = QVBoxLayout()

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(-90)
        slider.setMaximum(90)
        slider.setValue(0)
        slider.valueChanged.connect(callback)
        
        slider_layout.addWidget(slider)
        slider_group.setLayout(slider_layout)
        
        return slider_group
    
    def create_radius_slider(self, callback):
        slider_group = QGroupBox("Radius")
        slider_layout = QVBoxLayout()

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(1)
        slider.setMaximum(10)
        slider.setValue(3)
        slider.valueChanged.connect(callback)
        
        slider_layout.addWidget(slider)
        slider_group.setLayout(slider_layout)
        
        return slider_group


    ####################    RAY SIMULATION FUNCTIONS    ###################


    def toggle_ray_simulation(self):
        """Toggle the ray simulation."""
        self.ray_simulation_enabled = not self.ray_simulation_enabled
        self.update_file_list_visibility()
        if self.ray_simulation_enabled:
            self.x_slider.show()
            self.y_slider.show()
            self.z_slider.show()
            self.length_slider.show()
            self.azimuth_slider.show()
            self.elevation_slider.show()
            self.radius_slider.show()
            self.x_label.show()
            self.y_label.show()
            self.z_label.show()
            self.length_label.show()
            self.azimuth_label.show()
            self.elevation_label.show()
            self.radius_label.show()
            self.ray_button.setText("Disable Ray Simulation")

            # Ensure ray is created/reset when enabling ray simulation
            self.create_ray()
        else:
            self.x_slider.hide()
            self.y_slider.hide()
            self.z_slider.hide()
            self.length_slider.hide()
            self.azimuth_slider.hide()
            self.elevation_slider.hide()
            self.radius_slider.hide()
            self.x_label.hide()
            self.y_label.hide()
            self.z_label.hide()
            self.length_label.hide()
            self.azimuth_label.hide()
            self.elevation_label.hide()
            self.radius_label.hide()
            self.ray_button.setText("Activate Ray Simulation")

            # Remove ray when disabling ray simulation
            for ray_actor in self.ray_actors:
                self.vtk_renderer.RemoveActor(ray_actor)
            self.ray_actors = []

            self.remove_markers()

        self.vtk_widget.GetRenderWindow().Render()


    def create_ray(self):
        """Create and update the ray in the scene, and check for intersections with loaded files."""
        if not self.ray_simulation_enabled:  
            self.remove_markers()
            return
        if self.ray_origin is None or self.ray_length is None:
            return

        # Access the slider values
        azimuth_slider = self.azimuth_slider.findChild(QSlider) if isinstance(self.azimuth_slider, QGroupBox) else self.azimuth_slider
        elevation_slider = self.elevation_slider.findChild(QSlider) if isinstance(self.elevation_slider, QGroupBox) else self.elevation_slider
        azimuth_value = azimuth_slider.value() 
        elevation_value = elevation_slider.value() 

        # Convert slider values to radians
        azimuth_rad = math.radians(azimuth_value) 
        elevation_rad = math.radians(elevation_value)  

        # Calculate the direction of the ray using azimuth and elevation angles
        ray_direction = (
            math.cos(elevation_rad) * math.cos(azimuth_rad), 
            math.cos(elevation_rad) * math.sin(azimuth_rad), 
            math.sin(elevation_rad)                         
        )

        # Compute the end point of the ray 
        end_point = (
            self.ray_origin[0] + ray_direction[0] * self.ray_length,
            self.ray_origin[1] + ray_direction[1] * self.ray_length,
            self.ray_origin[2] + ray_direction[2] * self.ray_length
        )

        # Create a VTK Line Source for visualization
        line_source = vtk.vtkLineSource()
        line_source.SetPoint1(self.ray_origin)
        line_source.SetPoint2(end_point)

        # Mapper and actor setup for visualization
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(line_source.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1.0, 0.0, 0.0)

        # Remove any existing ray actor (if present)
        for ray_actor in self.ray_actors:
            self.vtk_renderer.RemoveActor(ray_actor)

        # Add the new ray actor to the scene
        self.ray_actors = [actor]
        self.vtk_renderer.AddActor(actor)

        # Check for intersections with loaded files
        self.check_intersections(self.ray_origin, end_point)

        # Render the updated scene
        self.vtk_widget.GetRenderWindow().Render()


    def remove_markers(self):
        """Remove all intersection markers from the scene."""
        for marker in self.intersection_markers:
            self.vtk_renderer.RemoveActor(marker)
        self.intersection_markers.clear() 
        self.vtk_widget.GetRenderWindow().Render()


    def populate_file_list(self):
        """Populate the file list widget with the base names of loaded files without extensions."""
        self.file_list_widget.clear()
        for file_path in self.nifti_files:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            item = QListWidgetItem(base_name)
            self.file_list_widget.addItem(item)


    def update_file_list_visibility(self):
        """Update the visibility of the file list widget based on ray simulation state."""
        if self.ray_simulation_enabled:
            self.populate_file_list() 
            self.file_list_widget.setVisible(True)  
        else:
            self.file_list_widget.setVisible(False) 


    def check_intersections(self, start_point, end_point):
        """Check if the ray intersects with any loaded 3D objects."""
        if not self.nifti_files:
            return  # No files loaded

        # Remove previous intersection markers
        for marker in self.intersection_markers:
            self.vtk_renderer.RemoveActor(marker)
        self.intersection_markers = []

        intersected_files = []  # Store the names of files that the ray intersects

        # Create a ray intersection checker
        obb_tree = vtk.vtkOBBTree()
        obb_tree.SetMaxLevel(10)

        for file_actor, file_name in zip(self.surface_actors, self.nifti_files):  # Assuming actors and filenames are paired
            poly_data = file_actor.GetMapper().GetInput()
            obb_tree.SetDataSet(poly_data)
            obb_tree.BuildLocator()

            # Compute intersection points
            intersection_points = vtk.vtkPoints()
            code = obb_tree.IntersectWithLine(start_point, end_point, intersection_points, None)

            if code == 1:  # Intersection found
                intersected_files.append(file_name)  # Add the file name to the list
                for i in range(intersection_points.GetNumberOfPoints()):
                    point = intersection_points.GetPoint(i)
                    # print(f"Intersection at: {point}")

                    # Visualize intersection points
                    self.add_intersection_marker(point,radius=self.marker_radius)

        # Update the file list with highlighted intersected files
        self.highlight_intersected_files(intersected_files)

        self.vtk_widget.GetRenderWindow().Render()


    def highlight_intersected_files(self, intersected_files):
        """Highlight the intersected files in the file list widget."""
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            item_name = item.text()
            intersected_base_names = [
                os.path.splitext(os.path.basename(file_path))[0] for file_path in intersected_files
            ]
            if item_name in intersected_base_names:
                # Highlight intersected files (red bold text)
                font = QFont()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(Qt.red)
            else:
                # Reset the style for non-intersected files
                font = QFont()
                font.setBold(False)
                item.setFont(font)
                item.setForeground(Qt.black)


    def add_intersection_marker(self, point,radius):
        """Add a marker to visualize intersection points."""
        sphere_source = vtk.vtkSphereSource()
        sphere_source.SetCenter(point)
        sphere_source.SetRadius(radius) 

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere_source.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.0, 1.0, 0.0)  # Green marker

        # Add marker actor and store it in the list
        self.vtk_renderer.AddActor(actor)
        self.intersection_markers.append(actor)

###################   UPDATE SLIDDERS VALUES WHEN MOVED    ########################

    def on_x_changed(self, value):
        """Update the X coordinate of the ray."""
        if self.ray_origin is None:
            return
        self.ray_origin = (value, self.ray_origin[1], self.ray_origin[2])
        self.x_label.setText(f"X: {value}") 
        self.create_ray()

    def on_y_changed(self, value):
        """Update the Y coordinate of the ray."""
        if self.ray_origin is None:
            return
        self.ray_origin = (self.ray_origin[0], value, self.ray_origin[2])
        self.y_label.setText(f"Y: {value}") 
        self.create_ray()

    def on_z_changed(self, value):
        """Update the Z coordinate of the ray."""
        if self.ray_origin is None:
            return
        self.ray_origin = (self.ray_origin[0], self.ray_origin[1], value)
        self.z_label.setText(f"Z: {value}")  
        self.create_ray()

    def on_radius_changed(self, value):
        """Update the radius value when slidder is moved."""
        self.marker_radius = value
        self.radius_label.setText(f"Radius : {self.marker_radius}")
        self.create_ray()

    def on_length_changed(self, value):
        """Update the length of the ray."""
        self.ray_length = value
        self.length_label.setText(f"Length: {value}") 
        self.create_ray()

    def on_azimuth_changed(self, value):
        """Update the Azimuth angle of the ray."""
        if self.ray_origin is None:
            return
        
        azimuth_rad = math.radians(value)
        # Adjust the ray direction based on the azimuth angle (around Z-axis)
        self.ray_direction = (math.cos(azimuth_rad), math.sin(azimuth_rad), self.ray_direction[2])
        # Update Azimuth label
        self.azimuth_label.setText(f"Azimuth: {value}°")
        self.create_ray()


    def on_elevation_changed(self, value):
        """Update the Elevation angle of the ray."""
        if self.ray_origin is None:
            return
        
        elevation_rad = math.radians(value)
        # Adjust the ray direction based on the elevation angle
        self.ray_direction = (self.ray_direction[0], self.ray_direction[1], math.sin(elevation_rad))
        # Update Elevation label
        self.elevation_label.setText(f"Elevation: {value}°")
        self.create_ray()



####################### OTHER FUNCTIONS #####################


    def reset_camera_to_default(self):
        """Reset the camera to the default view position, focal point, and view up."""
        camera = self.vtk_renderer.GetActiveCamera()
        camera.SetPosition(self.default_view_position)
        camera.SetFocalPoint(self.default_view_focal_point)
        camera.SetViewUp(self.default_view_up)
        self.vtk_widget.GetRenderWindow().Render()


    def go_back(self):
        """Go back to the previous view."""
        self.close()


    def toggle_full_screen(self):
        """Switch to full screen."""
        if self.is_full_screen:
            self.is_full_screen = False
            self.setWindowTitle("Render Window")
            
            # Dimensions small window
            window_width = 1280
            window_height = 720
            
            # Get screen dimensions
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()

            # Comput ecenter of the full screen 
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2

            self.showNormal() 
            self.setGeometry(x, y, window_width, window_height)
            vtk_width = self.vtk_widget.width()
            vtk_height = self.vtk_widget.height()
            
            # Apply dimensions to rendering window
            self.vtk_widget.GetRenderWindow().SetSize(vtk_width, vtk_height)
            self.vtk_widget.GetRenderWindow().Render() 
        else:
            self.is_full_screen = True
            self.setWindowTitle("Render Window (Full Screen)") 
            
            self.showFullScreen()
            
            vtk_width = self.vtk_widget.width()
            vtk_height = self.vtk_widget.height()
            self.vtk_widget.GetRenderWindow().SetSize(vtk_width, vtk_height)
            self.vtk_widget.GetRenderWindow().Render()  

        self.vtk_widget.GetRenderWindow().Render()


    def setup_key_event(self):
        """Set up the 'f' key event to toggle full-screen mode."""
        iren = self.vtk_widget.GetRenderWindow().GetInteractor()
        iren.AddObserver("KeyPressEvent", self.on_key_press)
        
    def on_key_press(self, obj, event):
        """Key event handling."""
        key = obj.GetKeySym() 
        if key == "f":  
            self.toggle_full_screen()

    def get_center_of_brain(self):
        """Calculate the center of the bounding box for the first NIfTI file."""
        reader = vtk.vtkNIFTIImageReader()
        reader.SetFileName(self.nifti_files[0])
        reader.Update()

        image_data = reader.GetOutput()
        bounds = image_data.GetBounds()

        # Calculate the center of the bounding box
        center_x = (bounds[0] + bounds[1]) / 2
        center_y = (bounds[2] + bounds[3]) / 2
        center_z = (bounds[4] + bounds[5]) / 2

        return (center_x, center_y, center_z)


    def observe_camera(self):
        """Set up an observer on the camera to update UI in real time."""
        camera = self.vtk_renderer.GetActiveCamera()
        camera.AddObserver('ModifiedEvent', self.update_camera_position)


    def truncate_coordinates(self,coords, decimals=2):
        """Round the coordinates to the specified number of decimal places."""
        return tuple(round(coord, decimals) for coord in coords)


    def update_camera_position(self, caller=None, event=None):
        """Update camera position, focal point, and view up in real-time."""
        camera = self.vtk_renderer.GetActiveCamera()
        position = camera.GetPosition()
        focal_point = camera.GetFocalPoint()
        view_up = camera.GetViewUp()
        position = self.truncate_coordinates(position, decimals=2)
        focal_point = self.truncate_coordinates(focal_point, decimals=2)
        view_up = self.truncate_coordinates(view_up, decimals=2)
        self.camera_position_label.setText(f"Position : {position}")
        self.camera_focal_point_label.setText(f"Focal Point : {focal_point}")
        self.camera_view_up_label.setText(f"Top view : {view_up}")


    def get_bounds_from_first_nifti(self):
        """Get bounds from the first NIfTI file for cube axes."""
        reader = vtk.vtkNIFTIImageReader()
        reader.SetFileName(self.nifti_files[0])
        reader.Update()
        image_data = reader.GetOutput()
        return image_data.GetBounds()

        
    def create_volume_actor(self, nifti_file):
        """Create and return a volume actor with a random color for each NIfTI file."""
        reader = vtk.vtkNIFTIImageReader()
        reader.SetFileName(nifti_file)
        reader.Update()

        # Volume mapper
        volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
        volume_mapper.SetInputConnection(reader.GetOutputPort())

        # Volume color transfer function
        color_func = vtk.vtkColorTransferFunction()

        # Generate a random color 
        r, g, b = generate_random_color()
        # Add a single color for the entire volume 
        color_func.AddRGBPoint(0, r, g, b) 
        color_func.AddRGBPoint(255, r, g, b)  # Ensure the entire range uses the same color

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
        """Toggle between surface and volume rendering."""
        self.is_volume_rendering = not self.is_volume_rendering

        if self.is_volume_rendering:
            for actor in self.surface_actors:
                self.vtk_renderer.RemoveActor(actor)
            for volume_actor in self.volume_actors:
                self.vtk_renderer.AddActor(volume_actor)
            self.volume_button.setText("Rendu Surface")
        else:
            for volume_actor in self.volume_actors:
                self.vtk_renderer.RemoveActor(volume_actor)
            for actor, label in self.labels:
                self.vtk_renderer.AddActor(actor)
            self.volume_button.setText("Rendu Volume")

        self.vtk_widget.GetRenderWindow().Render()


    def setup_mouse_move(self):
        """Set up mouse move interactor for showing tooltips."""
        def on_mouse_move(interactor, event):
            x, y = interactor.GetEventPosition()
            picker = vtk.vtkPropPicker()
            picker.Pick(x, y, 0, self.vtk_renderer)
            actor = picker.GetActor()

            if actor:
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



#################      ORGAN OPACITY CONTROL    ##########################
class OrganControlDialog(QDialog):
    """Dialog for adjusting the opacity and visibility of a 3D organ model."""
    
    def __init__(self, parent, actor, label):
        super().__init__(parent)
        self.actor = actor
        self.label = label
        self.setWindowTitle(f"Controls for {label}")
        self.setGeometry(300, 300, 300, 200)

        # Layout for the dialog
        layout = QFormLayout()

        # Add slider for opacity
        self.opacity_slider = QSlider()
        self.opacity_slider.setOrientation(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.update_opacity)
        layout.addRow("Opacity:", self.opacity_slider)

        # Add checkbox for visibility toggle
        self.visibility_checkbox = QCheckBox("Toggle")
        self.visibility_checkbox.setChecked(True)
        self.visibility_checkbox.toggled.connect(self.toggle_visibility)
        layout.addRow("Visible:", self.visibility_checkbox)

        # Button to confirm changes
        self.validate_button = QPushButton("Confirm")
        self.validate_button.clicked.connect(self.apply_changes)
        layout.addRow(self.validate_button)

        self.setLayout(layout)

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
        """Apply the changes when the 'Confirm' button is clicked."""
        self.accept() 



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_folder_with_nii_files>")
        sys.exit(1)

    folder = sys.argv[1]
    app = QApplication(sys.argv)
    main_window = MainWindow(folder)
    main_window.show()
    sys.exit(app.exec_())