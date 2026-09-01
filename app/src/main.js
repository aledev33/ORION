// src/main.js — Proceso principal de Electron ORION
const { app, BrowserWindow, ipcMain, screen, session } = require('electron')
const path   = require('path')
const axios  = require('axios')
const http   = require('http')
const { exec, spawn } = require('child_process')
const fs     = require('fs')
const readline = require('readline')

const API_URL    = process.env.ORION_API_URL || 'http://100.101.57.16:8000'
const AGENT_PORT = 8765

const PIPER_EXE   = path.join(__dirname, 'piper', 'piper.exe')
const PIPER_MODEL = path.join(__dirname, 'piper-voices', 'es_MX-claude-high.onnx')
const LISTENER_PY = path.join(__dirname, 'listener_win.py')
const PYTHON_EXE  = 'python'  // usa el python del sistema con vosk instalado

let mainWindow    = null
let overlayWindow = null
let piperMuted    = false
let trayRef       = null
let listenerProc  = null

// ── Tray menu ─────────────────────────────────────────────────────────────────
function buildTrayMenu() {
  if (!trayRef) return
  const { Menu } = require('electron')
  const menu = Menu.buildFromTemplate([
    { label: 'ORION', enabled: false },
    { type: 'separator' },
    { label: '⊞ Abrir panel', click: () => { mainWindow?.show(); mainWindow?.focus() } },
    {
      label: piperMuted ? '🔊 Activar voz' : '🔇 Silenciar voz',
      click: () => {
        piperMuted = !piperMuted
        overlayWindow?.webContents.send('mute-state', piperMuted)
        mainWindow?.webContents.send('mute-state', piperMuted)
        buildTrayMenu()
      }
    },
    { type: 'separator' },
    { label: '✕ Salir', click: () => app.quit() },
  ])
  trayRef.setContextMenu(menu)
}

// ── Ventana principal ─────────────────────────────────────────────────────────
function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 580,
    minWidth: 700,
    minHeight: 460,
    frame: false,
    backgroundColor: '#111318',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    icon: path.join(__dirname, 'Logo_ORION.png'),
    show: false,
  })
  mainWindow.loadFile(path.join(__dirname, 'index.html'))
  mainWindow.once('ready-to-show', () => mainWindow.show())
  mainWindow.on('closed', () => { mainWindow = null })
}

// ── Ventana overlay ───────────────────────────────────────────────────────────
function createOverlayWindow() {
  const { width } = screen.getPrimaryDisplay().workAreaSize
  overlayWindow = new BrowserWindow({
    width: 300,
    height: 300,
    x: width - 315,
    y: 10,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    focusable: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  })
  overlayWindow.loadFile(path.join(__dirname, 'overlay.html'))
  overlayWindow.setIgnoreMouseEvents(true, { forward: true })
}

// ── TTS con Piper ─────────────────────────────────────────────────────────────
function hablar(texto) {
  if (piperMuted || !texto) return

  if (!fs.existsSync(PIPER_EXE) || !fs.existsSync(PIPER_MODEL)) {
    hablarPowerShell(texto)
    return
  }

  try {
    const tmpFile = path.join(process.env.TEMP || 'C:\\Temp', 'orion_tts.wav')

    const piper = spawn(PIPER_EXE, [
      '--model', PIPER_MODEL,
      '--output_file', tmpFile
    ], { stdio: ['pipe', 'ignore', 'ignore'] })

    piper.stdin.write(texto + '\n')
    piper.stdin.end()

    piper.on('close', (code) => {
      if (code === 0 && fs.existsSync(tmpFile)) {
        exec(`powershell -c "(New-Object Media.SoundPlayer '${tmpFile}').PlaySync()"`, (err) => {
          if (err) hablarPowerShell(texto)
        })
      } else {
        hablarPowerShell(texto)
      }
    })
    piper.on('error', () => hablarPowerShell(texto))
  } catch (e) {
    hablarPowerShell(texto)
  }
}

