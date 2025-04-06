from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QGraphicsView, QGraphicsScene
from PySide6.QtGui import QPen, QBrush
from PySide6.QtCore import QRect, QPoint, Slot
import numpy as np
from astropy.io import fits
from photutils.aperture import CircularAperture, aperture_photometry

import util

import tomllib
from pathlib import Path
from datetime import datetime, time

from PIL import Image

class MainWindow(QWidget):

    def init_fhd(self, reference_fit, n_stars_min, scidata, n_fits, pixel, short_wave_colour,
                 long_wave_colour, offset_short_wave, offset_long_wave, reddening, FWHM, ratio_gauss,
                 factor_threshold, r_aperture):

        mean, median, std = util.get_stats(scidata)

        offset = util.get_offset(scidata, median, std, reference_fit)

        # shift and pad the images; we want the original number of pixel -> only part of the padded array needed
        self.shift_data(scidata, n_fits, offset, pixel)

        # the stars of the images are found here and the positions are saved
        sources, n_stars_min, positions = util.detect_star(n_stars_min, scidata, median, std, FWHM, ratio_gauss,
                                                          factor_threshold)


        stars_flux = np.zeros((n_fits, n_stars_min))
        deselected = np.zeros((n_stars_min))
        stars_mag_list = []

        # stars flux are only numbers, they are made from a circle around the position of a star and the sum of it.
        for i in range(n_fits):
            arr2d = []
            for a in range(len(positions[i, :, 0])):
                print([positions[i, a, 0], positions[i, a, 1]])
                arr2d.append([positions[i, a, 0], positions[i, a, 1]])

            apertures = CircularAperture(arr2d, r=r_aperture * FWHM)  # the area, where the flux is going to be taken from
            phot = aperture_photometry(scidata[i, :, :] - median[i], apertures)  # the numbers are generated from the specific area of 'apertures'
            stars_flux[i, :] = phot['aperture_sum'][0:n_stars_min]  # numbers, that represent the luminosity of a star. Not real flux, but similar

        # creating the ovals around the stars for user input
        pen = QPen("green")
        for j in range(n_stars_min):
            e = self.scene.addEllipse(
                QRect(
                    QPoint(positions[reference_fit, j, 0] - 3 / 2 * r_aperture * FWHM,
                           positions[reference_fit, j, 1] - 3 / 2 * r_aperture * FWHM,),
                    QPoint(positions[reference_fit, j, 0] + 3 / 2 * r_aperture * FWHM,
                           positions[reference_fit, j, 1] + 3 / 2 * r_aperture * FWHM,)
                ),
                pen=pen
            )
            e.setData(0, j)
            e.setData(1, stars_flux[reference_fit, j])

        print('Found ' + str(n_stars_min) + ' Stars')
        print('')
        print(
            'Select the not included stars by left clicking and put in the magnitude via right clicking and then typing in the console. Leave blank for no input')
        print('')
        print(
            'The colours mean: green - in the cluster ; red - not in the cluster ; blue - magnitude has been typed in ; orange - magnitude is given, but not in the cluster')
        print('')
        print('Controls are: Left click - deselect ; right click - type in magnitude')
        print('')

        # canvas.bind("<Button-1>", lambda e: deselect_star(e, canvas, deselected))  # left click to deselect a star
        # canvas.bind("<Button-3>", lambda e: info_star(e, canvas, deselected, stars_mag_list, short_wave_colour,
        #                                               long_wave_colour))  # right click to type in magnitudes
        # canvas.bind("<Button-2>", lambda e: tag_info(e, canvas, deselected,
        #                                              stars_mag_list))  # middle mouse, just to see the tags of the selected star

        return deselected, n_stars_min, stars_flux, stars_mag_list, positions

    def shift_data(self, data, n_len, offset, pixel):
        for i in range(n_len):
            upper0 = abs(max(0, offset[i, 0]))
            lower0 = abs(min(0, offset[i, 0]))
            upper1 = abs(max(0, offset[i, 1]))
            lower1 = abs(max(0, offset[i, 1]))
            tmp = np.pad(data[i], ((upper0, lower0), (upper1, lower1)), mode='constant')
            data[i] = tmp[lower0: pixel[0] + lower0, lower1:pixel[1] + lower1]

    def setup(self):
        n_stars_min = 1

        print('Searching for light frames of short wavelength ...')
        fit_list = util.get_fits_names(self.input_cmd["path_light_short"])
        short_wave_FIT_list = fit_list
        n_short_light = len(short_wave_FIT_list)
        print('... done')
        print('')

        print('Searching for light frames of long wavelength ...')
        fit_list_temp = util.get_fits_names(self.input_cmd["path_light_long"])
        long_wave_FIT_list = fit_list_temp
        n_long_light = len(long_wave_FIT_list)
        for i in range(n_long_light):
            fit_list.append(long_wave_FIT_list[i])
        print('... done')
        print('')

        n_fits = len(fit_list)
        scidata = util.fits_to_array(fit_list)
        pixel = scidata[0].shape

        # dark correction
        #
        if self.input_cmd["do_dark"]:
            print('Searching for dark frames of short wavelength ...')
            fit_list_dark_short = util.get_fits_names(self.input_cmd["path_dark_short"])
            if len(fit_list_dark_short) < 1:
                print('No dark correction will be done')
                print('')
            else:
                print('... done')
                print('')
                darks_short = util.fits_to_array(fit_list_dark_short)
                scidata[:n_short_light] = util.dark_correction(scidata[:n_short_light], darks_short)

            print('Searching for dark frames of long wavelength ...')
            fit_list_dark_long = util.get_fits_names(self.input_cmd["path_dark_long"])
            if len(fit_list_dark_long) < 1:
                print('No dark correction will be done')
                print('')
            else:
                print('... done')
                print('')
                darks_long = util.fits_to_array(fit_list_dark_long)
                scidata[n_short_light:] = util.dark_correction(scidata[n_short_light:], darks_long)

        # flat fielding
        #
        if self.input_cmd["do_flat"]:
            print('Searching for flatfields of short wavelength ...')
            fit_list_flat_short = util.get_fits_names(self.input_cmd["path_flat_short"])
            if len(fit_list_flat_short) < 1:
                print('No flatfielding will be done')
                print('')
            else:
                print('... done')
                print('')
                flats_short = util.fits_to_array(fit_list_flat_short)

                # dark correction of flat fields
                #
                if self.input_cmd["do_dark_flat"]:
                    print('Searching for dark_flat frames ...')
                    fit_list_dark_flat = util.get_fits_names(self.input_cmd["path_dark_flat"])
                    if len(fit_list_dark_flat) < 1:
                        print('No dark correction will be done for the flats')
                        print('')
                    else:
                        print('... done')
                        print('')
                        flat_darks = util.fits_to_array(fit_list_dark_flat)
                        flats_short = util.dark_correction(flats_short, flat_darks)

                scidata[:n_short_light] = util.flat_correction(scidata[:n_short_light], flats_short)

                del flats_short

            print('Searching for flatfields of long wavelength ...')
            fit_list_flat_long = util.get_fits_names(self.input_cmd["path_flat_long"])
            if len(fit_list_flat_long) < 1:
                print('No flatfielding will be done')
                print('')
            else:
                print('... done')
                print('')
                flats_long = util.fits_to_array(fit_list_flat_long)
                # dark correction of flat fields
                #
                if self.input_cmd["do_dark_flat"]:
                    print('Searching for dark_flat frames ...')
                    fit_list_dark_flat = util.get_fits_names(self.input_cmd["path_dark_flat"])
                    print('... done')
                    if len(fit_list_dark_flat) < 1:
                        print('No dark correction will be done for the flats')
                        print('')
                    else:
                        print('')
                        flat_darks = util.fits_to_array(fit_list_dark_flat)
                        flats_long = util.dark_correction(flats_long, flat_darks)

                scidata[n_short_light:] = util.flat_correction(scidata[n_short_light:], flats_long)

                del flats_long

        short_wave_colour = self.input_cmd["short_colour"]
        long_wave_colour = self.input_cmd["long_colour"]

        reference_name_list = []

        if n_short_light == 1:
            reference_name_list.append(short_wave_FIT_list[0])
        else:
            reference_name_list.append('short_wavelength_master')
        if n_long_light == 1:
            reference_name_list.append(long_wave_FIT_list[0])
        else:
            reference_name_list.append('long_wavelength_master')

        reference_fit = 0  # 0 = short wavelength; 1 = long wavelength

        reddening = 0.0
        # while True:  # offset for the colour-index for the diagram. The value will be subtracted from the index
        #     print('Reddening correction for interstellar dust extinction? [default: 0.0]')
        #     reddening = input('  :')
        #     if reddening == '':
        #         reddening = '0'
        #     try:
        #         reddening = float(reddening)
        #         print('')
        #         break
        #     except:
        #         print('Not a float, please try again')
        #         print('')

        print('Creating light masters ...')
        print('')

        fit_list_temp = fit_list
        fit_list = []

        # here the master lights are created, after each picture was offset-aligned regarding your input
        #
        short_wave_scidata = scidata[:n_short_light, :, :]

        if n_short_light > 1:
            mean, median, std = util.get_stats(short_wave_scidata)
            short_wave_offset = util.get_offset(short_wave_scidata, median, std, 0)
            self.shift_data(short_wave_scidata, n_short_light, short_wave_offset, pixel)
            master_short_wave = util.create_master(short_wave_scidata)
        else:
            short_wave_offset = np.zeros((n_short_light, 2), dtype=int)
            master_short_wave = short_wave_scidata

        long_wave_scidata = scidata[n_short_light:n_long_light + n_short_light, :, :]

        if n_long_light > 1:
            mean, median, std = util.get_stats(long_wave_scidata)
            long_wave_offset = util.get_offset(long_wave_scidata, median, std, 0)
            self.shift_data(long_wave_scidata, n_long_light, long_wave_offset, pixel)
            master_long_wave = util.create_master(long_wave_scidata)
        else:
            long_wave_offset = np.zeros((n_long_light, 2), dtype=int)
            master_long_wave = long_wave_scidata

        scidata = np.zeros((2, pixel[0], pixel[1]))
        scidata[0, :, :] = master_short_wave
        scidata[1, :, :] = master_long_wave

        del master_long_wave, master_short_wave

        if n_short_light == 1:
            fit_list.append(fit_list_temp[0])
        else:
            fit_list.append('short_wave_master_light')
        if n_long_light == 1:
            fit_list.append(fit_list_temp[1])
        else:
            fit_list.append('long_wave_master_light')

        n_fits = len(scidata[:, 0, 0])

        print('     ... done')
        print('')

        path_save = Path(self.input_cmd["path_result"])

        print('Saving the images that will be used for the CMD ...')

        if not path_save.exists():
            path_save.mkdir(parents=True)

        # hdulist_short = fits.HDUList(fits.PrimaryHDU(data=scidata[0, :, :]))
        # hdulist_short[0].header = fits.open(short_wave_FIT_list[0])[0].header
        #
        # hdulist_short[0].header['BZERO'] = 0.0
        # hdulist_short[0].header['SNAPSHOT'] = n_short_light
        # # hdulist_short[0].header['Date'] = time.strftime('%Y-%m-%d')
        # hdulist_short[0].header['Note'] = 'Created by colour_magnitude_diagram.py'
        #
        # hdulist_long = fits.HDUList(fits.PrimaryHDU(data=scidata[1, :, :]))
        # hdulist_long[0].header = fits.open(long_wave_FIT_list[0])[0].header
        #
        # hdulist_long[0].header['BZERO'] = 0.0
        # hdulist_long[0].header['SNAPSHOT'] = n_long_light
        # # hdulist_long[0].header['Date'] = time.strftime('%Y-%m-%d')
        # hdulist_long[0].header['Note'] = 'Created by colour_magnitude_diagram.py'
        #
        # time_stamp = datetime.now().isoformat()[:-10]
        #
        # hdulist_short.writeto(path_save / short_wave_colour + '_' + time_stamp + '.fits', overwrite=True)
        # hdulist_long.writeto(path_save / long_wave_colour + '_' + time_stamp + '.fits', overwrite=True)

        print('... done')
        print('')

        rescaled_scidata_frame = scidata[reference_fit]
        rescaled_pixel = pixel

        print('Creating window ...')

        # subtract sky background and set negative values to 0
        #
        mean, median, std = util.get_stats(rescaled_scidata_frame)
        data2show = np.maximum(np.zeros(rescaled_scidata_frame.shape), rescaled_scidata_frame - median)

        # equalize the histogram or use log scaling for nicer display of image
        #
        # array2show = np.uint16(aux.histeq(data2show,rescaled_pixel)/255)    # convert from 16 Bit to 8 Bit only for display
        array2show = np.uint16(util.hist_log(data2show) / 255)  # convert from 16 Bit to 8 Bit only for display

        # add image to canvas
        #
        image2show = Image.fromarray(array2show, mode='I;16')
        self.scene.addPixmap(image2show.toqpixmap())

        print('... done')
        print('')

        # TODO: ignored these
        # read some values from input_cmd.dat
        #
        FWHM = self.input_cmd["FWHM"]
        ratio_gauss = self.input_cmd["ratio"]
        factor_threshold = self.input_cmd["threshold"]
        r_aperture = self.input_cmd["r_aperture"]

        # the most work is done in init_fhd, it gives all the information for the colour magnitude diagram
        self.init_fhd(reference_fit, n_stars_min, scidata, n_fits, pixel, short_wave_colour, long_wave_colour,
                      short_wave_offset, long_wave_offset, reddening, FWHM, ratio_gauss, factor_threshold, r_aperture)
        # deselected, n_stars_min, estars_flux, stars_mag_list, positions = self.init_fhd(reference_fit, n_stars_min, scidata,
        #                                                                            n_fits,
        #                                                                            pixel, short_wave_colour,
        #                                                                            long_wave_colour,
        #                                                                            short_wave_offset, long_wave_offset,
        #                                                                            reddening, FWHM, ratio_gauss,
        #                                                                            factor_threshold, r_aperture)

    @Slot()
    def button_offset_master_clicked(self):
        # util.plot_offset(offset)
        pass

    @Slot()
    def button_offset_short_clicked(self):
        # util.plot_offset(offset_short_wave)
        pass

    @Slot()
    def button_offset_long_clicked(self):
        # util.plot_offset(offset_long_wave)
        pass

    @Slot()
    def button_toggle_selection_clicked(self):
        # deselect_all
        pass

    @Slot()
    def button_preview_clicked(self):
        # plot_fhd(n_stars_min, stars_flux, deselected, short_wave_colour,
    #         #                                                 long_wave_colour, reddening, stars_mag_list, positions,
    #         #                                                 path_save, time_stamp, False)
        pass

    def __init__(self):
        super().__init__()

        with open("input_cmd.toml", "rb") as fl:
            self.input_cmd = tomllib.load(fl)

        self.scene = QGraphicsScene()
        self.graphics_view = QGraphicsView(self.scene)

        button_stack = QVBoxLayout()

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
        # plot_fhd(n_stars_min, stars_flux, deselected, short_wave_colour, long_wave_colour, reddening, stars_mag_list,
        #          positions, path_save, time_stamp, True)  # creating the diagram

