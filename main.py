# main.py
import os
 
# Silencia el warning de Qt DPI en Windows (no afecta funcionalidad)
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window=false")
 
from orion.gui.main_window import main
 
if __name__ == "__main__":
    main()
 