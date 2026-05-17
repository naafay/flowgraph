# main.py
import sys, os
from pathlib import Path
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QSplashScreen
from PySide6.QtCore import Qt
from ui.theme_manager import ThemeManager  # light import, keep it early

def resource_path(rel):
    base = getattr(sys, "_MEIPASS", Path(__file__).parent)  # _MEIPASS for PyInstaller
    return str(Path(base) / rel)

def _get_splash_pixmap():
    png = resource_path("assets/FlowGraph_splash.png")
    if os.path.exists(png):
        pm = QPixmap(png)
        if not pm.isNull():
            return pm
    icon = QIcon(resource_path("assets/FlowGraph.ico"))
    return icon.pixmap(512, 512)

class CSVPlotterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FlowGraph")
        self.setMinimumSize(1200, 800)

        # Set window icon (works in dev AND in built exe)
        self.setWindowIcon(QIcon(resource_path("assets/FlowGraph.ico")))

        # Theme manager needs a real window; self is valid here
        self.theme_manager = ThemeManager(self)
        self.theme_manager.apply_dark_theme()

        # PlotWindow import is heavy (Qt WebEngine, pandas) — import it *after* splash is up (done below)
        from ui.plot_window import PlotWindow
        self.plot_window = PlotWindow(self.theme_manager)
        self.setCentralWidget(self.plot_window)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("assets/FlowGraph.ico")))
    if getattr(sys, 'frozen', False):
    # This block only executes when running as a PyInstaller frozen executable
        try:
            import pyi_splash
            # Your application's initialization code goes here
            # ...
            pyi_splash.close()
        except ImportError:
            # Handle cases where pyi_splash might not be available (e.g., during development)
            pass
    # Show splash ASAP
    splash = QSplashScreen(_get_splash_pixmap())
    splash.showMessage("FlowGraph v1.0.0 • Starting…", Qt.AlignHCenter | Qt.AlignBottom, Qt.white)
    splash.show()
    app.processEvents()  # paint the splash immediately

    # Defer heavy UI import until after splash is visible
    splash.showMessage("Loading UI modules…", Qt.AlignHCenter | Qt.AlignBottom, Qt.white)
    app.processEvents()

    # Build and show window (this will import ui.plot_window inside CSVPlotterApp.__init__)
    window = CSVPlotterApp()
    splash.showMessage("Initializing components…", Qt.AlignHCenter | Qt.AlignBottom, Qt.white)
    app.processEvents()

    window.show()
    splash.finish(window)
    sys.exit(app.exec())
