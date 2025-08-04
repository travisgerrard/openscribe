// electron_tray.js
// Handles tray icon management and menu actions

const { Tray, Menu, nativeImage, app } = require('electron');
const path = require('path');

function getTrayIconPath(iconName) {
  // In packaged app, use app.getAppPath() to get the correct resource path
  // In development, go up one level from electron/ to project root
  if (app.isPackaged) {
    // For packaged app, icons are in the asar file
    return path.join(app.getAppPath(), iconName);
  } else {
    // For development, icons are in the project directory (go up from electron/ to root)
    return path.join(__dirname, '..', iconName);
  }
}

const trayIconPaths = {
  green: getTrayIconPath('assets/icon-green.png'),
  orange: getTrayIconPath('assets/icon-orange.png'),
  blue: getTrayIconPath('assets/icon-blue.png'),
  grey: getTrayIconPath('assets/icon-grey.png')
};

// Pre-load and cache all tray icons to prevent flashing
let trayIcons = {};
let tray = null;

function preloadTrayIcons() {
  trayIcons = {
    green: nativeImage.createFromPath(trayIconPaths.green).resize({ width: 16, height: 16 }),
    orange: nativeImage.createFromPath(trayIconPaths.orange).resize({ width: 16, height: 16 }),
    blue: nativeImage.createFromPath(trayIconPaths.blue).resize({ width: 16, height: 16 }),
    grey: nativeImage.createFromPath(trayIconPaths.grey).resize({ width: 16, height: 16 })
  };
}

function setTrayIconByState(state) {
  if (!tray) return;
  let icon;
  switch (state) {
  case 'dictation':
    icon = trayIcons.green;
    break;
  case 'processing':
    icon = trayIcons.orange;
    break;
  case 'activation':
    icon = trayIcons.blue;
    break;
  case 'preparing':
  case 'inactive':
  default:
    icon = trayIcons.grey;
    break;
  }
  if (icon) {
    tray.setImage(icon);
  }
}

function createTrayIcon(mainWindow, pythonShell, createSettingsWindow, app) {
  if (tray) {
    console.log('Tray icon already exists.');
    return;
  }

  // Pre-load all tray icons to prevent flashing
  preloadTrayIcons();
  const iconPath = getTrayIconPath('assets/icon.png');
  let icon = nativeImage.createFromPath(iconPath);
  if (icon.isEmpty()) {
    console.error(`ERROR: Icon image loaded from path "${iconPath}" but is empty.`);
    return;
  }
  if (process.platform === 'darwin') {
    icon.setTemplateImage(true);
  }
  const resizedIcon = icon.resize({ width: 16, height: 16 });
  tray = new Tray(resizedIcon);

  // Set initial tray icon to grey immediately after creation
  console.log('[Tray] Setting initial tray icon to grey (inactive state)');
  tray.setImage(trayIcons.grey);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Start Dictation',
      click: () => {
        const { getPythonShell } = require('./electron_python');
        const pythonShell = getPythonShell();
        if (pythonShell) {
          pythonShell.send('start_dictate');
        } else {
          console.error('Tray Menu Error: Python backend not running.');
        }
      }
    },
    {
      label: 'Start Proof',
      click: () => {
        const { getPythonShell } = require('./electron_python');
        const pythonShell = getPythonShell();
        if (pythonShell) {
          pythonShell.send('start_proofread');
        } else {
          console.error('Tray Menu Error: Python backend not running.');
        }
      }
    },
    { label: 'Settings...', accelerator: 'CmdOrCtrl+,', click: createSettingsWindow },
    { label: 'Vocabulary', click: () => createSettingsWindow('vocabulary') },
    { type: 'separator' },
    { label: 'Show Floating UI', click: () => { if (mainWindow) mainWindow.show(); } },
    { label: 'Quit Citrix Transcriber', accelerator: 'CmdOrCtrl+Q', click: () => { app.quit(); } }
  ]);
  tray.setContextMenu(contextMenu);
}

module.exports = { setTrayIconByState, createTrayIcon, tray };
