# ORION Robot — Guía de instalación en Raspberry Pi 4
# Debian GNU/Linux 13 (Trixie) · aarch64

## Prerequisitos de hardware
- Raspberry Pi 4 (2GB RAM mínimo recomendado, 4GB ideal)
- Micrófono USB
- Altavoces (jack 3.5mm o USB)
- Pantalla OLED SSD1306 0.96" I2C (opcional pero recomendada)
  - Conexión: SDA → Pin 3, SCL → Pin 5, VCC → 3.3V, GND → GND

---

## 1. Paquetes del sistema

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
    git \
    python3-pip \
    python3-venv \
    espeak-ng \
    portaudio19-dev \
    python3-pyaudio \
    alsa-utils \
    pulseaudio \
    scrot \
    i2c-tools \
    python3-smbus \
    libgirepository1.0-dev \
    wget
```

---

## 2. Habilitar I2C (para pantalla OLED)

```bash
sudo raspi-config
# Interface Options → I2C → Enable → Finish

sudo reboot

# Después del reboot, verificar que la pantalla aparece:
sudo i2cdetect -y 1
# Debe mostrar 0x3C (o 0x3D) en la tabla
```

---

## 3. Clonar / copiar el proyecto

```bash
# Si tienes el proyecto en tu laptop, copiarlo con scp:
scp -r /ruta/local/orion2 pi@<IP_DE_RPi>:~/orion2

# O desde git (si tienes repositorio remoto):
git clone <tu-repo> ~/orion2
```

---

## 4. Entorno virtual Python

```bash
cd ~/orion2
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements-rpi.txt
```

---

## 5. Modelo Vosk

> IMPORTANTE: El modelo grande (vosk-model-es-0.42, 1.8GB) puede tardar
> hasta 20 segundos en cargar en RPi 4. Es funcional pero lento en el
> arranque inicial. Para hotword inmediata, considera usar el modelo small
> solo para hotword (mejora futura).

```bash
mkdir -p ~/orion2/models/vosk-es

# Copiar desde tu laptop:
scp -r /ruta/local/orion2/models/vosk-es pi@<IP_DE_RPi>:~/orion2/models/

# O descargar directamente en la RPi (requiere buena conexión):
cd ~/orion2/models/vosk-es
wget https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip
unzip vosk-model-es-0.42.zip
mv vosk-model-es-0.42/* .
rm -rf vosk-model-es-0.42 vosk-model-es-0.42.zip
```

---

## 6. Piper TTS (voz natural offline)

```bash
# Descargar el binario de Piper para aarch64
cd /tmp
wget https://github.com/rhasspy/piper/releases/latest/download/piper_linux_aarch64.tar.gz
tar -xzf piper_linux_aarch64.tar.gz
sudo mv piper /usr/local/bin/
piper --version  # verificar instalación

# Descargar modelo de voz en español mexicano
mkdir -p ~/piper-models
cd ~/piper-models
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/claude/high/es_MX-claude-high.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/claude/high/es_MX-claude-high.onnx.json
```

---

## 7. Variables de entorno (.env)

```bash
nano ~/orion2/.env
```

Contenido mínimo:
```
MARIADB_USER=orion_user
MARIADB_PASSWORD=tu_password_aqui
MARIADB_HOST=127.0.0.1
MARIADB_PORT=3306
MARIADB_DB=orion_db
TAVILY_API_KEY=tu_clave_aqui
PIPER_MODEL_PATH=/home/pi/piper-models/es_MX-claude-high.onnx
```

---

## 8. MariaDB en la Raspberry Pi

```bash
sudo apt install -y mariadb-server

sudo systemctl enable mariadb
sudo systemctl start mariadb

# Configuración inicial
sudo mysql_secure_installation

# Crear usuario y base de datos para ORION
sudo mysql -u root -p << 'EOF'
CREATE DATABASE IF NOT EXISTS orion_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'orion_user'@'localhost' IDENTIFIED BY 'tu_password_aqui';
GRANT ALL PRIVILEGES ON orion_db.* TO 'orion_user'@'localhost';
FLUSH PRIVILEGES;
EOF
```

---

## 9. Iniciar la API de ORION

```bash
cd ~/orion2
source .venv/bin/activate

# Primer arranque: crear tablas en MariaDB
uvicorn orion.orion_api.app.main:app --host 127.0.0.1 --port 8000

# Ctrl+C para detener, luego en producción lo gestiona systemd
```

---

## 10. Probar ORION manualmente

```bash
cd ~/orion2
source .venv/bin/activate

# Probar que el audio funciona
arecord -d 3 -f cd test.wav && aplay test.wav

# Probar que Piper funciona
echo "Hola, soy ORION" | piper --model ~/piper-models/es_MX-claude-high.onnx --output-raw | aplay -r 22050 -f S16_LE -c 1

# Iniciar ORION
python main_robot.py
```

---

## 11. Configurar systemd (arranque automático)

```bash
# Editar orion.service y verificar que el usuario sea correcto
# (cambiar "pi" por tu usuario si es diferente)
nano ~/orion2/orion.service

sudo cp ~/orion2/orion.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable orion
sudo systemctl start orion

# Ver logs en tiempo real
sudo journalctl -u orion -f
```

---

## Verificación final

```bash
# Estado del servicio
sudo systemctl status orion

# Reiniciar
sudo systemctl restart orion

# Ver logs de los últimos 50 eventos
sudo journalctl -u orion -n 50 --no-pager
```

---

## Solución de problemas frecuentes

**"No se detectó micrófono"**
```bash
arecord -l           # listar dispositivos de captura
# Si no aparece nada, verificar conexión USB del micrófono
```

**"Piper no disponible"**
```bash
which piper          # debe mostrar /usr/local/bin/piper
piper --version
ls ~/piper-models/   # debe contener el .onnx y .onnx.json
```

**"No se pudo inicializar pantalla OLED"**
```bash
sudo i2cdetect -y 1  # verificar dirección I2C (0x3C o 0x3D)
# Si la dirección es 0x3D, actualizar OLED_I2C_ADDRESS en orion/config.py
```

**"API no disponible, catálogo vacío"**
```bash
# Verificar que la API esté corriendo
curl http://127.0.0.1:8000/apps
# Si no responde, iniciar uvicorn manualmente primero
```

**El modelo Vosk tarda mucho en cargar**
```bash
# Normal en el primer arranque con el modelo de 1.8GB.
# Esperar ~20 segundos. Los arranques subsecuentes son igual de lentos
# porque el modelo se carga desde disco cada vez.
# Solución futura: usar vosk-model-small-es-0.42 para hotword.
```