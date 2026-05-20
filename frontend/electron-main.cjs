const { app, BrowserWindow, ipcMain, desktopCapturer, screen, globalShortcut } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenW, height: screenH } = primaryDisplay.workAreaSize;

  mainWindow = new BrowserWindow({
    width: 380,
    height: 680,
    x: screenW - 400,
    y: Math.round(screenH / 2 - 340),
    minWidth: 320,
    minHeight: 400,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    hasShadow: false,
    skipTaskbar: true,
    resizable: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'electron-preload.js'),
    },
  });

  // Make the window click-through in transparent regions
  mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  // Check if we are in development mode
  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

  if (isDev) {
    mainWindow.loadURL('http://127.0.0.1:5173');
    // mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  createWindow();

  // Register global shortcut for quick capture (restores and shows window if minimized/hidden)
  globalShortcut.register('CommandOrControl+Shift+S', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) {
        mainWindow.restore();
      }
      mainWindow.show();
      mainWindow.focus();
      // Small timeout to allow the window to show up before starting capture
      setTimeout(() => {
        mainWindow.webContents.send('trigger-capture');
      }, 50);
    }
  });

  // Register global shortcut to toggle overlay visibility (Show / Hide)
  globalShortcut.register('CommandOrControl+Shift+H', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized() || !mainWindow.isVisible()) {
        mainWindow.restore();
        mainWindow.show();
        mainWindow.focus();
      } else {
        mainWindow.minimize();
      }
    }
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// ─── IPC: Window Controls ────────────────────────────────────────────
ipcMain.on('window-minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.on('window-close', () => {
  if (mainWindow) mainWindow.close();
});

ipcMain.on('window-set-always-on-top', (event, flag) => {
  if (mainWindow) {
    mainWindow.setAlwaysOnTop(flag, 'screen-saver');
    event.reply('window-always-on-top-status', flag);
  }
});

// ─── IPC: Set Window Opacity ─────────────────────────────────────────
ipcMain.on('window-set-opacity', (event, opacity) => {
  if (mainWindow) {
    mainWindow.setOpacity(Math.max(0.1, Math.min(1.0, opacity)));
  }
});

// ─── IPC: Resize Window (compact / expanded) ────────────────────────
ipcMain.on('window-resize', (event, mode) => {
  if (!mainWindow) return;
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenW, height: screenH } = primaryDisplay.workAreaSize;

  if (mode === 'compact') {
    mainWindow.setBounds({
      width: 380,
      height: 220,
      x: screenW - 400,
      y: screenH - 240,
    }, true);
  } else if (mode === 'expanded') {
    mainWindow.setBounds({
      width: 400,
      height: 700,
      x: screenW - 420,
      y: Math.round(screenH / 2 - 350),
    }, true);
  }
});

// ─── IPC: Native Screen Capture (silent, no permission dialog) ──────
ipcMain.handle('capture-screen', async () => {
  try {
    // Briefly hide the overlay so we don't capture it
    if (mainWindow) {
      mainWindow.setOpacity(0);
    }

    // Small delay to let the OS finish hiding
    await new Promise(resolve => setTimeout(resolve, 150));

    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: {
        width: 1920,
        height: 1080,
      },
    });

    // Restore overlay
    if (mainWindow) {
      mainWindow.setOpacity(1);
    }

    if (sources.length === 0) {
      return { success: false, error: 'No screens found' };
    }

    // Use primary screen
    const primarySource = sources[0];
    const thumbnail = primarySource.thumbnail;

    // Convert NativeImage to base64 PNG
    const pngBuffer = thumbnail.toPNG();
    const base64 = pngBuffer.toString('base64');

    return {
      success: true,
      image_base64: base64,
      screen_name: primarySource.name,
      width: thumbnail.getSize().width,
      height: thumbnail.getSize().height,
    };
  } catch (error) {
    // Restore overlay on error
    if (mainWindow) {
      mainWindow.setOpacity(1);
    }
    return { success: false, error: error.message };
  }
});
