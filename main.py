from PySide6.QtWidgets import QApplication

from main_window import MainWindow

# TODO required python version 3.12
# TODO message on not finding input files
# TODO input_cmd longitude/latitude not used

if __name__ == "__main__":
    app = QApplication()

    app.setStyleSheet("""
    QPushButton {
        min-width: 80px;
        padding: 12px;
    }
    
    QDoubleSpinBox {
        width: 120px;
        padding: 12px;
    }
    """)

    window = MainWindow()
    window.showMaximized()
    window.show()
    exit(app.exec())