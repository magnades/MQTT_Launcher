import json
import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout, QSpinBox,
    QDoubleSpinBox, QLabel, QProgressBar, QGroupBox,
    QTextEdit, QHBoxLayout
)
from PySide6.QtCore import QTimer, Qt

# =========================================================
# === MODELO FÍSICO =======================================
# =========================================================

OVERHEAD_BYTES = 60
WIFI_LIMIT_KB = 2000.0
PPS_LIMIT = 5000.0
CPU_LIMIT = 5000.0
IOPS_LIMIT = 10.0
COMPRESSION_RATIO = 0.20


def real_payload_bytes(json_text: str) -> int:
    try:
        return len(json.dumps(json.loads(json_text), separators=(",", ":")).encode())
    except Exception:
        return 0


def compute_metrics(N, Q, L, payload_bytes):
    msgs_per_sec = N * Q
    total_msg_size = payload_bytes + OVERHEAD_BYTES

    # Red
    bytes_per_sec = msgs_per_sec * total_msg_size
    kb_per_sec = bytes_per_sec / 1024.0

    # Disco (IOPS)
    safe_L = max(0.01, L)
    iops = 1.0 / safe_L

    # Proyecciones
    bytes_per_day_db = bytes_per_sec * 3600 * 24 * COMPRESSION_RATIO
    gb_per_month = (bytes_per_day_db * 30) / (1024 ** 3)
    buffer_1h_msgs = msgs_per_sec * 3600
    ram_mb = (buffer_1h_msgs * total_msg_size * 2) / (1024 ** 2)

    # --- CÁLCULOS DE CONFIGURACIÓN ---

    # 1. Batch Size
    # Debe ser lo suficientemente grande para contener todos los mensajes que llegan
    # durante el tiempo de espera (L), más un 20% de margen.
    batch = max(int(msgs_per_sec * L * 1.2), 1000)

    # 2. Buffer Limit
    # Debe poder guardar 1 hora de datos en RAM si se cae la red.
    buffer_limit = int(max(10000, buffer_1h_msgs))

    # 3. Jitter (Aleatoriedad)
    # Importante para que no todos los procesos escriban en el milisegundo 000 exacto.
    jitter = L * 0.1

    return {
        "msgs_per_sec": msgs_per_sec,
        "kb_per_sec": kb_per_sec,
        "iops": iops,
        "payload_bytes": payload_bytes,
        "gb_per_month": gb_per_month,
        "ram_mb": ram_mb,

        "batch": batch,
        "buffer_limit": buffer_limit,
        "jitter": jitter,

        "wifi_pct": (kb_per_sec / WIFI_LIMIT_KB) * 100,
        "pps_pct": (msgs_per_sec / PPS_LIMIT) * 100,
        "cpu_pct": (msgs_per_sec / CPU_LIMIT) * 100,
        "disk_pct": (iops / IOPS_LIMIT) * 100,
    }


# =========================================================
# ===================== UI (VISTA) ========================
# =========================================================

class CalculatorWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calculadora IoT: Análisis Completo")
        self.resize(1150, 800)

        self.setStyleSheet("""
            QWidget { background-color: #2c3e50; color: white; }
            QGroupBox { font-weight: bold; border: 1px solid #7f8c8d; margin-top: 6px; padding-top: 10px; }
            QProgressBar { text-align: center; border: 1px solid #555; background: #34495e; color: white; font-weight: bold; }
            QProgressBar[state="good"]::chunk { background: #27ae60; }
            QProgressBar[state="warn"]::chunk { background: #f39c12; }
            QProgressBar[state="bad"]::chunk { background: #c0392b; }
            QLabel.console { font-family: Consolas; color: #2ecc71; font-weight: bold; font-size: 13px; }
        """)

        self._debounce = QTimer(self)
        self._debounce.setInterval(300)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self.calculate)

        main_layout = QHBoxLayout(self)

        # ========== PANEL IZQUIERDO ==========
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Inputs
        gb_input = QGroupBox("1. Variables del Sistema")
        form = QFormLayout()

        self.spin_sensors = QSpinBox()
        self.spin_sensors.setRange(1, 100000)
        self.spin_sensors.setValue(10)
        self.spin_sensors.setSuffix(" disp")

        self.spin_hz = QDoubleSpinBox()
        self.spin_hz.setRange(0.1, 10000.0)
        self.spin_hz.setValue(100.0)
        self.spin_hz.setSuffix(" Hz")

        self.spin_latency = QDoubleSpinBox()
        self.spin_latency.setRange(0.1, 60.0)
        self.spin_latency.setValue(1.0)
        self.spin_latency.setSuffix(" s")

        form.addRow("Nº Sensores:", self.spin_sensors)
        form.addRow("Frecuencia:", self.spin_hz)
        form.addRow("Latencia (Flush):", self.spin_latency)
        gb_input.setLayout(form)
        left_layout.addWidget(gb_input)

        # JSON
        gb_json = QGroupBox("2. Payload JSON")
        l_json = QVBoxLayout()
        self.txt_json = QTextEdit()
        self.txt_json.setMaximumHeight(60)
        self.txt_json.setStyleSheet("background: #111; color: #e67e22; font-family: Consolas; border: none;")
        self.txt_json.setText("""{
  "ts": 946598401852,
  "ax": -0.0293,
  "ay": -0.0132,
  "az": -1.001,
  "lat": 41.55549204890693,
  "lng": -8.412197669159601,
  "sats": 11
}""")
        l_json.addWidget(self.txt_json)
        gb_json.setLayout(l_json)
        left_layout.addWidget(gb_json)

        # Barras
        gb_stats = QGroupBox("3. Diagnóstico")
        l_stats = QVBoxLayout()
        self.bar_wifi = QProgressBar()
        self.bar_pps = QProgressBar()
        self.bar_cpu = QProgressBar()
        self.bar_disk = QProgressBar()
        l_stats.addWidget(QLabel("WiFi:"))
        l_stats.addWidget(self.bar_wifi)
        l_stats.addWidget(QLabel("Router (PPS):"))
        l_stats.addWidget(self.bar_pps)
        l_stats.addWidget(QLabel("CPU Telegraf:"))
        l_stats.addWidget(self.bar_cpu)
        l_stats.addWidget(QLabel("Disco (IOPS):"))
        l_stats.addWidget(self.bar_disk)
        gb_stats.setLayout(l_stats)
        left_layout.addWidget(gb_stats)

        # Resultados
        gb_res = QGroupBox("4. Recomendación [agent]")
        gb_res.setStyleSheet("border: 1px solid #27ae60;")
        l_res = QFormLayout()
        l_res.setLabelAlignment(Qt.AlignLeft)

        self.lbl_interval = QLabel()
        self.lbl_round = QLabel("true")
        self.lbl_batch = QLabel()
        self.lbl_buffer = QLabel()
        self.lbl_col_jitter = QLabel('"0s"')
        self.lbl_flush = QLabel()
        self.lbl_flush_jitter = QLabel()

        for l in [self.lbl_interval, self.lbl_round, self.lbl_batch, self.lbl_buffer,
                  self.lbl_col_jitter, self.lbl_flush, self.lbl_flush_jitter]:
            l.setProperty("class", "console")

        l_res.addRow("interval =", self.lbl_interval)
        l_res.addRow("round_interval =", self.lbl_round)
        l_res.addRow("metric_batch_size =", self.lbl_batch)
        l_res.addRow("metric_buffer_limit =", self.lbl_buffer)
        l_res.addRow("collection_jitter =", self.lbl_col_jitter)
        l_res.addRow("flush_interval =", self.lbl_flush)
        l_res.addRow("flush_jitter =", self.lbl_flush_jitter)

        gb_res.setLayout(l_res)
        left_layout.addWidget(gb_res)

        # ========== PANEL DERECHO ==========
        gb_math = QGroupBox("MEMORIA DE CÁLCULO")
        l_math = QVBoxLayout()
        self.txt_math = QTextEdit()
        self.txt_math.setReadOnly(True)
        self.txt_math.setStyleSheet("background: #2c3e50; color: #ecf0f1; font-family: Consolas; border: none;")
        l_math.addWidget(self.txt_math)
        gb_math.setLayout(l_math)

        main_layout.addWidget(left_panel, 4)
        main_layout.addWidget(gb_math, 5)

        # Conexiones
        for w in [self.spin_sensors, self.spin_hz, self.spin_latency]:
            w.valueChanged.connect(self.schedule_calc)
        self.txt_json.textChanged.connect(self.schedule_calc)

        self.calculate()

    # ===================== LÓGICA UI =====================

    def schedule_calc(self):
        self._debounce.start()

    def set_bar(self, bar, pct):
        val = min(100, int(pct))
        bar.setValue(val)
        if val < 50:
            state = "good"
        elif val < 85:
            state = "warn"
        else:
            state = "bad"
        bar.setProperty("state", state)
        bar.style().polish(bar)

    def calculate(self):
        N = self.spin_sensors.value()
        Q = self.spin_hz.value()
        L = self.spin_latency.value()
        json_txt = self.txt_json.toPlainText()

        payload = real_payload_bytes(json_txt)
        m = compute_metrics(N, Q, L, payload)

        self.set_bar(self.bar_wifi, m["wifi_pct"])
        self.set_bar(self.bar_pps, m["pps_pct"])
        self.set_bar(self.bar_cpu, m["cpu_pct"])
        self.set_bar(self.bar_disk, m["disk_pct"])

        # Asignaciones de Texto
        self.lbl_interval.setText(f'"{L}s"')
        self.lbl_batch.setText(str(m["batch"]))
        self.lbl_buffer.setText(str(m["buffer_limit"]))
        self.lbl_flush.setText(f'"{L}s"')
        self.lbl_flush_jitter.setText(f'"{m["jitter"]:.1f}s"')

        # HTML Explicativo (LA RESPUESTA A TU PREGUNTA)
        html = f"""
        <h3 style='color:#3498db'>1. ¿POR QUÉ interval = {L}s?</h3>
        En MQTT, los datos llegan solos (Push), no por polling.<br>
        Igualamos <b>interval</b> al <b>flush_interval</b> ({L}s) para:<br>
        1. Sincronizar el ciclo de reloj de Telegraf.<br>
        2. Evitar ciclos de CPU innecesarios.<br>
        3. Alinear la recolección de stats internos con la escritura.

        <h3 style='color:#27ae60'>2. TAMAÑO DE LOTE (Batch)</h3>
        Calculado: <b>{m['batch']} mensajes</b><br>
        <i>(Mensajes por segundo x Latencia + 20% margen)</i><br>
        Este es el "paquete" óptimo para que InfluxDB escriba rápido.

        <h3 style='color:#e67e22'>3. BUFFER Y SEGURIDAD</h3>
        Calculado: <b>{m['buffer_limit']} mensajes</b><br>
        Esto protege tus datos en la RAM si InfluxDB se cae por 1 hora.

        <h3 style='color:#c0392b'>4. ESTRÉS DEL DISCO</h3>
        Estás escribiendo cada {L} segundos.<br>
        Impacto: <b>{m['iops']:.2f} escrituras/seg</b>
        
        <h3 style='color:#9b59b6'>5. PROYECCIONES DE ALMACENAMIENTO</h3>
        - Datos diarios (comprimidos): <b>{m['msgs_per_sec'] *
(m['payload_bytes'] + OVERHEAD_BYTES) * 86400 / (1024**2):.2f} MB</b><br>
        - Datos mensuales (comprimidos): <b>{m['gb_per_month']
:.2f} GB</b><br>
        - RAM necesaria (buffer 1h x2): <b>{m['ram_mb']:.2f} MB</b>
                                              
        """
        self.txt_math.setHtml(html)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CalculatorWindow()
    window.show()
    sys.exit(app.exec())