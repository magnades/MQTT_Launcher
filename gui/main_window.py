from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import Qt

# Importamos las ventanas individuales
from gui.windows.mosquitto import MosquittoWindow
from gui.windows.influx import InfluxWindow
from gui.windows.telegraf import TelegrafWindow
from gui.windows.calculator import CalculatorWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IoT Installer Launcher")
        self.setFixedSize(400, 500)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        layout.addWidget(QLabel("Selecciona un Módulo"), alignment=Qt.AlignCenter)

        # Botones del Menú
        btn_influx = QPushButton("1. InfluxDB Manager")
        btn_influx.setMinimumHeight(60)
        btn_influx.clicked.connect(self.open_influx)

        btn_mosquitto = QPushButton("2. Mosquitto MQTT Manager")
        btn_mosquitto.setMinimumHeight(60)
        btn_mosquitto.clicked.connect(self.open_mosquitto)

        btn_telegraf = QPushButton("3. Telegraf Agent Manager")
        btn_telegraf.setMinimumHeight(60)
        btn_telegraf.clicked.connect(self.open_telegraf)

        btn_calculator = QPushButton("4. Calculator")
        btn_calculator.setMinimumHeight(60)
        btn_calculator.clicked.connect(self.open_calculator)

        layout.addWidget(btn_influx)
        layout.addWidget(btn_mosquitto)
        layout.addWidget(btn_telegraf)
        layout.addWidget(btn_calculator)
        layout.addStretch()

        # Variable para mantener viva la ventana secundaria
        self.sub_window = None

    def open_mosquitto(self):
        self.sub_window = MosquittoWindow()
        self.sub_window.show()

    def open_influx(self):
        self.sub_window = InfluxWindow()
        self.sub_window.show()

    def open_telegraf(self):
        self.sub_window = TelegrafWindow()
        self.sub_window.show()

    def open_calculator(self):
        self.sub_window = CalculatorWindow()
        self.sub_window.show()