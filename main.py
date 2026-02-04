import sys
import ctypes
import os
import traceback
# 1. AÑADIMOS QIcon A LAS IMPORTACIONES
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui import MainWindow


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    script = os.path.abspath(sys.argv[0])
    # Aseguramos comillas por si hay espacios en la ruta
    params = f'"{script}"'
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)


if __name__ == "__main__":
    try:
        if is_admin():
            # --- INICIO MODIFICACIÓN ICONO ---
            app = QApplication(sys.argv)

            # 2. CALCULAR LA RUTA ABSOLUTA AL ICONO
            # Obtenemos el directorio donde está este archivo main.py
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # Construimos la ruta completa hacia assets/logo.png
            icon_path = os.path.join(base_dir, "assets", "logo.jpg")

            # Verificación opcional (útil para depurar)
            if not os.path.exists(icon_path):
                print(f"ADVERTENCIA: No se encontró el icono en: {icon_path}")
            else:
                # 3. ESTABLECER EL ICONO GLOBAL DE LA APP
                app.setWindowIcon(QIcon(icon_path))
            # --- FIN MODIFICACIÓN ICONO ---

            window = MainWindow()
            window.show()
            sys.exit(app.exec())
        else:
            print("Solicitando permisos de administrador...")
            run_as_admin()

    except Exception as e:
        print("ERROR:")
        traceback.print_exc()
        input("Presiona ENTER para salir...")

