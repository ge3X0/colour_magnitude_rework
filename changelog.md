- Created StarEllipse class, which replaces "tag" system of tkinter
  - vmag1 and vmag2 hold user defined magnitudes of stars, replacing stars_mag_list variable
  - flux1 and flux2 hold the flux values of one star, replacing stars_flux variable
  - Flags for status of ellipse (selected, deselected, labeled, not labeled) are introduced
  - Colour (Pens) of ellipses change automatically on changing status

- util.py is mostly copied from auxiliary_functions.py, changes were made on:
  - prints and quiet-parameters were mostly removed
  - fits_to_array
    - np.flip is used to display image correctly (not inverted)
    - conversion to np.float64 is not necessary, as fits already loads in this format
    - list comprehension is used instead of for loop
  - get_fits_names:
    - Set to use pathlib.Path
    - glob-method optimized

- StarGraphicsView represents the display class for the image
  - mousePressEvent replaces mouse interactions with tkinter canvas:
    - Left-click for toggle selection
    - Right-click for setting user defined magnitudes
    - Middle-click for info has been replaced by hover:
      - Each labeled ellipse shows its user defined magnitudes by hovering ofer it
  - wheelEvent
    - Implements zooming-functionality. This replaces the rescaling functionality for smaller monitors

- PlotWindow creates a new Window for displaying plots
  - self.mag_short and self.mag_long are used for saving fhd-plot data
  - plot_offset plots offset-plots