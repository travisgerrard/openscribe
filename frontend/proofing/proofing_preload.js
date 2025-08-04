// proofing_preload.js
// Minimal IPC bridge for the proofing window

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // send messages to main
  send: (channel, ...args) => {
    console.log('[Preload] send:', channel, args);
    ipcRenderer.send(channel, ...args);
  },

  // receive messages from main
  on: (channel, listener) => {
    console.log('[Preload] on:', channel);
    if (channel === 'proof-stream') {
      ipcRenderer.on(channel, (_event, data) => listener(_event, data));
    }
  },
});

console.log('[Preload] proofing_preload.js loaded');
if (typeof window !== 'undefined') window._proofingPreloadLoaded = true;