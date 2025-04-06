from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import Signal

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

import numpy as np


class PlotWindow(QWidget):
    closed = Signal(QWidget)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.figure_canvas = FigureCanvasQTAgg()
        self.ax = self.figure_canvas.figure.subplots()

        self.layout = QHBoxLayout(self)
        self.layout.addWidget(self.figure_canvas)

    def closeEvent(self, event):
        self.closed.emit(self)
        super().closeEvent(event)


    def plot_fhd(self, n_stars_min, stars_flux, deselected, short_wave_colour, long_wave_colour, reddening, stars_mag_list,
                 positions, path_save, quit_save=False):
        stars_mag_1 = []
        stars_mag_2 = []

        for i in range(len(stars_mag_list)):
            if stars_mag_list[i][0] == 0:
                stars_mag_1.append(stars_mag_list[i])
            elif stars_mag_list[i][0] == 1:
                stars_mag_2.append(stars_mag_list[i])

        n_ref_stars_1 = len(stars_mag_1)

        if n_ref_stars_1 > 0:
            arbitrary_unit_mag = False

            ref_flux = np.zeros((n_ref_stars_1, 2))
            ref_mag_RGB = np.zeros((n_ref_stars_1, 2))
            ref_mag_UBV = np.zeros((n_ref_stars_1, 2))

            for i_ref_star in range(n_ref_stars_1):
                ref_flux[i_ref_star, 0] = stars_flux[int(stars_mag_1[i_ref_star][0]), int(stars_mag_1[i_ref_star][1])]
                ref_flux[i_ref_star, 1] = stars_flux[int(stars_mag_2[i_ref_star][0]), int(stars_mag_2[i_ref_star][1])]
                ref_mag_UBV[i_ref_star, 0] = stars_mag_1[i_ref_star][2]
                ref_mag_UBV[i_ref_star, 1] = stars_mag_2[i_ref_star][2]

            # convert fluxes to magnitudes in our own filter system
            ref_mag_RGB[:, :] = -2.5 * np.log10(ref_flux[:, :])

            # find conversion from our RGB filters to Johnson UBV filters
            fit_result_short = np.polyfit(ref_mag_RGB[:, 0], ref_mag_UBV[:, 0], 1)
            fit_result_long = np.polyfit(ref_mag_RGB[:, 1], ref_mag_UBV[:, 1], 1)

            RGB_UBV_converter_short = np.poly1d(fit_result_short)
            RGB_UBV_converter_long = np.poly1d(fit_result_long)

            # plot the conversion function
            # x_short = np.linspace(np.amin(ref_mag_RGB[:, 0]), np.amax(ref_mag_RGB[:, 0]), 2)
            # x_long = np.linspace(np.amin(ref_mag_RGB[:, 1]), np.amax(ref_mag_RGB[:, 1]), 2)

            # plt.plot(ref_mag_RGB[:, 0], ref_mag_UBV[:, 0], 'bx', label=short_wave_colour)
            # plt.plot(ref_mag_RGB[:, 1], ref_mag_UBV[:, 1], 'gx', label=long_wave_colour)
            # plt.plot(x_short, RGB_UBV_converter_short(x_short), 'b--', label='fit ' + short_wave_colour)
            # plt.plot(x_long, RGB_UBV_converter_long(x_long), 'g--', label='fit ' + long_wave_colour)
            # plt.xlabel('RGB [mag]')
            # plt.ylabel('UBV [mag]')
            # plt.legend()

            mag_short = np.zeros(n_stars_min)
            mag_long = np.zeros(n_stars_min)

            for star_i in range(n_stars_min):
                if stars_flux[0, star_i] > 0 and stars_flux[1, star_i] > 0:
                    # convert to RGB mags
                    mag_RGB_short = -2.5 * np.log10(stars_flux[0, star_i])
                    mag_RGB_long = -2.5 * np.log10(stars_flux[1, star_i])
                    # convert to UBV mags
                    mag_short[star_i] = RGB_UBV_converter_short(mag_RGB_short)
                    mag_long[star_i] = RGB_UBV_converter_long(mag_RGB_long)
                else:
                    mag_short[star_i] = None
                    mag_long[star_i] = None
        else:
            arbitrary_unit_mag = True

            mag_short = np.zeros(n_stars_min)
            mag_long = np.zeros(n_stars_min)

            ref_flux = [stars_flux[0, 0], stars_flux[1, 0]]
            ref_mag_UBV = [10, 10]
            for star_i in range(n_stars_min):
                if stars_flux[0, star_i] > 0 and stars_flux[1, star_i] > 0:
                    mag_short[star_i] = -2.5 * np.log10(stars_flux[0, star_i] / ref_flux[0]) + ref_mag_UBV[0]
                    mag_long[star_i] = -2.5 * np.log10(stars_flux[1, star_i] / ref_flux[1]) + ref_mag_UBV[1]
                else:
                    mag_short[star_i] = None
                    mag_long[star_i] = None

        colour_index = mag_short - mag_long
        colour_index_0 = colour_index - reddening

        if arbitrary_unit_mag == 0:
            self.ax.set_ylabel(long_wave_colour + ' [mag]')
        else:
            self.ax.set_ylabel(long_wave_colour + ' [a.u.]')

        if quit_save:
            # TODO timestamp
            time_stamp = "TODO"
            f = open(path_save + '/colour_mag_diagram_%s-%s_%s.dat' % (short_wave_colour, long_wave_colour, time_stamp), 'w')

            f.write('#ID\tx[px]\ty[px]\t')
            f.write('flux_%s[ADU]\tflux_%s[ADU]\t%s_mag\t%s_mag\n' % (short_wave_colour, long_wave_colour, short_wave_colour, long_wave_colour))

        for i in range(n_stars_min):
            if deselected[i] == 0:  # 1 means not in the cluster
                self.ax.plot(colour_index_0[i], mag_long[i], 'bo')
                if quit_save:
                    f.write('%3.3i \t %5.1f \t %5.1f \t %10.4f \t %10.4f \t %8.4f \t %8.4f \n'
                            % (i, positions[0, i, 0], positions[0, i, 1],
                               stars_flux[0, i], stars_flux[1, i],
                               mag_short[i], mag_long[i]))

        self.ax.invert_yaxis()
        if arbitrary_unit_mag == 0:
            self.ax.set_xlabel('Colour Index (%s-%s)_0 [mag]' % (short_wave_colour, long_wave_colour))
        else:
            self.ax.set_xlabel('Colour Index (%s-%s)_0 [a.u.]' % (short_wave_colour, long_wave_colour))

        if quit_save:
            f.close()