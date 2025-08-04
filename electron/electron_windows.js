// electron_windows.js
// Handles main/floating window and proofing window management

const { BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { startPythonBackend } = require('./electron_python');

let mainWindow = null;
// proofingWindow is no longer needed

function createWindow() {
  // Calculate position for main window (top-right corner)
  const mainWindowWidth = 600;
  const mainWindowHeight = 120;
  const mainWindowX = 20; // 20px from left edge
  const mainWindowY = 20; // 20px from top

  mainWindow = new BrowserWindow({
    width: mainWindowWidth,
    height: mainWindowHeight,
    x: mainWindowX,
    y: mainWindowY,
    minHeight: 90,
    frame: false,
    transparent: false, // Temporarily disable transparency for debugging
    resizable: true,
    webPreferences: {
      preload: path.join(__dirname, '../frontend/main/preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      devTools: true // Enable DevTools for debugging
    },
    show: true // Show immediately for debugging
  });

  // Load the main window
  const htmlPath = path.join(__dirname, '../frontend/main/index.html');
  console.log('[DEBUG] Loading index.html from:', htmlPath);
  mainWindow.loadFile(htmlPath)
    .then(() => {
      console.log('[DEBUG] index.html loaded successfully');
    })
    .catch((error) => {
      console.error('[ERROR] Failed to load index.html:', error);
    });

  // Show main window after it's loaded (keeping this for when we re-enable proper show)
  mainWindow.once('ready-to-show', () => {
    console.log('[DEBUG] ready-to-show event fired');
    mainWindow.show();
  });

  // IPC handler for resizing the main window from the renderer
  ipcMain.on('resize-window', (event, { height }) => {
    if (mainWindow && height) {
      const currentBounds = mainWindow.getBounds();
      mainWindow.setBounds({
        x: currentBounds.x,
        y: currentBounds.y,
        width: currentBounds.width, // Keep current width
        height: Math.round(height)
      }, true); // Animate the resize
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
    // No proofingWindow to close anymore
  });

  // Start Python backend when the window is ready
  startPythonBackend(mainWindow);
}

function getMainWindow() {
  return mainWindow;
}


let settingsWindow = null;

function createSettingsWindow(section = null) {
  if (settingsWindow) {
    settingsWindow.focus();
    // If a section is specified and window already exists, navigate to that section
    if (section) {
      settingsWindow.webContents.send('navigate-to-section', section);
    }
    return;
  }

  settingsWindow = new BrowserWindow({
    width: 800,
    height: 600,
    title: 'Citrix Transcriber Settings',
    webPreferences: {
      preload: path.join(__dirname, '../frontend/settings/settings_preload.js'), // Assuming a settings_preload.js for settings IPC
      contextIsolation: true,
      nodeIntegration: false,
      devTools: true // Enable DevTools for settings window for easier debugging
    },
    show: false // Don't show until ready
  });

  settingsWindow.loadFile(path.join(__dirname, '../frontend/settings/settings.html'));

  settingsWindow.once('ready-to-show', () => {
    settingsWindow.show();
    // If a section is specified, navigate to it after the window is ready
    if (section) {
      settingsWindow.webContents.send('navigate-to-section', section);
    }
  });

  settingsWindow.on('closed', () => {
    settingsWindow = null;
  });
}

module.exports = { createWindow, getMainWindow, createSettingsWindow };