function hablarPowerShell(texto) {
  if (piperMuted) return
  const t = texto.replace(/'/g, "''")
  exec(`powershell -c "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.SelectVoiceByHints('es'); $s.Speak('${t}')"`)
}

// ── Listener de voz (Python + Vosk) ──────────────────────────────────────────
async function ejecutarComandoVoz(comando) {
  console.log(`[Voz] Comando: ${comando}`)
  overlayWindow?.webContents.send('estado', 'procesando')
  mainWindow?.webContents.send('voz-comando', comando)

  // Interceptar sistema localmente
  const cmdLower = comando.toLowerCase()
  const esVolumen = cmdLower.includes('volumen') || cmdLower.includes('mute') ||
                    cmdLower.includes('silencia') || cmdLower.includes('silencio')
  const esLock    = cmdLower.includes('bloquea') || cmdLower.includes('lock')
  const esScreenshot = cmdLower.includes('screenshot') || cmdLower.includes('captura de pantalla')

  if (esVolumen || esLock || esScreenshot) {
    ejecutarSistema(comando)
    const msg = 'Listo.'
    hablar(msg)
    mainWindow?.webContents.send('voz-respuesta', { success: true, message: msg, action: 'SYSTEM_CONTROL_OK' })
    overlayWindow?.webContents.send('estado', 'system_control')
    return
  }

  try {
    const r = await axios.post(`${API_URL}/execute`, { text: comando }, { timeout: 8000 })
    const data = r.data

    // Interceptar OPEN_APP
    if (data.action === 'OPEN_APP_NOT_SUPPORTED_ON_ROBOT' ||
        data.action === 'OPEN_APP_AGENT_FAIL') {
      const appsR = await axios.get(`${API_URL}/apps`, { timeout: 3000 })
      const apps  = appsR.data || []
      const input = comando.toLowerCase().replace(/abre|abre el|abre la|inicia|lanza|pon/g, '').trim()
      for (const ap of apps) {
        const aliases = (ap.aliases || []).map(a => a.alias.toLowerCase())
        const nombre  = ap.name.toLowerCase()
        if (nombre.includes(input) || input.includes(nombre) ||
            aliases.some(a => a.includes(input) || input.includes(a))) {
          abrirAppLocal(ap.exec_path)
          const msg = `Listo, abriendo ${ap.name}.`
          hablar(msg)
          mainWindow?.webContents.send('voz-respuesta', { message: msg, action: 'OPEN_APP_OK' })
          overlayWindow?.webContents.send('estado', 'open_app')
          return
        }
      }
    }

    if (data.message) hablar(data.message)
    mainWindow?.webContents.send('voz-respuesta', data)

    const action = data.action || ''
    if (action.includes('WEB_SEARCH'))    overlayWindow?.webContents.send('estado', 'web_search')
    else if (action.includes('OPEN_APP')) overlayWindow?.webContents.send('estado', 'open_app')
    else if (action.includes('SYSTEM'))   overlayWindow?.webContents.send('estado', 'system_control')
    else if (action.includes('SMALL') || action.includes('PHOTO')) overlayWindow?.webContents.send('estado', 'hablando')
    else if (!data.success)               overlayWindow?.webContents.send('estado', 'error')

  } catch (e) {
    console.log('[Voz] Error ejecutando comando:', e.message)
    overlayWindow?.webContents.send('estado', 'error')
  }
}

function startVoiceListener() {
  if (!fs.existsSync(LISTENER_PY)) {
    console.log('[Voz] listener_win.py no encontrado')
    return
  }

  // Usar el python del .venv si existe, si no el del sistema
  const venvPython = path.join(__dirname, '..', '..', '..', '.venv', 'Scripts', 'python.exe')
  const pythonExe  = fs.existsSync(venvPython) ? venvPython : PYTHON_EXE

  console.log(`[Voz] Iniciando listener con ${pythonExe}`)

  listenerProc = spawn(pythonExe, [LISTENER_PY], {
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  const rl = readline.createInterface({ input: listenerProc.stdout })

  rl.on('line', (line) => {
    line = line.trim()
    console.log(`[Voz] stdout: ${line}`)

    if (line === 'READY') {
      console.log('[Voz] Listener listo, escuchando...')
      overlayWindow?.webContents.send('estado', 'idle')
    } else if (line === 'HOTWORD') {
      console.log('[Voz] Hotword detectada sin comando')
      overlayWindow?.webContents.send('estado', 'escuchando')
    } else if (line.startsWith('CMD:')) {
      const comando = line.slice(4).trim()
      ejecutarComandoVoz(comando)
    }
  })

  listenerProc.stderr.on('data', (data) => {
    const msg = data.toString().trim()
    if (msg && !msg.includes('LOG') && !msg.includes('WARNING')) {
      console.log(`[Voz stderr] ${msg}`)
    }
  })

  listenerProc.on('close', (code) => {
    console.log(`[Voz] Listener terminó con código ${code}. Reiniciando en 3s...`)
    listenerProc = null
    setTimeout(startVoiceListener, 3000)
  })

  listenerProc.on('error', (e) => {
    console.log(`[Voz] Error al iniciar listener: ${e.message}`)
  })
}

// ── Abrir app localmente ──────────────────────────────────────────────────────
function abrirAppLocal(cmd) {
  if (!cmd) return
  if (cmd.startsWith('http')) {
    exec(`start "" "${cmd}"`)
  } else if (cmd.includes('--')) {
    const match = cmd.match(/^([^\s]+)\s+(.+)$/)
    if (match) exec(`start "" "${match[1]}" ${match[2]}`)
    else exec(`start "" ${cmd}`)
  } else {
    exec(`start "" "${cmd}"`, (err) => {
      if (err) exec(`powershell -WindowStyle Hidden -c "Start-Process '${cmd}'"`)
    })
  }
}

// ── Sistema ───────────────────────────────────────────────────────────────────
function ejecutarSistema(payload) {
  const p = (payload || '').toLowerCase()
  if (p.includes('volumen') && (p.includes('sube') || p.includes('arriba')))
    exec('powershell -c "(New-Object -com WScript.Shell).SendKeys([char]175)"')
  else if (p.includes('volumen') && (p.includes('baja') || p.includes('abajo')))
    exec('powershell -c "(New-Object -com WScript.Shell).SendKeys([char]174)"')
  else if (p.includes('mute') || p.includes('silenci'))
    exec('powershell -c "(New-Object -com WScript.Shell).SendKeys([char]173)"')
  else if (p.includes('screenshot') || p.includes('captura')) {
    const fecha = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    const ruta  = `C:\\Users\\whada\\orion2\\screenshots\\orion_${fecha}.png`
    const ps = [
      'Add-Type -AssemblyName System.Windows.Forms',
      'Add-Type -AssemblyName System.Drawing',
      '$b = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width,[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height)',
      '$g = [System.Drawing.Graphics]::FromImage($b)',
      '$g.CopyFromScreen(0,0,0,0,$b.Size)',
      `$b.Save('${ruta}')`,
      '$g.Dispose()',
      '$b.Dispose()',
    ].join('; ')
    exec(`powershell -c "${ps}"`, (err) => {
      if (err) console.log('[Screenshot] Error:', err.message)
      else console.log('[Screenshot] Guardado:', ruta)
    })
  }
  else if (p.includes('bloquea') || p.includes('lock'))
    exec('rundll32.exe user32.dll,LockWorkStation')
}

// ── Agente HTTP ───────────────────────────────────────────────────────────────
function startLocalAgent() {
  const server = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*')
    res.setHeader('Content-Type', 'application/json')
    if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return }

    if (req.method === 'POST' && req.url === '/run') {
      let body = ''
      req.on('data', chunk => body += chunk)
      req.on('end', () => {
        try {
          const { action, payload } = JSON.parse(body)
          console.log(`[Agente] action=${action}`)
          if (action === 'OPEN_APP') {
            abrirAppLocal(payload)
            res.writeHead(200); res.end(JSON.stringify({ ok: true }))
          } else if (action === 'SYSTEM_CONTROL') {
            ejecutarSistema(payload)
            res.writeHead(200); res.end(JSON.stringify({ ok: true }))
          } else if (action === 'SPEAK') {
            hablar(payload)
            res.writeHead(200); res.end(JSON.stringify({ ok: true }))
          } else {
            res.writeHead(400); res.end(JSON.stringify({ ok: false }))
          }
        } catch (e) {
          res.writeHead(500); res.end(JSON.stringify({ ok: false }))
        }
      })
    } else if (req.method === 'GET' && req.url === '/ping') {
      res.writeHead(200); res.end(JSON.stringify({ ok: true, agent: 'ORION-Laptop' }))
    } else {
      res.writeHead(404); res.end(JSON.stringify({ ok: false }))
    }
  })
  server.listen(AGENT_PORT, '0.0.0.0', () => console.log(`[Agente] Puerto ${AGENT_PORT}`))
}

