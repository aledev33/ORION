# ORION — Configuración de Tailscale
# Acceso remoto a la RPi desde cualquier red (casa, universidad, etc.)

## ¿Qué es Tailscale?
# Red privada virtual entre tus dispositivos. Sin configurar routers,
# sin IP dinámica, sin puertos abiertos. Gratis para uso personal.
# Laptop y RPi siempre tendrán la misma IP privada (100.x.x.x)
# sin importar en qué red física estén.

---

## 1. Instalar Tailscale en la Raspberry Pi

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# Abre el link que aparece en consola → autentícate con tu cuenta
```

---

## 2. Instalar Tailscale en tu laptop Windows

Descargar desde: https://tailscale.com/download/windows
Instalar → iniciar sesión con la misma cuenta que usaste en la RPi.

---

## 3. Obtener la IP Tailscale de la RPi

```bash
# En la RPi:
tailscale ip -4
# Ejemplo de salida: 100.64.0.5
```

O desde tu laptop, en el panel de Tailscale verás todos tus dispositivos
con sus IPs asignadas.

---

## 4. Configurar la laptop para conectarse a la RPi

En el `.env` de tu proyecto en Windows, agregar:

```
ORION_API_URL=http://100.64.0.5:8000
```

(Reemplaza 100.64.0.5 con la IP Tailscale real de tu RPi)

Esta IP nunca cambia mientras Tailscale esté activo en ambos dispositivos,
sin importar si estás en casa, universidad o casa de un amigo.

---

## 5. Verificar la conexión

```bash
# Desde tu laptop Windows (PowerShell o CMD):
curl http://100.64.0.5:8000/health
# Debe responder: {"status":"ok","db_connected":true}
```

---

## 6. Hacer que Tailscale arranque automáticamente en la RPi

```bash
sudo systemctl enable tailscaled
# Ya debería estar habilitado desde la instalación, pero por si acaso
```

---

## Orden de arranque al encender la RPi

Systemd gestiona todo automáticamente en este orden:
  1. mariadb.service     → base de datos
  2. tailscaled.service  → red Tailscale
  3. orion-api.service   → FastAPI backend
  4. orion.service       → asistente de voz

Sin hacer nada, ORION estará listo en ~30-40 segundos tras encender.
