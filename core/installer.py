import subprocess


def install_package(package_id, log_callback=None):
    """
    Instala un paquete usando Winget.
    Detecta si ya está instalado para no detener el proceso.
    """
    # Agregamos parámetros para evitar preguntas interactivas
    command = f"winget install --id {package_id} -e --silent --accept-package-agreements --accept-source-agreements"

    # Palabras clave que indican que, aunque no se instaló nada nuevo, todo está bien.
    # Cubrimos español e inglés por si acaso.
    success_keywords = [
        "ya instalado",
        "already installed",
        "correctamente",
        "successfully",
        "ninguna actualización",  # Caso: No update available
        "no update available"
    ]

    found_success_keyword = False

    try:
        if log_callback:
            log_callback(f"Ejecutando: {package_id}...")

        # Ejecutamos el proceso
        process = subprocess.Popen(
            ["powershell", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
            encoding='utf-8',  # Forzamos utf-8 para leer tildes
            errors='replace'  # Si hay caracteres raros, no romper el programa
        )

        # Leer salida línea por línea en tiempo real
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break

            if line:
                cleaned_line = line.strip()
                if log_callback: log_callback(cleaned_line)

                # Buscamos si la línea contiene alguna palabra de éxito
                for keyword in success_keywords:
                    if keyword.lower() in cleaned_line.lower():
                        found_success_keyword = True

        rc = process.poll()

        # LÓGICA MEJORADA:
        # Es éxito si el código es 0 O SI encontramos texto que dice "ya instalado"
        if rc == 0 or found_success_keyword:
            if log_callback: log_callback(f"\n[OK] El paquete {package_id} está listo.")
            return True, "Listo"
        else:
            # Si falló, leemos el error real
            err = process.stderr.read()
            if log_callback: log_callback(f"[ERROR CRÍTICO]: {err}")
            return False, err

    except Exception as e:
        return False, str(e)