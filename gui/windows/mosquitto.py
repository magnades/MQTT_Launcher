from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,
                               QLineEdit, QGroupBox, QTextEdit, QFileDialog)
from gui.utils import WorkerThread
import core
import os


class MosquittoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuración de Mosquitto MQTT")
        self.resize(600, 500)
        self.layout = QVBoxLayout(self)

        # 1. Carpeta
        self.layout.addWidget(QLabel("Ruta de Instalación:"))
        # Cargamos ruta guardada o usamos defecto
        last_path = core.get_setting("mosquitto_path", "C:\\mosquitto")
        self.path_input = QLineEdit(last_path)

        self.btn_browse = QPushButton("Seleccionar...")
        self.btn_browse.clicked.connect(self.select_folder)
        self.layout.addWidget(self.path_input)
        self.layout.addWidget(self.btn_browse)

        # 2. Credenciales
        auth_group = QGroupBox("Seguridad (Se compartirá con Telegraf)")
        auth_layout = QVBoxLayout()

        # --- CARGAR CONFIGURACIÓN GUARDADA ---
        saved_user = core.get_setting("mqtt_user", "admin")
        saved_pass = core.get_setting("mqtt_pass", "secret")

        self.user_input = QLineEdit(saved_user)
        self.user_input.setPlaceholderText("Usuario")

        self.pass_input = QLineEdit(saved_pass)
        self.pass_input.setPlaceholderText("Contraseña")
        self.pass_input.setEchoMode(QLineEdit.Password)

        auth_layout.addWidget(QLabel("Usuario MQTT:"))
        auth_layout.addWidget(self.user_input)
        auth_layout.addWidget(QLabel("Contraseña:"))
        auth_layout.addWidget(self.pass_input)
        auth_group.setLayout(auth_layout)
        self.layout.addWidget(auth_group)

        # ... (Logs y Botón igual que antes) ...
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background: black; color: lime;")
        self.layout.addWidget(self.log_area)

        self.btn_run = QPushButton("Instalar y Guardar Configuración")
        self.btn_run.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold;")
        self.btn_run.clicked.connect(self.start_process)
        self.layout.addWidget(self.btn_run)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta")
        if folder: self.path_input.setText(os.path.normpath(folder))

    def log(self, text):
        self.log_area.append(text)

    def start_process(self):
        self.btn_run.setEnabled(False)
        target_dir = self.path_input.text()
        user = self.user_input.text()
        pwd = self.pass_input.text()

        # --- AQUÍ GUARDAMOS EN EL JSON COMPARTIDO ---
        core.save_setting("mosquitto_path", target_dir)
        core.save_setting("mqtt_user", user)
        core.save_setting("mqtt_pass", pwd)
        self.log(">> Configuración guardada en JSON compartido.")

        def task(log_callback):
            success, _ = core.install_package("EclipseFoundation.Mosquitto", log_callback)
            if success:
                core.configure_mosquitto_custom(target_dir, user, pwd, log_callback)

        self.worker = WorkerThread(task)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(lambda: self.btn_run.setEnabled(True))
        self.worker.start()