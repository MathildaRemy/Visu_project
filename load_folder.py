import vtk
import sys
import os
import random


def load_nifti_as_actor(filename, threshold, color):
    """
    Load a NIFTI file, extract a surface using Marching Cubes, and return an actor for rendering.
    :param filename: Path to the .nii file.
    :param threshold: Threshold value for the Marching Cubes algorithm.
    :param color: Tuple (R, G, B) defining the color of the actor.
    :return: vtkActor representing the surface.
    """
    # Read the NIFTI file
    reader = vtk.vtkNIFTIImageReader()
    reader.SetFileName(filename)
    reader.Update()

    # Generate 3D mesh using Marching Cubes
    contour = vtk.vtkMarchingCubes()
    contour.SetInputConnection(reader.GetOutputPort())
    contour.ComputeNormalsOn()
    contour.ComputeGradientsOn()
    contour.SetValue(0, threshold)  # Apply threshold for surface extraction

    # Create mapper
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(contour.GetOutputPort())

    # Create actor and set color
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(color)  # Set the actor's unique color

    return actor


def generate_random_color():
    """
    Generate a random color as a tuple of RGB values.
    :return: Tuple (R, G, B) with values between 0 and 1.
    """
    return random.random(), random.random(), random.random()


def main(folder_path):
    """
    Main function to load and display all NIFTI files in a folder.
    :param folder_path: Path to the folder containing NIFTI files.
    """
    # Get all .nii files in the folder
    nifti_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.nii.gz')]


    if not nifti_files:
        print(f"No .nii files found in the folder: {folder_path}")
        sys.exit(1)

    print(f"Loading {len(nifti_files)} .nii files from {folder_path}")

    # Create renderer and add actors
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(0.0, 0.0, 0.0)  # Black background

    for nifti_file in nifti_files:
        color = generate_random_color()
        actor = load_nifti_as_actor(nifti_file, threshold=0.5, color=color)
        renderer.AddActor(actor)

    # Create render window and interactor
    ren_win = vtk.vtkRenderWindow()
    ren_win.AddRenderer(renderer)
    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)

    # Calculate camera settings based on the first dataset
    reader = vtk.vtkNIFTIImageReader()
    reader.SetFileName(nifti_files[0])
    reader.Update()
    data = reader.GetOutput()
    bounds = data.GetBounds()
    data_size = [bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]]
    camera_distance = max(data_size) * 1.5
    center = data.GetCenter()

    # Set up the camera
    camera = vtk.vtkCamera()
    camera.SetPosition(0, 0, camera_distance)
    camera.SetFocalPoint(center[0], center[1], center[2])
    camera.SetViewUp(0, 1, 0)
    camera.SetClippingRange(camera_distance / 2, camera_distance * 2)
    camera.SetViewAngle(45)
    renderer.SetActiveCamera(camera)

    # Render and start interaction
    ren_win.Render()
    iren.Initialize()
    iren.Start()


if __name__ == "__main__":
    # Ensure the script is called with one folder argument
    if len(sys.argv) != 2:
        print("Usage: python load_folder.py <path_to_folder_with_nii_files>")
        sys.exit(1)

    main(sys.argv[1])