// ── IPC ───────────────────────────────────────────────────────────────────────
ipcMain.handle('api-commands', async (_, limit = 20) => {
  try {
    const r = await axios.get(`${API_URL}/commands/recent?limit=${limit}`, { timeout: 3000 })
    return { ok: true, data: r.data }
  } catch (e) { return { ok: false, data: [] } }
})

ipcMain.handle('api-execute', async (_, text) => {
  try {
    // Interceptar comandos de sistema localmente antes de mandar a RPi
    const textLower = text.toLowerCase()
    const esVolumen = textLower.includes('volumen') || textLower.includes('mute') ||
                      textLower.includes('silencia') || textLower.includes('silencio')
    const esLock    = textLower.includes('bloquea') || textLower.includes('lock')
    const esScreenshot = textLower.includes('screenshot') || textLower.includes('captura de pantalla')

    if (esVolumen || esLock || esScreenshot) {
      ejecutarSistema(text)
      const msg = 'Listo.'
      hablar(msg)
      return { ok: true, data: { success: true, message: msg, action: 'SYSTEM_CONTROL_OK' } }
    }

    const r = await axios.post(`${API_URL}/execute`, { text }, { timeout: 8000 })
    const data = r.data

    if (data.action === 'OPEN_APP_NOT_SUPPORTED_ON_ROBOT' ||
        data.action === 'OPEN_APP_AGENT_FAIL') {
      const appsR = await axios.get(`${API_URL}/apps`, { timeout: 3000 })
      const apps  = appsR.data || []
      const input = text.toLowerCase().replace(/abre|abre el|abre la|inicia|lanza|pon/g, '').trim()
      for (const ap of apps) {
        const aliases = (ap.aliases || []).map(a => a.alias.toLowerCase())
        const nombre  = ap.name.toLowerCase()
        if (nombre.includes(input) || input.includes(nombre) ||
            aliases.some(a => a.includes(input) || input.includes(a))) {
          abrirAppLocal(ap.exec_path)
          const msg = `Listo, abriendo ${ap.name}.`
          hablar(msg)
          return { ok: true, data: { success: true, message: msg, action: 'OPEN_APP_OK' } }
        }
      }
    }

    if (data.message) hablar(data.message)
    return { ok: true, data }
  } catch (e) { return { ok: false } }
})

