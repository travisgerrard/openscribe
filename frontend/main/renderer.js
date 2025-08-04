// Modularized renderer.js entry point
// Imports and initializes all renderer logic

import { drawWaveform } from '../shared/renderer_waveform.js';
import { registerIPCHandlers } from '../shared/renderer_ipc.js';
import { logMessage } from '../shared/renderer_utils.js';
import { initializeExpansionUi } from '../shared/renderer_expansion_ui.js';
import { initializeStatusIndicator } from '../shared/renderer_state.js';
import { initializeControls } from '../shared/renderer_controls.js';

// Initialize modules
registerIPCHandlers();
drawWaveform();
initializeExpansionUi();

// Initialize status indicator to grey after DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  console.log('[Renderer] DOM loaded, initializing status indicator to grey');
  initializeStatusIndicator();
  initializeControls();
});

logMessage('Renderer process started.');

