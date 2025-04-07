## Changed from

- plot_fhd:
  - Moved to PlotWindow
  - parameter quit_save removed: Saving is now done via button on PlotDialog
  - parameter stars_mag_list removed: mag values are now part of StarEllipse class. Parameter was only accessed iteratively (not via np broadcast)
  - parameter stars_flux removed: flux is now part of StarEllipse class. Parameter was only accessed iteratively (not via np broadcast)
  - parameter deselected removed: selection status is managed via flags in StarEllipse class.
  - n_ref_stars2 variable removed: unused
  - plot conversion functions removed: Plot was never shown
  - mag_short and mag_long are now members of PlotDialog (used for saving plot fhd data)
  - removed tkinter
  - moved writing to .dat-file from method to MainWindow::save_fhd_files
- init_fhd:
  - Moved to MainWindow
  - parameters root, canvas removed: part of tkinter
  - parameter fit_list removed: unused
  - parameter ask_rescale removed: rescaling obsolete due to zoom
  - parameters short_wave_colour, long_wave_colour, offset_short_wave, offset_long_wave, FWHM, ratio_gauss, factor_thresholf, r_aperture removed: part of parent class MainWindow
  - repeating np.pad-method abstracted and moved to MainWindow::shift_data
  - Button definition of tkinter moved to init of parent class MainWindow and replaced with PySide6 QPushButton and Slots
  - aux.plot_offset moved to PlotWindow class
  - deselect_all connected to toggle_all of MainWindow
  - stars_flux "global" variable removed: flux is now member of StarEllipse
  - deselected variable removed: selection is managed by StarEllipse status
  - stars_mag_list variable removed: user defined magnitude is now member of StarEllipse
    - DRAWBACK: This occupies more memory, as two float64 are reserved per StarEllipse-Instance, as for demand-allocated stars_mag_list
  - arr2d-construction through list-comprehension
  - photutils-import modernized (sub-modules set correctly)
  - print calls removed
  - rescaling removed: obsolete due to zoom
  - canvas.create_oval replaced with StarEllipse creation
  - tags are now part of StarEllipse class
  - canvas.bind-buttons moved to StarGraphicsView mousePressed Slot
- deselect_all:
  - renamed to toggle_all and moved to MainWindow
  - complete rewrite using StarEllipse status flags
- tag_info:
  - obsolete, user defined magnitudes are displayed via hover
- deselect_star:
  - renamed to toggle_selection and moved to StarGraphicsView
  - complete rewrite using StarEllipse status flags

## Changed to

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