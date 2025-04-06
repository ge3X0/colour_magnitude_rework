from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QMessageBox
from PySide6.QtCore import Signal, Slot

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

import numpy as np

from star_ellipse import StarEllipse, StarStatus


class PlotWindow(QWidget):
    # Signal is emitted when the window is closed. Used to remove it from the MainWindow list
    closed = Signal(QWidget)

    # Signal is emitted when fhd data should be saved
    saving = Signal(np.ndarray, np.ndarray)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.figure_canvas = FigureCanvasQTAgg()

        # Used to save fhd data
        self.mag_short = None
        self.mag_long = None

        button_stack = QVBoxLayout()

        save_button = QPushButton("Save Data")
        save_button.clicked.connect(self.save_button_clicked)
        button_stack.addWidget(save_button)

        # TODO save-image button?

        self.layout = QHBoxLayout(self)
        self.layout.addWidget(self.figure_canvas)
        self.layout.addLayout(button_stack)

        self.resize(800, 600)


    def closeEvent(self, event):
        """Informs MainWindow that we would like to close"""
        self.closed.emit(self)
        super().closeEvent(event)


    def plot_offset(self, offset):
        """shows the offset of pictures, aligned by the align function"""
        # TODO looped?
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


    @Slot()
    def save_button_clicked(self):
        """Informs MainWindow we would like to save data"""
        if self.mag_long is not None and self.mag_short is not None:
            self.saving.emit(self.mag_short, self.mag_long)
        else:
            QMessageBox.information(self, "", "Saving is only supported for FHD-Plots")


    def plot_fhd(self, n_stars_min: int, stars: list[StarEllipse], input_cmd: dict, stars_flux, reddening):
        # TODO is n_stars_min == len(stars) ?
        ax = self.figure_canvas.figure.subplots()

        stars_mag_1 = []
        stars_mag_2 = []

        for star in stars:
            if StarStatus.Labeled in star.status:
                stars_mag_1.append([0, star.index, star.vmag1])
                stars_mag_2.append([1, star.index, star.vmag2])

        n_ref_stars_1 = len(stars_mag_1)

        self.mag_short = np.zeros(n_stars_min)
        self.mag_long = np.zeros(n_stars_min)

        arbitrary_unit_mag = n_ref_stars_1 <= 0

        if not arbitrary_unit_mag:
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
            # TODO: is this needed?
            # x_short = np.linspace(np.amin(ref_mag_RGB[:, 0]), np.amax(ref_mag_RGB[:, 0]), 2)
            # x_long = np.linspace(np.amin(ref_mag_RGB[:, 1]), np.amax(ref_mag_RGB[:, 1]), 2)

            # plt.plot(ref_mag_RGB[:, 0], ref_mag_UBV[:, 0], 'bx', label=short_wave_colour)
            # plt.plot(ref_mag_RGB[:, 1], ref_mag_UBV[:, 1], 'gx', label=long_wave_colour)
            # plt.plot(x_short, RGB_UBV_converter_short(x_short), 'b--', label='fit ' + short_wave_colour)
            # plt.plot(x_long, RGB_UBV_converter_long(x_long), 'g--', label='fit ' + long_wave_colour)
            # plt.xlabel('RGB [mag]')
            # plt.ylabel('UBV [mag]')
            # plt.legend()

            for star_i in range(n_stars_min):
                if stars_flux[0, star_i] > 0 and stars_flux[1, star_i] > 0:
                    # convert to RGB mags
                    mag_RGB_short = -2.5 * np.log10(stars_flux[0, star_i])
                    mag_RGB_long = -2.5 * np.log10(stars_flux[1, star_i])
                    # convert to UBV mags
                    self.mag_short[star_i] = RGB_UBV_converter_short(mag_RGB_short)
                    self.mag_long[star_i] = RGB_UBV_converter_long(mag_RGB_long)
                else:
                    self.mag_short[star_i] = None
                    self.mag_long[star_i] = None
        else:
            ref_flux = [stars_flux[0, 0], stars_flux[1, 0]]
            ref_mag_UBV = [10, 10]
            for star_i in range(n_stars_min):
                if stars_flux[0, star_i] > 0 and stars_flux[1, star_i] > 0:
                    self.mag_short[star_i] = -2.5 * np.log10(stars_flux[0, star_i] / ref_flux[0]) + ref_mag_UBV[0]
                    self.mag_long[star_i] = -2.5 * np.log10(stars_flux[1, star_i] / ref_flux[1]) + ref_mag_UBV[1]
                else:
                    self.mag_short[star_i] = None
                    self.mag_long[star_i] = None

        colour_index = self.mag_short - self.mag_long
        colour_index_0 = colour_index - reddening

        ex = "[mag]" if not arbitrary_unit_mag else "[a.u.]"
        ax.set_xlabel(f"Colour Index ({input_cmd['short_colour']}-{input_cmd['long_colour']}) {ex}")
        ax.set_ylabel(f"{input_cmd['long_colour']} {ex}")

        for star in filter(lambda x: StarStatus.Selected in x.status, stars):
            ax.plot(colour_index_0[star.index], self.mag_long[star.index], 'bo')

        ax.invert_yaxis()

        # for i in range(n_stars_min):
        #     if deselected[i] == 0:  # 1 means not in the cluster
        #         ax.plot(colour_index_0[i], mag_long[i], 'bo')
        #         if quit_save:
        #             f.write('%3.3i \t %5.1f \t %5.1f \t %10.4f \t %10.4f \t %8.4f \t %8.4f \n'
        #                     % (i, positions[0, i, 0], positions[0, i, 1],
        #                        stars_flux[0, i], stars_flux[1, i],
        #                        mag_short[i], mag_long[i]))
