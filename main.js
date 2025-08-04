// main.js (modular entry point)
const { app } = require('electron');
const { createWindow, mainWindow, createSettingsWindow } = require('./electron/electron_windows'); // Added createSettingsWindow
const { createTrayIcon } = require('./electron/electron_tray');
const { pythonShell } = require('./electron/electron_python');
const { initializeIpcHandlers } = require('./electron/electron_ipc');
const { setupAppLifecycle } = require('./electron/electron_lifecycle'); // Import lifecycle setup

function main() {
  // Setup app lifecycle handlers first
  setupAppLifecycle();
  
  app.whenReady().then(() => {
    createWindow();
    initializeIpcHandlers();
    setTimeout(() => {
      // Pass app to createTrayIcon as it's used there for quit
      createTrayIcon(mainWindow, pythonShell, createSettingsWindow, app);
    }, 300);
  });
}

// Call the main function to start the app logic
main();