ipcMain.handle('api-stats', async () => {
  try {
    const r = await axios.get(`${API_URL}/stats`, { timeout: 3000 })
    return { ok: true, data: r.data }
  } catch (e) { return { ok: false, data: {} } }
})

ipcMain.on('window-minimize', () => mainWindow?.minimize())
ipcMain.on('window-close',    () => mainWindow?.hide())
ipcMain.on('window-show',     () => { mainWindow?.show(); mainWindow?.focus() })
ipcMain.on('toggle-mute',     () => {
  piperMuted = !piperMuted
  overlayWindow?.webContents.send('mute-state', piperMuted)
  mainWindow?.webContents.send('mute-state', piperMuted)
  buildTrayMenu()
})
ipcMain.on('notify-overlay', (_, estado) => {
  overlayWindow?.webContents.send('estado', estado)
})

// ── App ───────────────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  const { Tray, nativeImage } = require('electron')
  const iconPath = path.join(__dirname, 'Logo_ORION.png')
  const icon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 })
  trayRef = new Tray(icon)
  trayRef.setToolTip('ORION')
  buildTrayMenu()
  trayRef.on('double-click', () => { mainWindow?.show(); mainWindow?.focus() })

  createOverlayWindow()
  createMainWindow()
  startLocalAgent()
  startVoiceListener()
})

app.on('window-all-closed', () => {
  if (listenerProc) listenerProc.kill()
  if (process.platform !== 'darwin') app.quit()
})