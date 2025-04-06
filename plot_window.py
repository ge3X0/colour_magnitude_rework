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


    def plot_fhd(self, n_stars_min: int, stars: list[StarEllipse], input_cmd: dict, reddening: float):
        # TODO is n_stars_min == len(stars) ?
        ax = self.figure_canvas.figure.subplots()

        labeled_stars = list(filter(lambda x: StarStatus.Labeled in x.status, stars))
        n_ref_stars_1 = len(labeled_stars)

        self.mag_short = np.zeros(n_stars_min)
        self.mag_long = np.zeros(n_stars_min)

        arbitrary_unit_mag = n_ref_stars_1 <= 0

        if not arbitrary_unit_mag:
            ref_flux = np.zeros((n_ref_stars_1, 2))
            ref_mag_RGB = np.zeros((n_ref_stars_1, 2))
            ref_mag_UBV = np.zeros((n_ref_stars_1, 2))

            for i_ref_star, star in enumerate(labeled_stars):
                ref_flux[i_ref_star, 0] = star.flux1
                ref_flux[i_ref_star, 1] = star.flux2
                ref_mag_UBV[i_ref_star, 0] = star.vmag1
                ref_mag_UBV[i_ref_star, 1] = star.vmag2

            # convert fluxes to magnitudes in our own filter system
            ref_mag_RGB[:, :] = -2.5 * np.log10(ref_flux[:, :])

            # find conversion from our RGB filters to Johnson UBV filters
            fit_result_short = np.polyfit(ref_mag_RGB[:, 0], ref_mag_UBV[:, 0], 1)
            fit_result_long = np.polyfit(ref_mag_RGB[:, 1], ref_mag_UBV[:, 1], 1)

            RGB_UBV_converter_short = np.poly1d(fit_result_short)
            RGB_UBV_converter_long = np.poly1d(fit_result_long)

            for star in stars:
                if star.flux1 > 0 and star.flux2 > 0:
                    # convert to RGB mags
                    mag_RGB_short = -2.5 * np.log10(star.flux1)
                    mag_RGB_long = -2.5 * np.log10(star.flux2)
                    # convert to UBV mags
                    self.mag_short[star.index] = RGB_UBV_converter_short(mag_RGB_short)
                    self.mag_long[star.index] = RGB_UBV_converter_long(mag_RGB_long)
                else:
                    self.mag_short[star.index] = None
                    self.mag_long[star.index] = None
        else:
            ref_flux = [stars[0].flux1, stars[0].flux2]
            ref_mag_UBV = [10, 10]

            for star in stars:
                if star.flux1 > 0 and star.flux2 > 0:
                    self.mag_short[star.index] = -2.5 * np.log10(star.flux1 / ref_flux[0]) + ref_mag_UBV[0]
                    self.mag_long[star.index] = -2.5 * np.log10(star.flux2 / ref_flux[1]) + ref_mag_UBV[1]
                else:
                    self.mag_short[star.index] = None
                    self.mag_long[star.index] = None

        colour_index = self.mag_short - self.mag_long
        colour_index_0 = colour_index - reddening

        ex = "[mag]" if not arbitrary_unit_mag else "[a.u.]"
        ax.set_xlabel(f"Colour Index ({input_cmd['short_colour']}-{input_cmd['long_colour']}) {ex}")
        ax.set_ylabel(f"{input_cmd['long_colour']} {ex}")

        for star in filter(lambda x: StarStatus.Selected in x.status, stars):
            ax.plot(colour_index_0[star.index], self.mag_long[star.index], 'bo')

        ax.invert_yaxis()