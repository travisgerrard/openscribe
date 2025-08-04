// renderer_ui.js
// DOM element references and UI variables

export const statusDot = document.getElementById('status-dot');
export const stopButton = document.getElementById('stop-button');
export const cancelButton = document.getElementById('cancel-button');
export const modeIndicator = document.getElementById('mode-indicator');
export const processingIndicator = document.getElementById('processing-indicator');
export const alwaysOnTopButton = document.getElementById('always-on-top-button');
export const logContent = document.getElementById('log-content');
export const canvas = document.getElementById('waveform-canvas');
export const canvasCtx = canvas.getContext('2d');
export const amplitudes = new Array(100).fill(0);
