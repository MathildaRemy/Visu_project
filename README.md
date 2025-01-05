# **Radiotherapy Visualisation and Planning Application**

## **Overview**
The **NIFTI Visualisation Application** is a Python-based desktop application for rendering and interacting with 3D medical imaging data in NIfTI (`.nii.gz`) format. It allows users to visualize volumetric data, interact with 3D renderings, toggle stereo rendering modes, and simulate ray interactions with the models.

This application is built using **PyQt5** for the GUI and **VTK** for 3D rendering.

---

## **Features**

1. **NIfTI File Management:**
   - Automatically scans and lists `.nii.gz` files from a specified folder.
   - Users can select multiple files to render.

2. **3D Rendering:**
   - Surface and volume rendering of selected NIfTI files.
   - Toggle between stereo and normal rendering modes.

3. **Ray Simulation:**
   - Simulate rays through 3D models.
   - Interactive sliders to control ray position, direction, length, and radius.
   - Highlights intersections with 3D objects.

4. **Organ Control:**
   - Adjust opacity and visibility of individual models using a dedicated dialog.

5. **Camera Control:**
   - Real-time camera updates for position, focal point, and view-up direction.
   - Reset the camera to the default view.

6. **User-Friendly Interface:**
   - Simple GUI with labeled controls for rendering and interaction.
   - Includes tooltips and pop-up dialogs for enhanced usability.

---

## **Installation**

### **Prerequisites**
- Python 3.7 or higher
- The following Python libraries:
  - `PyQt5`
  - `vtk`
  - `numpy` (optional, if additional processing is required)

### **Steps**
1. Clone or download the repository:
   ```bash
   git clone https://github.com/your-repo/nifti-visualisation-app.git
   cd nifti-visualisation-app
