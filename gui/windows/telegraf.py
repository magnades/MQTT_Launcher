from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,
                               QLineEdit, QTextEdit, QFormLayout, QFileDialog, QGroupBox)
from gui.utils import WorkerThread
import core
import os


class TelegrafWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instalación Portable de Telegraf (MQTT Bridge)")
        self.resize(600, 750)
        self.layout = QVBoxLayout(self)

        # --- 1. DESCARGA ---
        dl_group = QGroupBox("1. Descarga")
        dl_layout = QVBoxLayout()

        default_path = core.get_setting("telegraf_path")

        if not default_path:
            # Intentamos leer la ruta de mosquitto, si no, la de influx
            neighbor_path = core.get_setting("mosquitto_path") or core.get_setting("influx_path")

            if neighbor_path:
                default_path = os.path.join(neighbor_path, "Telegraf_Portable")
            else:
                # Si no hay nada instalado aun, usamos el defecto
                default_path = "C:\\Telegraf_Portable"

        self.path_input = QLineEdit(default_path)

        self.btn_browse = QPushButton("Seleccionar Carpeta...")
        self.btn_browse.clicked.connect(self.select_folder)

        # --- CAMBIO AQUÍ: CARGAR URL GUARDADA O USAR DEFECTO ---
        saved_url = core.get_setting("telegraf_url","https://dl.influxdata.com/telegraf/releases/telegraf-1.37.1_windows_amd64.zip")
        self.url_input = QLineEdit(saved_url)
        self.url_input.setPlaceholderText("Pega aquí el link de descarga del ZIP")

        dl_layout.addWidget(QLabel("Carpeta:"))
        dl_layout.addWidget(self.path_input)
        dl_layout.addWidget(self.btn_browse)
        dl_layout.addWidget(QLabel("URL de descarga (ZIP):"))
        dl_layout.addWidget(self.url_input)
        dl_group.setLayout(dl_layout)
        self.layout.addWidget(dl_group)

        # --- 2. CONFIG INFLUXDB ---
        influx_group = QGroupBox("2. Destino: InfluxDB")
        influx_layout = QFormLayout()
        self.input_url = QLineEdit("http://127.0.0.1:8181")
        self.input_org = QLineEdit("default")

        # Recuperamos lo guardado por InfluxWindow (o valores por defecto)
        saved_bucket = core.get_setting("influx_bucket", "shmdatabase")
        saved_org = core.get_setting("influx_org", "docs")
        saved_token = core.get_setting("influx_token", "")

        self.input_bucket = QLineEdit(saved_bucket)
        self.input_org = QLineEdit(saved_org)
        self.input_token = QLineEdit(saved_token)
        self.input_token.setPlaceholderText("Token InfluxDb (apiv3_...)")

        influx_layout.addRow("URL Influx:", self.input_url)
        influx_layout.addRow("Organización:", self.input_org)
        influx_layout.addRow("Bucket:", self.input_bucket)
        influx_layout.addRow("Token:", self.input_token)
        influx_group.setLayout(influx_layout)
        self.layout.addWidget(influx_group)

        # --- 3. CONFIG MQTT ---
        mqtt_group = QGroupBox("3. Origen: MQTT (Mosquitto)")
        mqtt_layout = QFormLayout()

        saved_mqtt_user = core.get_setting("mqtt_user", "shmuser")
        saved_mqtt_pass = core.get_setting("mqtt_pass", "shm1234")

        self.input_mqtt_user = QLineEdit(saved_mqtt_user)
        self.input_mqtt_pass = QLineEdit(saved_mqtt_pass)
        self.input_mqtt_pass.setEchoMode(QLineEdit.Password)

        mqtt_layout.addRow("Usuario MQTT:", self.input_mqtt_user)
        mqtt_layout.addRow("Password MQTT:", self.input_mqtt_pass)
        mqtt_layout.addRow(QLabel("(Se conectará a tcp://127.0.0.1:1884)"))

        mqtt_group.setLayout(mqtt_layout)
        self.layout.addWidget(mqtt_group)

        # --- 4. LOGS Y BOTÓN ---
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background: black; color: cyan;")
        self.layout.addWidget(self.log_area)

        self.btn_run = QPushButton("DESCARGAR Y GENERAR CONFIGURACIÓN")
        self.btn_run.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 15px;")
        self.btn_run.clicked.connect(self.start_process)
        self.layout.addWidget(self.btn_run)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta")
        if folder: self.path_input.setText(os.path.normpath(folder))

    def start_process(self):

        core.save_setting("telegraf_url", self.url_input.text())
        core.save_setting("influx_token", self.input_token.text())
        core.save_setting("influx_bucket", self.input_bucket.text())
        core.save_setting("mqtt_user", self.input_mqtt_user.text())
        core.save_setting("mqtt_pass", self.input_mqtt_pass.text())
        core.save_setting("telegraf_path", self.path_input.text())

        self.btn_run.setEnabled(False)

        # Datos
        target = self.path_input.text()
        url_zip = self.url_input.text()
        url_db = self.input_url.text()
        token = self.input_token.text()
        org = self.input_org.text()
        bucket = self.input_bucket.text()
        mqtt_user = self.input_mqtt_user.text()
        mqtt_pass = self.input_mqtt_pass.text()

        def task(log_callback):
            log_callback("--- Iniciando Setup Telegraf ---")
            log_callback(f"URL: {url_zip}")  # Confirmamos qué URL se usa

            success, msg = core.download_and_extract(url_zip, target, log_callback)

            if success:
                log_callback("Generando telegraf.conf con esquema MQTT...")
                ok, res_path = core.setup_telegraf_portable(
                    target, url_db, token, org, bucket, mqtt_user, mqtt_pass, log_callback
                )

                if ok:
                    log_callback("\n[¡ÉXITO TOTAL!]")
                    log_callback(f"Lanzador creado: {res_path}")
                else:
                    log_callback(f"[ERROR Config]: {res_path}")
            else:
                log_callback(f"[ERROR Descarga]: {msg}")

        self.worker = WorkerThread(task)
        self.worker.log_signal.connect(self.log_area.append)
        self.worker.finished_signal.connect(lambda: self.btn_run.setEnabled(True))
        self.worker.start()