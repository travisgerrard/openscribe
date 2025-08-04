// electron_lifecycle.js
// Handles app lifecycle events (ready, window-all-closed, activate)

const { app } = require('electron');

function setupAppLifecycle() {
  // Handle when all windows are closed
  app.on('window-all-closed', () => {
    console.log('[App Lifecycle] All windows closed');
    // On macOS, apps typically stay running even when all windows are closed
    // unless the user explicitly quits with Cmd+Q
    if (process.platform !== 'darwin') {
      console.log('[App Lifecycle] Platform is not macOS, quitting app');
      gracefulShutdown();
    }
  });

  // Handle app activation (macOS specific)
  app.on('activate', () => {
    console.log('[App Lifecycle] App activated');
    // On macOS, re-create windows when dock icon is clicked and no windows are open
    const { createWindow, mainWindow } = require('./electron_windows');
    if (mainWindow === null) {
      createWindow();
    }
  });

  // Handle before-quit event to ensure Python process cleanup
  app.on('before-quit', (_event) => {
    console.log('[App Lifecycle] Before quit event received');
    gracefulShutdown();
  });

  // Handle will-quit event as backup
  app.on('will-quit', (_event) => {
    console.log('[App Lifecycle] Will quit event received');
    gracefulShutdown();
  });

  // Handle window-all-closed for final cleanup
  app.on('quit', () => {
    console.log('[App Lifecycle] App quit event received');
    gracefulShutdown();
  });
}

function gracefulShutdown() {
  console.log('[App Lifecycle] Initiating graceful shutdown');

  try {
    // Use the proper shutdown function from electron_python module
    const { shutdownPythonBackend } = require('./electron_python');

    // Call the proper shutdown function
    shutdownPythonBackend().then(() => {
      console.log('[App Lifecycle] Python backend shutdown completed');
    }).catch((error) => {
      console.error('[App Lifecycle] Error during Python shutdown:', error);
    });

  } catch (error) {
    console.error('[App Lifecycle] Error during graceful shutdown:', error);
  }
}

module.exports = { setupAppLifecycle, gracefulShutdown };
