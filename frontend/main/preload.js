const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Send data/commands to the Python backend via the main process
  sendToPython: (data) => ipcRenderer.send('to-python', data),

  // Receive messages from the Python backend (forwarded by main process)
  handleFromPython: (callback) => ipcRenderer.on('from-python', (_event, value) => callback(value)),

  // Receive stderr messages from the Python backend
  handlePythonStderr: (callback) => ipcRenderer.on('python-stderr', (_event, value) => callback(value)),

  // Send toggle always on top request to main process
  toggleAlwaysOnTop: (forceState) => ipcRenderer.send('toggle-always-on-top', forceState), // forceState can be true, false, or undefined (to toggle)

  // Control proofing window pinned state
  setProofingPinned: (forceState) => ipcRenderer.send('set-proofing-pinned', forceState),

  // Send stop dictation request (process audio) to main process
  stopDictation: () => ipcRenderer.send('stop-dictation'),

  // Send abort dictation request (discard audio) to main process
  abortDictation: () => ipcRenderer.send('abort-dictation'), // New function

  // Send tray state to main process for icon update
  sendTrayState: (state) => ipcRenderer.send('set-tray-state', state),

  // Show/hide proofing window
  showProofingWindow: (show) => ipcRenderer.send('show-proofing-window', show),

  // Send resize window request to main process
  resizeWindow: (data) => ipcRenderer.send('resize-window', data),

  // Clean up listeners when they are no longer needed (important!)
  removeListener: (channel) => ipcRenderer.removeAllListeners(channel),

  // Generic listener for specific channels from main process
  on: (channel, callback) => {
    // Deliberately strip event from callback to match other handlers
    const newCallback = (_, data) => {
      if (channel === 'ui-update') {
        // console.log(`[Preload: ui-update] Received data: ${JSON.stringify(data)}`);
      }
      callback(data);
    };
    ipcRenderer.on(channel, newCallback);
    // Return a function to remove the listener, consistent with some event emitter patterns
    return () => ipcRenderer.removeListener(channel, newCallback);
  }
});

console.log('Preload script loaded.');