// renderer_waveform.js
// Handles waveform drawing and canvas manipulation

import { amplitudes, canvas, canvasCtx } from './renderer_ui.js';
import { currentAudioState } from './renderer_state.js';

let isAnimationRunning = false;

export function clearCanvas() {
  canvasCtx.clearRect(0, 0, canvas.width, canvas.height);
}

export function drawFlatLine() {
  canvasCtx.fillStyle = '#444';
  canvasCtx.fillRect(0, canvas.height / 2 - 1, canvas.width, 2);
}

export function drawWaveformBars() {
  const width = canvas.width;
  const height = canvas.height;
  const barWidth = width / amplitudes.length;
  const maxBarHeight = height * 0.95; // Use more of the canvas height
  canvasCtx.fillStyle = '#6a6a6a';
  for (let i = 0; i < amplitudes.length; i++) {
    const amplitude = amplitudes[i];
    // Much more aggressive scaling: divide by 30 instead of 100, with minimum visibility
    const scaledAmplitude = Math.max(amplitude / 30, amplitude > 0 ? 0.1 : 0);
    const barHeight = Math.max(2, scaledAmplitude * maxBarHeight);
    const x = i * barWidth;
    const y = (height - barHeight) / 2;
    try {
      canvasCtx.fillRect(x, y, barWidth - 1, barHeight);
    } catch (e) {
      // Ignore drawing errors
    }
  }
}

function animateWaveform() {
  clearCanvas();
  if (currentAudioState === 'inactive') {
    drawFlatLine();
  } else {
    drawWaveformBars();
  }

  // Continue animation if still running
  if (isAnimationRunning) {
    requestAnimationFrame(animateWaveform);
  }
}

export function startWaveformAnimation() {
  if (!isAnimationRunning) {
    isAnimationRunning = true;
    animateWaveform();
  }
}

export function stopWaveformAnimation() {
  isAnimationRunning = false;
}

// Main function - starts the animation immediately
export function drawWaveform() {
  startWaveformAnimation();
}
