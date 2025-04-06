from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QGraphicsScene, QInputDialog, QMessageBox, QDoubleSpinBox, QLabel
from PySide6.QtCore import QRect, QPoint, Slot
import numpy as np
from astropy.io import fits
from photutils.aperture import CircularAperture, aperture_photometry

import util

import tomllib
from pathlib import Path
from datetime import date, datetime

from PIL import Image

from star_ellipse import StarEllipse, StarStatus
from star_graphics_view import StarGraphicsView
from plot_window import PlotWindow


class MainWindow(QWidget):
    # TODO: show mag via tooltip on hove

    def init_fhd(self, reference_fit, scidata, n_fits, pixel):
        """Initialize pictures and data"""

        FWHM = self.input_cmd["FWHM"]
        r_aperture = self.input_cmd["r_aperture"]
        mean, median, std = util.get_stats(scidata)
        self.offset = util.get_offset(scidata, median, std, reference_fit)

        # shift and pad the images; we want the original number of pixel -> only part of the padded array needed
        self.shift_data(scidata, n_fits, self.offset, pixel)

        # the stars of the images are found here and the positions are saved
        _, self.n_stars_min, self.positions = util.detect_star(self.n_stars_min, scidata, median, std, FWHM, self.input_cmd["ratio"], self.input_cmd["threshold"])
        self.stars_flux = np.zeros((n_fits, self.n_stars_min))
        self.stars_mag_list = []

        # stars flux are only numbers, they are made from a circle around the position of a star and the sum of it.
        for i in range(n_fits):
            arr2d = []
            for a in range(len(self.positions[i, :, 0])):
                arr2d.append([self.positions[i, a, 0], self.positions[i, a, 1]])

            apertures = CircularAperture(arr2d, r=r_aperture * FWHM)  # the area, where the flux is going to be taken from
            phot = aperture_photometry(scidata[i, :, :] - median[i], apertures)  # the numbers are generated from the specific area of 'apertures'
            self.stars_flux[i, :] = phot['aperture_sum'][0:self.n_stars_min]  # numbers, that represent the luminosity of a star. Not real flux, but similar

        # creating the ovals around the stars for user input
        for j in range(self.n_stars_min):
            e = StarEllipse(QRect(
                    QPoint(self.positions[reference_fit, j, 0] - 3 / 2 * r_aperture * FWHM,
                           self.positions[reference_fit, j, 1] - 3 / 2 * r_aperture * FWHM,),
                    QPoint(self.positions[reference_fit, j, 0] + 3 / 2 * r_aperture * FWHM,
                           self.positions[reference_fit, j, 1] + 3 / 2 * r_aperture * FWHM,)
                )
            )
            e.setData(0, j)
            # TODO: unused?
            e.setData(1, self.stars_flux[reference_fit, j])

            self.scene.addItem(e)

        self.logger.append(f"""
        Found {self.n_stars_min} Stars
        Select the not included stars by left clicking and put in the magnitude via right clicking and then typing in the console. Leave blank for no input
        The colours mean: green - in the cluster ; red - not in the cluster ; blue - magnitude has been typed in ; orange - magnitude is given, but not in the cluster
        Controls are: Left click - deselect ; right click - type in magnitude
        """)



    def shift_data(self, data, n_len, offset, pixel):
        for i in range(n_len):
            upper0 = abs(max(0, offset[i, 0]))
            lower0 = abs(min(0, offset[i, 0]))
            upper1 = abs(max(0, offset[i, 1]))
            lower1 = abs(max(0, offset[i, 1]))
            tmp = np.pad(data[i], ((upper0, lower0), (upper1, lower1)), mode='constant')
            data[i] = tmp[lower0: pixel[0] + lower0, lower1:pixel[1] + lower1]


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

    def setup(self):
        self.n_stars_min = 1

        fit_list = util.get_fits_names(self.input_cmd["path_light_short"])
        short_wave_FIT_list = fit_list
        n_short_light = len(short_wave_FIT_list)

        long_wave_FIT_list = util.get_fits_names(self.input_cmd["path_light_long"])
        n_long_light = len(long_wave_FIT_list)
        fit_list.extend(long_wave_FIT_list)

        scidata = util.fits_to_array(fit_list)
        pixel = scidata[0].shape

        frames = None

        # dark correction
        #
        if self.input_cmd["do_dark"]:
            if lst := util.get_fits_names(self.input_cmd["path_dark_short"]):
                frames = util.fits_to_array(lst)
                scidata[:n_short_light] = util.dark_correction(scidata[:n_short_light], frames)
            else:
                self.logger.append("No dark correction files found for short wavelengths")

            if lst := util.get_fits_names(self.input_cmd["path_dark_long"]):
                frames = util.fits_to_array(lst)
                scidata[n_short_light:] = util.dark_correction(scidata[n_short_light:], frames)
            else:
                self.logger.append("No dark correction files found for long wavelengths")

        # flat fielding
        #
        if self.input_cmd["do_flat"]:
            dark_correct_flats = lambda x: x

            if self.input_cmd["do_dark_flat"]:
                if lst := util.get_fits_names(self.input_cmd["path_dark_flat"]):
                    flat_darks = util.fits_to_array(lst)
                    dark_correct_flats = lambda x: util.dark_correction(x, flat_darks)
                else:
                    self.logger.append("No dark correction files were found for flats")

            if lst := util.get_fits_names(self.input_cmd["path_flat_short"]):
                frames = dark_correct_flats(util.fits_to_array(lst))
                scidata[:n_short_light] = util.flat_correction(scidata[:n_short_light], frames)
            else:
                self.logger.append("No flatfielding files found for short wavelengths")

            if lst := util.get_fits_names(self.input_cmd["path_flat_long"]):
                frames = dark_correct_flats(util.fits_to_array(lst))
                scidata[n_short_light:] = util.flat_correction(scidata[n_short_light:], frames)
            else:
                self.logger.append("No flatfielding files found for long wavelengths")

        if frames:
            del frames

        reference_fit = 0  # 0 = short wavelength; 1 = long wavelength

        # fit_list_temp = fit_list
        # fit_list = []

        # here the master lights are created, after each picture was offset-aligned regarding your input
        short_wave_scidata = scidata[:n_short_light, :, :]

        if n_short_light > 1:
            _, median, std = util.get_stats(short_wave_scidata)
            self.short_wave_offset = util.get_offset(short_wave_scidata, median, std, 0)
            self.shift_data(short_wave_scidata, n_short_light, self.short_wave_offset, pixel)
            master_short_wave = util.create_master(short_wave_scidata)
        else:
            self.short_wave_offset = np.zeros((n_short_light, 2), dtype=int)
            master_short_wave = short_wave_scidata

        long_wave_scidata = scidata[n_short_light:n_long_light + n_short_light, :, :]

        if n_long_light > 1:
            _, median, std = util.get_stats(long_wave_scidata)
            self.long_wave_offset = util.get_offset(long_wave_scidata, median, std, 0)
            self.shift_data(long_wave_scidata, n_long_light, self.long_wave_offset, pixel)
            master_long_wave = util.create_master(long_wave_scidata)
        else:
            self.long_wave_offset = np.zeros((n_long_light, 2), dtype=int)
            master_long_wave = long_wave_scidata

        # TODO no copying
        scidata = np.zeros((2, pixel[0], pixel[1]))
        scidata[0, :, :] = master_short_wave
        scidata[1, :, :] = master_long_wave

        del master_long_wave, master_short_wave

        # TODO why do we do this??
        # if n_short_light == 1:
        #     fit_list.append(fit_list_temp[0])
        # else:
        #     fit_list.append('short_wave_master_light')
        # if n_long_light == 1:
        #     fit_list.append(fit_list_temp[1])
        # else:
        #     fit_list.append('long_wave_master_light')

        n_fits = len(scidata[:, 0, 0])

        self.save_fits_files(scidata, n_short_light, n_long_light, short_wave_FIT_list, long_wave_FIT_list)

        rescaled_scidata_frame = scidata[reference_fit]

        # subtract sky background and set negative values to 0
        _, median, _ = util.get_stats(rescaled_scidata_frame)
        data2show = np.maximum(np.zeros(rescaled_scidata_frame.shape), rescaled_scidata_frame - median)

        # equalize the histogram or use log scaling for nicer display of image
        # array2show = np.uint16(aux.histeq(data2show,rescaled_pixel)/255)    # convert from 16 Bit to 8 Bit only for display
        array2show = np.uint16(util.hist_log(data2show) / 255)  # convert from 16 Bit to 8 Bit only for display

        image2show = Image.fromarray(array2show, mode='I;16')
        self.scene.addPixmap(image2show.toqpixmap())

        # the most work is done in init_fhd, it gives all the information for the colour magnitude diagram
        self.init_fhd(reference_fit, scidata, n_fits, pixel)


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
        for star in self.graphics_view.stars():
            star.status ^= StarStatus.Selected


    @Slot()
    def button_preview_clicked(self):
        plot_win = self.create_plot_window()

        plot_win.plot_fhd(self.n_stars_min, self.graphics_view.stars(), self.input_cmd, self.stars_flux, self.reddening_box.value(), self.stars_mag_list)
        plot_win.show()


    @Slot(StarEllipse)
    def info_star(self, star: StarEllipse): # event, canvas, stars_mag_list, short_wave_colour, long_wave_colour):
        # TODO: remove from list on 0 0
        index = star.data(0)

        typed_mag_1, ok = QInputDialog.getDouble(self, "", self.input_cmd["short_colour"])
        if not ok:
            QMessageBox.warning(self, "", "Expected valid floating point number")
            return

        typed_mag_2, ok = QInputDialog.getDouble(self, "", self.input_cmd["long_colour"])
        if not ok:
            QMessageBox.warning(self, "", "Expected valid floating point number")
            return

        # TODO: remove stars_mag_list
        for i in range(len(self.stars_mag_list)):
            if self.stars_mag_list[i][0] == 0 and self.stars_mag_list[i][1] == index:
                self.stars_mag_list.pop(i)
                break
        self.stars_mag_list.append([0, index, typed_mag_1])

        for i in range(len(self.stars_mag_list)):
            if self.stars_mag_list[i][0] == 1 and self.stars_mag_list[i][1] == index:
                self.stars_mag_list.pop(i)
                break
        self.stars_mag_list.append([1, index, typed_mag_2])

        self.logger.append(f"Set {index} to {typed_mag_1} and {typed_mag_2}")

        star.status |= StarStatus.Labeled
        # TODO: unused
        star.setData(2, typed_mag_1)
        star.setData(3, typed_mag_2)
        star.setToolTip(f"{self.input_cmd['short_colour']}: {typed_mag_1} | {self.input_cmd['long_colour']}: {typed_mag_2}")


    @Slot(QWidget)
    def plot_window_closed(self, win: QWidget):
        self.plot_windows.remove(win)


    def __init__(self):
        super().__init__()

        self.plot_windows = set()
        self.logger = [f"Started program @ {datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}"]

        with open("input_cmd.toml", "rb") as fl:
            self.input_cmd = tomllib.load(fl)

        self.scene = QGraphicsScene()
        self.graphics_view = StarGraphicsView(self.scene)
        self.graphics_view.star_chosen.connect(self.info_star)

        button_stack = QVBoxLayout()
        button_stack.addStretch()

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

        button_preview = QPushButton("Preview Diagrams")
        button_preview.clicked.connect(self.button_preview_clicked)
        button_stack.addWidget(button_preview)

        self.layout = QHBoxLayout(self)
        self.layout.addWidget(self.graphics_view)
        self.layout.addLayout(button_stack)

        self.setup()

    def close(self, /):
        pass
        # plot_fhd(n_stars_min, stars_flux, short_wave_colour, long_wave_colour, reddening, stars_mag_list,
        #          positions, path_save, time_stamp, True)  # creating the diagram

    def create_plot_window(self) -> PlotWindow:
        plot_win = PlotWindow()
        plot_win.closed.connect(self.plot_window_closed)

        self.plot_windows.add(plot_win)
        return plot_win

