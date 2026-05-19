// src/preload.js
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('orion', {
  getCommands:   (limit) => ipcRenderer.invoke('api-commands', limit),
  execute:       (text)  => ipcRenderer.invoke('api-execute', text),
  getStats:      ()      => ipcRenderer.invoke('api-stats'),
  minimize:      ()      => ipcRenderer.send('window-minimize'),
  close:         ()      => ipcRenderer.send('window-close'),
  show:          ()      => ipcRenderer.send('window-show'),
  toggleMute:    ()      => ipcRenderer.send('toggle-mute'),
  notifyOverlay: (e)     => ipcRenderer.send('notify-overlay', e),
  onEstado:      (cb)    => ipcRenderer.on('estado',       (_, e) => cb(e)),
  onMuteState:   (cb)    => ipcRenderer.on('mute-state',   (_, m) => cb(m)),
  onVozComando:  (cb)    => ipcRenderer.on('voz-comando',  (_, c) => cb(c)),
  onVozRespuesta:(cb)    => ipcRenderer.on('voz-respuesta',(_, r) => cb(r)),
})