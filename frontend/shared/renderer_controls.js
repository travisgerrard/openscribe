// renderer_controls.js
// Handles button clicks and keyboard shortcuts for stop/cancel functionality

import { stopButton, cancelButton, alwaysOnTopButton } from './renderer_ui.js';
import { logMessage } from './renderer_utils.js';

export function initializeControls() {
  // Stop button click handler
  if (stopButton) {
    stopButton.addEventListener('click', () => {
      logMessage('Stop button clicked', 'controls');
      if (window.electronAPI && window.electronAPI.stopDictation) {
        window.electronAPI.stopDictation();
      } else {
        logMessage('electronAPI.stopDictation not available', 'error');
      }
    });
  }

  // Cancel button click handler
  if (cancelButton) {
    cancelButton.addEventListener('click', () => {
      logMessage('Cancel button clicked', 'controls');
      if (window.electronAPI && window.electronAPI.abortDictation) {
        window.electronAPI.abortDictation();
      } else {
        logMessage('electronAPI.abortDictation not available', 'error');
      }
    });
  }

  // Always on top button click handler
  if (alwaysOnTopButton) {
    alwaysOnTopButton.addEventListener('click', () => {
      logMessage('Always on top button clicked', 'controls');
      if (window.electronAPI && window.electronAPI.toggleAlwaysOnTop) {
        window.electronAPI.toggleAlwaysOnTop();
      } else {
        logMessage('electronAPI.toggleAlwaysOnTop not available', 'error');
      }
    });
  }

  // Keyboard event handlers
  document.addEventListener('keydown', (event) => {
    // Space key for stop (during dictation)
    if (event.code === 'Space') {
      event.preventDefault();
      logMessage('Space pressed - stopping dictation', 'controls');
      if (window.electronAPI && window.electronAPI.stopDictation) {
        window.electronAPI.stopDictation();
      }
    }

    // Escape key for cancel
    if (event.code === 'Escape') {
      event.preventDefault();
      logMessage('Escape pressed - canceling dictation', 'controls');
      if (window.electronAPI && window.electronAPI.abortDictation) {
        window.electronAPI.abortDictation();
      }
    }
  });

  logMessage('Control handlers initialized', 'controls');
}