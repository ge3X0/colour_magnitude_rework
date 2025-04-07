from PySide6.QtWidgets import QApplication

from main_window import MainWindow

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