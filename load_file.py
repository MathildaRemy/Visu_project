import vtk
import sys
from vtkmodules.util import numpy_support  # Correct import for VTK 9.0+


def main(filename):
    """
    Main function to load NIFTI data, render a 3D model, and display it interactively.
    
    Arguments:
    - filename: Path to the .nii file.
    """
    # Load the NIFTI data
    reader_src = vtk.vtkNIFTIImageReader()
    reader_src.SetFileName(filename)
    reader_src.Update()
    data = reader_src.GetOutput()

    # Get the scalar data and print its range
    raw_data = data.GetPointData().GetScalars()
    raw_array = numpy_support.vtk_to_numpy(raw_data)  # Convert to NumPy for analysis
    print(f"Data range: {raw_array.min()} to {raw_array.max()}")

    # Generate 3D mesh using the Marching Cubes algorithm
    contour = vtk.vtkMarchingCubes()
    contour.SetInputData(data)
    contour.ComputeNormalsOn()
    contour.ComputeGradientsOn()
    contour.SetValue(0, 0.5)  # Threshold value for surface extraction

    # Create mapper and actor for rendering
    con_mapper = vtk.vtkPolyDataMapper()
    con_mapper.SetInputConnection(contour.GetOutputPort())

    actor = vtk.vtkActor()
    actor.SetMapper(con_mapper)

    # Create a renderer and set up the camera
    renderer = vtk.vtkRenderer()
    bounds = data.GetBounds()  # Get the dataset's bounding box
    data_size = [bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]]

    # Estimate a good camera distance based on data size
    camera_distance = max(data_size) * 1.5
    center = data.GetCenter()

    # Configure the camera
    camera = vtk.vtkCamera()
    camera.SetPosition(0, 0, camera_distance)  # Set camera at a safe distance
    camera.SetFocalPoint(center[0], center[1], center[2])  # Focus on data center
    camera.SetViewUp(0, 1, 0)  # Set Y-axis as up
    camera.SetClippingRange(camera_distance / 2, camera_distance * 2)  # Near/far clipping
    camera.SetViewAngle(45)  # Field of view

    # Add the actor and camera to the renderer
    renderer.SetBackground(0.0, 0.0, 0.0)  # Black background
    renderer.SetActiveCamera(camera)
    renderer.AddActor(actor)

    # Create a render window
    ren_win = vtk.vtkRenderWindow()
    ren_win.AddRenderer(renderer)

    # Create and configure an interactor
    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)

    # Render the window and start the interactive session
    ren_win.Render()
    iren.Initialize()
    iren.Start()


if __name__ == "__main__":
    # Ensure a file path is provided as an argument
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_nifti_file>")
        sys.exit(1)

    main(sys.argv[1])