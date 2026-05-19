# orion/os_apps/launcher.py
import subprocess
import sys
import os
 
 
def abrir_app(exec_path: str) -> bool:
    """
    Abre una aplicación dado su exec_path.
    - Windows: usa os.startfile() para .exe o shell=True para rutas con argumentos
    - Linux:   usa subprocess.Popen directamente
    """
    try:
        if not exec_path:
            return False
 
        if sys.platform == "win32":
            if ".exe" in exec_path.lower():
                subprocess.Popen(exec_path, shell=True)
            else:
                os.startfile(exec_path)
        else:
            # Linux / Raspberry Pi: lanzar directamente como proceso
            subprocess.Popen(
                exec_path.split(),   # soporta "app --flag" también
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
 
        return True
    except Exception as e:
        print(f"[ERROR] No se pudo abrir la app: {e}")
        return False