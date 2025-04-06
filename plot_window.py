from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import Signal

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

import numpy as np

from star_ellipse import StarEllipse, StarStatus

from typing import Iterator


class PlotWindow(QWidget):
    closed = Signal(QWidget)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.figure_canvas = FigureCanvasQTAgg()

        self.layout = QHBoxLayout(self)
        self.layout.addWidget(self.figure_canvas)

    def closeEvent(self, event):
        self.closed.emit(self)
        super().closeEvent(event)

    # shows the offset of pictures, aligned by the align function
    def plot_offset(self, offset):
        ax1, ax2 = self.figure_canvas.figure.subplots(2, 1)

        ax1.plot(range(1, len(offset[:, 0]) + 1), offset[:, 0])

        n_ticks_x = min(len(offset[:, 0]), 15)
        n_ticks_y = min(abs(max(offset[:, 0]) - min(offset[:, 0])) + 2, 15)

        ax1.set_yticks(np.linspace(min(offset[:, 0]) - 1, max(offset[:, 0]) + 1, n_ticks_y).astype(
            int))  # having only integers at the y axis
        ax1.set_xticks(np.linspace(1, len(offset[:, 0]), n_ticks_x).astype(int))  # and only integers on the x axis

        ax1.set_ylabel('Offset in x direction [px]')

        ax2.plot(range(1, len(offset[:, 1]) + 1), offset[:, 1])

        n_ticks_x = min(len(offset[:, 1]), 15)
        n_ticks_y = min(abs(max(offset[:, 1]) - min(offset[:, 1])) + 2, 15)

        ax2.set_yticks(np.linspace(min(offset[:, 1]) - 1, max(offset[:, 1]) + 1, n_ticks_y).astype(
            int))  # having only integers at the y axis
        ax2.set_xticks(np.linspace(1, len(offset[:, 1]), n_ticks_x).astype(int))  # and only integers on the x axis

        ax2.set_ylabel('Offset in y direction [px]')
        ax2.set_xlabel('Image Number')


    def plot_fhd(self, n_stars_min: int, stars: Iterator[StarEllipse],
                 input_cmd: dict, stars_flux, reddening, stars_mag_list):
        ax = self.figure_canvas.figure.subplots()

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

        ex = "[mag]" if arbitrary_unit_mag == 0 else "[a.u.]"
        ax.set_ylabel(f"{input_cmd['long_colour']} {ex}")

        # if quit_save:
        #     # TODO timestamp
            # TODO saving
        #     time_stamp = "TODO"
        #     f = open(path_save + '/colour_mag_diagram_%s-%s_%s.dat' % (short_wave_colour, long_wave_colour, time_stamp), 'w')
        #
        #     f.write('#ID\tx[px]\ty[px]\t')
        #     f.write('flux_%s[ADU]\tflux_%s[ADU]\t%s_mag\t%s_mag\n' % (short_wave_colour, long_wave_colour, short_wave_colour, long_wave_colour))

        for star in stars:
            if not StarStatus.Selected in star.status:
                continue
            idx = star.data(0)
            ax.plot(colour_index_0[idx], mag_long[idx], 'bo')
            # if quit_save:
            #     f.write(f"{idx}\t{positions[0, idx, 0]}\t{positions[0, idx, 1]}\t"
            #             f"{stars_flux[0, idx]}\t{stars_flux[1, idx]}\t"
            #             f"{mag_short[idx]}\t{mag_long[idx]}\n")

        # for i in range(n_stars_min):
        #     if deselected[i] == 0:  # 1 means not in the cluster
        #         ax.plot(colour_index_0[i], mag_long[i], 'bo')
        #         if quit_save:
        #             f.write('%3.3i \t %5.1f \t %5.1f \t %10.4f \t %10.4f \t %8.4f \t %8.4f \n'
        #                     % (i, positions[0, i, 0], positions[0, i, 1],
        #                        stars_flux[0, i], stars_flux[1, i],
        #                        mag_short[i], mag_long[i]))

        ax.invert_yaxis()
        ax.set_xlabel(f"Colour Index ({input_cmd['short_colour']}-{input_cmd['long_colour']}) {ex}")

        # if quit_save:
        #     f.close()