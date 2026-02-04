import os
import subprocess


def write_file(path, content, log_callback=None):
    """Escribe contenido en un archivo, creando directorios si no existen."""
    try:
        if log_callback: log_callback(f"Configurando archivo en: {path}")

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding='utf-8') as f:
            f.write(content)

        if log_callback: log_callback("Configuración guardada exitosamente.\n")
        return True
    except Exception as e:
        if log_callback: log_callback(f"ERROR escribiendo config: {str(e)}")
        return False


def configure_mosquitto(target_dir, username, password, log_callback=None):
    """
    Configura Mosquitto, genera passwords y CREA EL LANZADOR .BAT
    """
    if log_callback: log_callback("\n--- CONFIGURANDO MOSQUITTO ---")

    # 1. Rutas
    data_dir = os.path.join(target_dir, "data")
    passwd_file = os.path.join(target_dir, "passwd")
    conf_file = os.path.join(target_dir, "mosquitto.conf")

    # Ruta donde se instala el ejecutable (Winget por defecto)
    program_files_mosquitto = r"C:\Program Files\Mosquitto"
    mosquitto_exe = os.path.join(program_files_mosquitto, "mosquitto.exe")
    mosquitto_passwd_exe = os.path.join(program_files_mosquitto, "mosquitto_passwd.exe")

    # Crear carpetas necesarias
    os.makedirs(data_dir, exist_ok=True)

    # 2. Generar Password (hash)
    if os.path.exists(mosquitto_passwd_exe):
        if log_callback: log_callback(f"Creando usuario MQTT: {username}")
        cmd = [mosquitto_passwd_exe, "-c", "-b", passwd_file, username, password]
        try:
            # creationflags=0x08000000 oculta la consola negra momentánea
            subprocess.run(cmd, check=True, creationflags=0x08000000)
            if log_callback: log_callback("Archivo de contraseñas generado.")
        except subprocess.CalledProcessError as e:
            if log_callback: log_callback(f"ERROR generando password: {e}")
    else:
        if log_callback: log_callback("ADVERTENCIA: No se encontró mosquitto_passwd.exe (¿No se instaló aún?)")

    # 3. Crear mosquitto.conf
    # Importante: Rutas con doble barra para que Windows no falle
    safe_passwd = passwd_file.replace("\\", "\\\\")
    safe_data = data_dir.replace("\\", "\\\\")
    if not safe_data.endswith("\\\\"): safe_data += "\\\\"
    safe_log = os.path.join(target_dir, "mosquitto.log").replace("\\", "\\\\")

    config_content = f"""listener 1884
protocol mqtt

allow_anonymous false
password_file {safe_passwd}

persistence true
persistence_location {safe_data}

log_dest file {safe_log}
log_dest stdout
log_type all
"""
    write_file(conf_file, config_content, log_callback)

    # --- 4. CREAR SCRIPT DE ARRANQUE (.BAT) ---
    # Este es el paso nuevo que pediste.

    bat_path = os.path.join(target_dir, "3_INICIAR_MQTT.bat")

    # Explicación del BAT:
    # 1. @echo off: Limpia la pantalla.
    # 2. cd /d ...: Cambia al directorio del ejecutable (Vital para que cargue las DLLs).
    # 3. mosquitto.exe -c ... -v: Ejecuta usando TU archivo de config y modo verbose (-v).

    bat_content = f"""@echo off
title Servidor Mosquitto MQTT (Puerto 1884)
echo ---------------------------------------------------
echo INICIANDO SERVIDOR MQTT
echo Conf: "{conf_file}"
echo ---------------------------------------------------
echo.

cd /d "{program_files_mosquitto}"

if exist mosquitto.exe (
    mosquitto.exe -c "{conf_file}" -v
) else (
    echo ERROR: No se encuentra mosquitto.exe en:
    echo {program_files_mosquitto}
    echo Por favor instala Mosquitto primero.
    pause
)
pause
"""

    if write_file(bat_path, bat_content, log_callback):
        if log_callback:
            log_callback("\n[¡LISTO!]")
            log_callback(f"He creado el lanzador en: {bat_path}")
            log_callback("Dale doble clic a ese archivo para iniciar el servidor.")

    return True


def configure_telegraf(influx_url, influx_token, org, bucket, log_callback=None):
    # Ruta típica de Telegraf
    path = r"C:\Program Files\Telegraf\telegraf.conf"

    config_content = f"""
[agent]
  interval = "1.0s"
  round_interval = true
  metric_batch_size = 1200
  metric_buffer_limit = 3600000
  collection_jitter = "0s"
  flush_interval = "1s"
  flush_jitter = "0.1s"
  precision = ""
  debug = false
  quiet = false
  logfile = ""
  hostname = ""
  omit_hostname = false

[[outputs.influxdb_v2]]
  urls = ["{influx_url}"]
  token = "{influx_token}"
  organization = "{org}"
  bucket = "{bucket}"

[[inputs.cpu]]
  percpu = true
  totalcpu = true
  collect_cpu_time = false
  report_active = false
[[inputs.disk]]
  ignore_fs = ["tmpfs", "devtmpfs", "devfs", "iso9660", "overlay", "aufs", "squashfs"]
[[inputs.mem]]
[[inputs.system]]
    """
    return write_file(path, config_content, log_callback)


def setup_influxdb(username, password, org, bucket, log_callback=None):
    """
    Ejecuta el comando 'influx setup' para inicializar la base de datos.
    Solo funciona si InfluxDB está recién instalado y nunca se ha configurado.
    """
    # Winget suele instalar el cliente CLI 'influx.exe' también.
    # Si no está en el PATH, habría que buscar su ruta, pero probemos directo.

    command = [
        "influx", "setup",
        "--username", username,
        "--password", password,
        "--org", org,
        "--bucket", bucket,
        "--force"  # Fuerza la configuración sin pedir confirmación interactiva
    ]

    try:
        if log_callback: log_callback(f"Configurando InfluxDB: Org={org}, Bucket={bucket}...")

        # creationflags=0x08000000 oculta la ventana de consola en Windows (CREATE_NO_WINDOW)
        process = subprocess.run(command, capture_output=True, text=True, creationflags=0x08000000)

        if process.returncode == 0:
            if log_callback:
                log_callback("ÉXITO: InfluxDB configurado.")
                log_callback(f"Token Admin: Revisa la salida o la UI web.")
                log_callback(process.stdout)  # El token suele salir aquí
            return True
        else:
            if log_callback:
                log_callback("ADVERTENCIA: No se pudo configurar (¿Quizás ya estaba configurado?)")
                log_callback(f"Detalle: {process.stderr}")
            return False

    except FileNotFoundError:
        if log_callback: log_callback("ERROR: No se encontró el comando 'influx'. Reinicia el PC tras instalar.")
        return False