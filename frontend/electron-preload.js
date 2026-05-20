const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  // Window controls
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),
  setAlwaysOnTop: (flag) => ipcRenderer.send('window-set-always-on-top', flag),
  setOpacity: (opacity) => ipcRenderer.send('window-set-opacity', opacity),
  resize: (mode) => ipcRenderer.send('window-resize', mode),

  // Status listeners
  onAlwaysOnTopStatus: (callback) => {
    ipcRenderer.on('window-always-on-top-status', (_event, flag) => callback(flag));
  },

  // Global shortcut listener
  onTriggerCapture: (callback) => {
    ipcRenderer.on('trigger-capture', () => callback());
  },

  // Native screen capture (silent — no permission dialog)
  captureScreen: () => ipcRenderer.invoke('capture-screen'),
});
