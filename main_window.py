from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QGraphicsScene, QInputDialog, QMessageBox, QDoubleSpinBox, QLabel
from PySide6.QtCore import QRect, QPoint, Slot
import numpy as np
from astropy.io import fits
from photutils.aperture import CircularAperture, aperture_photometry

import util

import tomllib
from pathlib import Path
from datetime import datetime

from PIL import Image

from star_ellipse import StarEllipse, StarStatus
from star_graphics_view import StarGraphicsView
from plot_window import PlotWindow


class MainWindow(QWidget):
    # TODO: save selection and values
    # TODO: dump log if wanted

    @staticmethod
    def shift_data(data, n_len, offset, pixel):
        """Extracted from old script, as this code block was used multiple times"""
        for i in range(n_len):
            upper0 = abs(max(0, offset[i, 0]))
            lower0 = abs(min(0, offset[i, 0]))
            upper1 = abs(max(0, offset[i, 1]))
            lower1 = abs(max(0, offset[i, 1]))
            tmp = np.pad(data[i], ((upper0, lower0), (upper1, lower1)), mode='constant')
            data[i] = tmp[lower0: pixel[0] + lower0, lower1:pixel[1] + lower1]

    def __init__(self):
        """Setup Gui and calls self.setup()"""

        super().__init__()

        self.plot_windows = set()
        self.logger = [f"Started program @ {datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}"]

        with open("input_cmd.toml", "rb") as fl:
            self.input_cmd = tomllib.load(fl)

        # Setup Graphics View

        self.scene = QGraphicsScene()
        self.graphics_view = StarGraphicsView(self.scene)
        self.graphics_view.star_chosen.connect(self.info_star)

        # Setup UI

        button_stack = QVBoxLayout()

        reddening_label = QLabel("Reddening")
        self.reddening_box = QDoubleSpinBox(value=0.0)
        button_stack.addWidget(reddening_label)
        button_stack.addWidget(self.reddening_box)

        button_offset_master = QPushButton("Masters Offset")
        button_offset_master.clicked.connect(self.button_offset_master_clicked)
        button_stack.addWidget(button_offset_master)

        button_offset_short = QPushButton(f"Plot {self.input_cmd['short_colour']} Offset")
        button_offset_short.clicked.connect(self.button_offset_short_clicked)
        button_stack.addWidget(button_offset_short)

        button_offset_long = QPushButton(f"Plot {self.input_cmd['long_colour']} Offset")
        button_offset_long.clicked.connect(self.button_offset_long_clicked)
        button_stack.addWidget(button_offset_long)

        button_toggle_selection = QPushButton("Toggle Selection")
        button_toggle_selection.clicked.connect(self.button_toggle_selection_clicked)
        button_stack.addWidget(button_toggle_selection)

        button_preview = QPushButton("FHD Diagram")
        button_preview.clicked.connect(self.button_preview_clicked)
        button_stack.addWidget(button_preview)

        button_stack.addStretch()

        self.center = QHBoxLayout(self)
        self.center.addWidget(self.graphics_view)
        self.center.addLayout(button_stack)

        self.setup()

    def create_plot_window(self) -> PlotWindow:
        plot_win = PlotWindow()
        plot_win.closed.connect(self.plot_window_closed)

        self.plot_windows.add(plot_win)
        return plot_win

    def dark_correction(self, scidata: np.ndarray, n_short_light: int):
        if lst := util.get_fits_names(self.input_cmd["path_dark_short"]):
            frames = util.fits_to_array(lst)
            scidata[:n_short_light] = util.dark_correction(scidata[:n_short_light], frames)
        else:
            QMessageBox.warning(self, "File not found", "Could not find files for short wave dark correction")

        if lst := util.get_fits_names(self.input_cmd["path_dark_long"]):
            frames = util.fits_to_array(lst)
            scidata[n_short_light:] = util.dark_correction(scidata[n_short_light:], frames)
        else:
            QMessageBox.warning(self, "File not found", "Could not find files for long wave dark correction")

    def flat_fielding(self, scidata: np.ndarray, n_short_light: int):
        # Define identity lambda if not dark correction can/should be used for flats
        dark_correct_flats = lambda x: x

        # Define dark_correct_flats otherwise
        if self.input_cmd["do_dark_flat"]:
            if lst := util.get_fits_names(self.input_cmd["path_dark_flat"]):
                flat_darks = util.fits_to_array(lst)
                dark_correct_flats = lambda x: util.dark_correction(x, flat_darks)
            else:
                QMessageBox.warning(self, "File not found", "Could not find files for dark correction of flats")

        # Flatfielding starts here
        if lst := util.get_fits_names(self.input_cmd["path_flat_short"]):
            frames = dark_correct_flats(util.fits_to_array(lst))
            scidata[:n_short_light] = util.flat_correction(scidata[:n_short_light], frames)
        else:
            QMessageBox.warning(self, "File not found", "Could not find files for short wave flatfielding")

        if lst := util.get_fits_names(self.input_cmd["path_flat_long"]):
            frames = dark_correct_flats(util.fits_to_array(lst))
            scidata[n_short_light:] = util.flat_correction(scidata[n_short_light:], frames)
        else:
            QMessageBox.warning(self, "Files not found", "Could not find files for long wave flatfielding")

    def master_wave(self, data: np.ndarray, n_light: int, pixel) -> tuple[np.ndarray, np.ndarray]:
        if n_light > 1:
            _, median, std = util.get_stats(data)
            wave_offset = util.get_offset(data, median, std, 0)
            self.shift_data(data, n_light, wave_offset, pixel)
            master_wave = util.create_master(data)
        else:
            wave_offset = np.zeros((n_light, 2), dtype=int)
            master_wave = data

        return master_wave, wave_offset

    def setup(self):
        self.n_stars_min = 1

        fit_list = util.get_fits_names(self.input_cmd["path_light_short"])
        short_wave_fit_list = fit_list
        n_short_light = len(fit_list)

        if n_short_light == 0:
            QMessageBox.warning(self, "File not found", f"Could not find short wave files at {self.input_cmd['path_light_short']}")
            return

        long_wave_fit_list = util.get_fits_names(self.input_cmd["path_light_long"])
        n_long_light = len(long_wave_fit_list)
        fit_list.extend(long_wave_fit_list)

        if n_long_light == 0:
            QMessageBox.warning(self, "File not found", f"Could not find short wave files at {self.input_cmd['path_light_long']}")
            return

        scidata = util.fits_to_array(fit_list)

        pixel = scidata[0].shape

        if self.input_cmd["do_dark"]:
            self.dark_correction(scidata, n_short_light)

        if self.input_cmd["do_flat"]:
            self.flat_fielding(scidata, n_short_light)

        # here the master lights are created, after each picture was offset-aligned regarding your input
        master_short_wave, self.short_wave_offset = self.master_wave(scidata[:n_short_light, :, :], n_short_light, pixel)
        master_long_wave, self.long_wave_offset = self.master_wave(scidata[n_short_light:n_short_light + n_long_light, :, :], n_long_light, pixel)

        # TODO no copying
        scidata = np.zeros((2, pixel[0], pixel[1]))
        scidata[0, :, :] = master_short_wave
        scidata[1, :, :] = master_long_wave

        del master_long_wave, master_short_wave

        self.save_fits_files(scidata, n_short_light, n_long_light, short_wave_fit_list, long_wave_fit_list)

        reference_fit = 0  # 0 = short wavelength; 1 = long wavelength
        scidata_frame = scidata[reference_fit]

        # subtract sky background and set negative values to 0
        _, median, _ = util.get_stats(scidata_frame)
        data2show = np.maximum(np.zeros(scidata_frame.shape), scidata_frame - median)

        # equalize the histogram or use log scaling for nicer display of image
        # array2show = np.uint16(aux.histeq(data2show,rescaled_pixel)/255)    # convert from 16 Bit to 8 Bit only for display
        array2show = np.uint16(util.hist_log(data2show) / 255)  # convert from 16 Bit to 8 Bit only for display

        image2show = Image.fromarray(array2show, mode='I;16')
        self.scene.addPixmap(image2show.toqpixmap())

        self.init_fhd(reference_fit, scidata, pixel)

    def init_fhd(self, reference_fit, scidata, pixel):
        """Initialize pictures and data"""

        n_fits = len(scidata[:, 0, 0])
        FWHM = self.input_cmd["FWHM"]
        r_aperture = self.input_cmd["r_aperture"]
        _, median, std = util.get_stats(scidata)
        self.offset = util.get_offset(scidata, median, std, reference_fit)

        # shift and pad the images; we want the original number of pixel -> only part of the padded array needed
        self.shift_data(scidata, n_fits, self.offset, pixel)

        # the stars of the images are found here and the positions are saved
        _, self.n_stars_min, self.positions = util.detect_star(self.n_stars_min, scidata, median, std, FWHM, self.input_cmd["ratio"], self.input_cmd["threshold"])
        stars_flux = np.zeros((n_fits, self.n_stars_min))

        # stars flux are only numbers, they are made from a circle around the position of a star and the sum of it.
        for i in range(n_fits):
            arr2d = [
                [self.positions[i, a, 0], self.positions[i, a, 1]]
                for a in range(len(self.positions[i, :, 0]))
            ]

            apertures = CircularAperture(arr2d, r=r_aperture * FWHM)  # the area, where the flux is going to be taken from
            phot = aperture_photometry(scidata[i, :, :] - median[i], apertures)  # the numbers are generated from the specific area of 'apertures'
            stars_flux[i, :] = phot['aperture_sum'][0:self.n_stars_min]  # numbers, that represent the luminosity of a star. Not real flux, but similar

        # creating the ovals around the stars for user input
        for j in range(self.n_stars_min):
            e = StarEllipse(
                QRect(
                    QPoint(self.positions[reference_fit, j, 0] - 3 / 2 * r_aperture * FWHM,
                           self.positions[reference_fit, j, 1] - 3 / 2 * r_aperture * FWHM,),
                    QPoint(self.positions[reference_fit, j, 0] + 3 / 2 * r_aperture * FWHM,
                           self.positions[reference_fit, j, 1] + 3 / 2 * r_aperture * FWHM,)
                ),
            )
            e.index = j
            e.flux1 = stars_flux[0, j]
            e.flux2 = stars_flux[1, j]

            self.scene.addItem(e)

        self.logger.append(f"""
        Found {self.n_stars_min} Stars
        Select the not included stars by left clicking and put in the magnitude via right clicking and then typing in the console. Leave blank for no input
        The colours mean: green - in the cluster ; red - not in the cluster ; blue - magnitude has been typed in ; orange - magnitude is given, but not in the cluster
        Controls are: Left click - deselect ; right click - type in magnitude
        """)

    def save_fits_files(self, scidata, n_short_light, n_long_light, short_wave_FIT_list, long_wave_FIT_list):
        path_save = Path(self.input_cmd["path_result"])

        if not path_save.exists():
            path_save.mkdir(parents=True)

        timestamp = datetime.now()

        hdulist_short = fits.HDUList(fits.PrimaryHDU(data=scidata[0, :, :]))
        with fits.open(short_wave_FIT_list[0]) as hdul:
            hdulist_short[0].header = hdul[0].header

        hdulist_short[0].header['BZERO'] = 0.0
        hdulist_short[0].header['SNAPSHOT'] = n_short_light
        hdulist_short[0].header['Date'] = timestamp.strftime("%Y-%m-%d")
        hdulist_short[0].header['Note'] = 'Created by colour_magnitude_diagram.py'

        hdulist_long = fits.HDUList(fits.PrimaryHDU(data=scidata[1, :, :]))
        with fits.open(long_wave_FIT_list[0]) as hdul:
            hdulist_long[0].header = hdul[0].header

        hdulist_long[0].header['BZERO'] = 0.0
        hdulist_long[0].header['SNAPSHOT'] = n_long_light
        hdulist_long[0].header['Date'] = timestamp.strftime("%Y-%m-%d")
        hdulist_long[0].header['Note'] = 'Created by colour_magnitude_diagram.py'

        tme = timestamp.strftime("%Y-%m-%dT%H-%M-%S")

        hdulist_short.writeto(path_save / f"{self.input_cmd['short_colour']}_{tme}.fits", overwrite=True)
        hdulist_long.writeto(path_save / f"{self.input_cmd['long_colour']}_{tme}.fits", overwrite=True)

    @Slot()
    def button_offset_master_clicked(self):
        plot_win = self.create_plot_window()
        plot_win.plot_offset(self.offset)
        plot_win.show()

    @Slot()
    def button_offset_short_clicked(self):
        plot_win = self.create_plot_window()
        plot_win.plot_offset(self.short_wave_offset)
        plot_win.show()

    @Slot()
    def button_offset_long_clicked(self):
        plot_win = self.create_plot_window()
        plot_win.plot_offset(self.long_wave_offset)
        plot_win.show()

    @Slot()
    def button_toggle_selection_clicked(self):
        """Toggles selection of ALL Stars"""
        for star in self.graphics_view.stars():
            star.status ^= StarStatus.Selected

    @Slot()
    def button_preview_clicked(self):
        plot_win = self.create_plot_window()
        plot_win.saving.connect(self.save_fhd_files)

        plot_win.plot_fhd(self.n_stars_min, list(self.graphics_view.stars()), self.input_cmd, self.reddening_box.value())
        plot_win.show()

    @Slot(StarEllipse)
    def info_star(self, star: StarEllipse):
        """Set values of one star"""

        # Ask for both values

        typed_mag_1, ok = QInputDialog.getDouble(self, "Input short colour", f"Input {self.input_cmd['short_colour']}", value=star.vmag1, decimals=3)
        if not ok:
            QMessageBox.warning(self, "Aborting", "Expected valid floating point number")
            return

        typed_mag_2, ok = QInputDialog.getDouble(self, "Input long colour", f"Input {self.input_cmd['long_colour']}", value=star.vmag2, decimals=3)
        if not ok:
            QMessageBox.warning(self, "Aborting", "Expected valid floating point number")
            return

        # Update star
        star.vmag1 = typed_mag_1
        star.vmag2 = typed_mag_2

        # Change status: Colour etc. will be adjusted automatically

        # Unset star if both values are 0
        if typed_mag_1 == 0.0 and typed_mag_2 == 0.0:
            self.logger.append(f"Unset {star.index}")
            star.status &= ~StarStatus.Labeled
            star.setToolTip("")
        else:
            self.logger.append(f"Set {star.index} to {typed_mag_1} and {typed_mag_2}")
            star.status |= StarStatus.Labeled
            star.setToolTip(f"{self.input_cmd['short_colour']}: {typed_mag_1} | {self.input_cmd['long_colour']}: {typed_mag_2}")

    @Slot(np.ndarray, np.ndarray)
    def save_fhd_files(self, mag_short: np.ndarray, mag_long: np.ndarray):
        """Called from PlotWindow to save fhd data"""

        swc = self.input_cmd["short_colour"]
        lwc = self.input_cmd["long_colour"]

        save_file = Path(self.input_cmd["path_result"]) / f"colour_mag_diagram_{swc}-{lwc}_{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.dat"
        if not save_file.exists():
            save_file.parent.mkdir(parents=True, exist_ok=True)

        with save_file.open("w+") as fl:
            fl.write(f"#ID\tx[px]\ty[px]\tflux_{swc}[ADU]\tflux_{lwc}[ADU]\t{swc}_mag\t{lwc}_mag\n")
            lines = [
                f"{star.index}\t{self.positions[0,star.index,0]}\t{self.positions[0,star.index,1]}\t"
                f"{star.flux1}\t{star.flux2}\t"
                f"{mag_short[star.index]}\t{mag_long[star.index]}\n"
                for star in filter(lambda x: StarStatus.Selected in x.status, self.graphics_view.stars())]
            fl.writelines(lines)

        QMessageBox.information(self, "Data saved", f"Data written to {save_file}")

    @Slot(QWidget)
    def plot_window_closed(self, win: QWidget):
        """Delete PlotWindows from set to free memory"""
        self.plot_windows.remove(win)



