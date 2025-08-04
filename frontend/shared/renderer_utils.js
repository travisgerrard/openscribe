// renderer_utils.js
// Utility functions and logging

import { logContent } from './renderer_ui.js';

export function logMessage(message, type = 'info') {
  // Only log if the log area exists and is visible (optional)
  if (logContent && logContent.parentElement.style.display !== 'none') {
    const timestamp = new Date().toLocaleTimeString();
    const prefix = type === 'error' ? '[PyERR]' : type === 'py' ? '[PyOUT]' : '[App]';
    logContent.textContent += `${timestamp} ${prefix}: ${message}\n`;
    logContent.scrollTop = logContent.scrollHeight; // Auto-scroll
  }
  // Also log to console for easier debugging
  console.log(`[${type.toUpperCase()}] ${message}`);
}
