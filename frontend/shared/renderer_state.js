// renderer_state.js
// Handles UI state management and status indicator updates

import { statusDot, stopButton, cancelButton, modeIndicator, processingIndicator, amplitudes } from './renderer_ui.js';
import { conflictNotificationManager } from './renderer_conflict_ui.js';

// Exported variable for the audio visualizer and other potential consumers
export let currentAudioState = 'inactive'; // This will be updated by updateStatusIndicator
export let isAlwaysOnTop = false; // This seems unrelated to current changes, keep it.

// Module-level state, managed by updateStatusIndicator
let internalState = {
  programActive: false, // Start as false until first STATE message confirms microphone availability
  audioState: 'inactive',
  isDictating: false,
  currentMode: null,
  microphoneError: null, // Store microphone error information
  lastConflictCheck: 0 // Track when we last checked for conflicts
};

export function updateStatusIndicator(newState) {
  // Update internalState with new values, providing defaults if properties are missing
  internalState.programActive = typeof newState.programActive === 'boolean' ? newState.programActive : internalState.programActive;
  internalState.audioState = newState.audioState || internalState.audioState; // The actual state from Python (activation, dictation, processing)
  internalState.isDictating = typeof newState.isDictating === 'boolean' ? newState.isDictating : internalState.isDictating;
  internalState.currentMode = newState.currentMode !== undefined ? newState.currentMode : internalState.currentMode;
  internalState.microphoneError = newState.microphoneError || null;

  console.log('[RendererState] updateStatusIndicator called with:', newState);
  console.log('[RendererState] Internal state after update:', internalState);

  if (!statusDot) return; // Guard if UI element isn't ready

  const previousCurrentAudioStateForTransition = currentAudioState; // Store previous *exported* currentAudioState for transition logic

  // If program is not active, force UI to inactive state and handle microphone errors
  if (!internalState.programActive) {
    if (statusDot) {
      // Use red color if there's a microphone error, otherwise grey
      if (internalState.microphoneError) {
        statusDot.style.backgroundColor = '#ff3b30'; // Red for error
        statusDot.style.boxShadow = '0 0 5px #ff3b30';

        // Add error tooltip if supported
        statusDot.title = `Microphone Error: ${internalState.microphoneError}`;

        // Pulse effect for error state
        statusDot.style.animation = 'pulse-error 2s infinite';
      } else {
        statusDot.style.backgroundColor = '#8e8e93'; // Grey
        statusDot.style.boxShadow = 'none';
        statusDot.title = '';
        statusDot.style.animation = '';
      }
    }

    if (stopButton) stopButton.disabled = true;
    if (cancelButton) cancelButton.disabled = true;
    currentAudioState = 'inactive'; // For visualizer
    if (modeIndicator) modeIndicator.style.display = 'none';
    if (processingIndicator) processingIndicator.style.display = 'none';
    if (amplitudes) amplitudes.fill(0); // Clear waveform

    if (window.electronAPI && window.electronAPI.showProofingWindow) {
      window.electronAPI.showProofingWindow(false);
    }

    // Tray state updates are handled by backend STATUS messages, no need to duplicate here
    // const trayState = internalState.microphoneError ? 'error' : 'inactive';
    // console.log('[RendererState] Sending tray state:', trayState, '(programActive:', internalState.programActive, ')');
    // if (window.electronAPI && window.electronAPI.sendTrayState) {
    //   window.electronAPI.sendTrayState(trayState);
    // }
    return;
  }

  // Clear any error state when program becomes active
  if (statusDot) {
    statusDot.title = '';
    statusDot.style.animation = '';
  }

  // Determine effective audio state for UI based on isDictating and actual audioState
  // This effectiveAudioState is what the user sees (dot color, tray icon)
  let effectiveVisibleAudioState = internalState.audioState;
  if (internalState.isDictating) {
    effectiveVisibleAudioState = 'dictation';
  }

  // Update the exported currentAudioState that the visualizer loop uses
  // The visualizer should only animate when effectiveVisibleAudioState is 'dictation'
  currentAudioState = effectiveVisibleAudioState === 'dictation' ? 'dictation' : 'inactive';
  // More precise: visualizer should be active if isDictating is true,
  // and the raw audioState is 'dictation'.
  // The effectiveVisibleAudioState already captures this.
  // So, if effectiveVisibleAudioState is 'dictation', currentAudioState (for animation) is 'dictation'.
  // Otherwise, for 'activation' or 'processing', animation should be off.
  if (effectiveVisibleAudioState !== 'dictation') {
    currentAudioState = 'inactive'; // Ensure animation is off unless truly dictating
  }


  // Manage listening animation buffer: clear amplitudes if not in 'dictation' state
  if (currentAudioState !== 'dictation') { // Check the animation-driving state
    if (amplitudes) amplitudes.fill(0);
  }
  // Additional check: if transitioning out of dictation, ensure waveform is cleared
  if (previousCurrentAudioStateForTransition === 'dictation' && currentAudioState !== 'dictation') {
    if (amplitudes) amplitudes.fill(0);
  }

  // Reset indicators before setting them based on the new state
  if (modeIndicator) modeIndicator.style.display = 'none';
  if (processingIndicator) processingIndicator.style.display = 'none';

  switch (effectiveVisibleAudioState) {
  case 'activation':
  case 'preparing': // Treat preparing state like activation (blue indicator)
    if (statusDot) {
      statusDot.style.backgroundColor = '#007aff'; // Blue
      statusDot.style.boxShadow = '0 0 5px #007aff';
    }
    if (stopButton) stopButton.disabled = true;
    if (cancelButton) cancelButton.disabled = true;
    break;
  case 'dictation':
    if (statusDot) {
      statusDot.style.backgroundColor = '#34c759'; // Green
      statusDot.style.boxShadow = '0 0 5px #34c759';
    }
    if (stopButton) stopButton.disabled = false;
    if (cancelButton) cancelButton.disabled = false;

    if (modeIndicator && internalState.currentMode) {
      if (internalState.currentMode === 'dictate') {
        modeIndicator.textContent = 'Note';
        modeIndicator.style.display = 'inline-block';
      } else if (internalState.currentMode === 'proofread') {
        modeIndicator.textContent = 'Proof';
        modeIndicator.style.display = 'inline-block';
        if (window.electronAPI && window.electronAPI.showProofingWindow) {
          window.electronAPI.showProofingWindow(true);
        }
      } else if (internalState.currentMode === 'letter') {
        modeIndicator.textContent = 'Letter';
        modeIndicator.style.display = 'inline-block';
      }
    }
    break;
  case 'processing':
    if (statusDot) {
      statusDot.style.backgroundColor = '#ff9500'; // Orange
      statusDot.style.boxShadow = '0 0 5px #ff9500';
    }
    if (stopButton) stopButton.disabled = true;
    if (cancelButton) cancelButton.disabled = true;
    if (processingIndicator) processingIndicator.style.display = 'inline-block';
    if (internalState.currentMode === 'proofread' && window.electronAPI && window.electronAPI.showProofingWindow) {
      window.electronAPI.showProofingWindow(true);
    }
    break;
  case 'inactive': // This case would be hit if programActive is true, but audioState is 'inactive'
  default:
    if (statusDot) {
      statusDot.style.backgroundColor = '#8e8e93'; // Grey
      statusDot.style.boxShadow = 'none';
    }
    if (stopButton) stopButton.disabled = true;
    if (cancelButton) cancelButton.disabled = true;
    currentAudioState = 'inactive'; // Ensure animation state reflects inactivity
    if (modeIndicator) modeIndicator.style.display = 'none';
    if (processingIndicator) processingIndicator.style.display = 'none';
    if (window.electronAPI && window.electronAPI.showProofingWindow) {
      window.electronAPI.showProofingWindow(false);
    }
    break;
  }

  // Tray state updates are handled by backend STATUS messages, no need to duplicate here
  // console.log('[RendererState] Sending tray state:', effectiveVisibleAudioState, '(programActive:', internalState.programActive, ')');
  // if (window.electronAPI && window.electronAPI.sendTrayState) {
  //   window.electronAPI.sendTrayState(effectiveVisibleAudioState);
  // }
}

// Initialize the UI to the correct initial state (grey) immediately when module loads
export function initializeStatusIndicator() {
  console.log('[RendererState] Initializing status indicator to inactive state');
  console.log('[RendererState] statusDot element:', statusDot);

  // Directly set the status dot to grey without going through updateStatusIndicator
  if (statusDot) {
    statusDot.style.backgroundColor = '#8e8e93'; // Grey
    statusDot.style.boxShadow = 'none';
    console.log('[RendererState] Successfully set status dot to grey');
  } else {
    console.warn('[RendererState] statusDot element not found during initialization');
  }

  // Also call updateStatusIndicator to ensure all state is consistent
  updateStatusIndicator({
    programActive: false,
    audioState: 'inactive',
    isDictating: false,
    currentMode: null,
    microphoneError: null
  });
}

// Get current microphone error (if any)
export function getMicrophoneError() {
  return internalState.microphoneError;
}

// Check if there's a microphone error
export function hasMicrophoneError() {
  return !!internalState.microphoneError;
}

// Handle status messages and detect microphone conflicts
export function handleStatusMessage(statusText, color) {
  // Store microphone error information for visual indicators
  if (color === 'red' && (statusText.toLowerCase().includes('microphone') || statusText.toLowerCase().includes('audio'))) {
    internalState.microphoneError = statusText;
  } else if (color === 'green' || color === 'blue') {
    // Clear error state on successful operations
    internalState.microphoneError = null;
  }

  // Detect ACTUAL microphone conflict messages - be more precise
  // Only trigger on definitive conflict detection messages, not just mentions of browsers
  const definitiveConflictPhrases = [
    'microphone conflict detected',
    'detected active conflict',
    'conflicting application detected',
    'microphone access blocked',
    'another application is using the microphone',
    'audio input conflict'
  ];

  // Check if this is a definitive conflict message
  const isDefinitiveConflict = definitiveConflictPhrases.some(phrase =>
    statusText.toLowerCase().includes(phrase.toLowerCase())
  );

  // Additional check for specific browser conflict patterns (more precise)
  const isBrowserConflictMessage = statusText.toLowerCase().includes('microphone conflict detected') &&
                                   (statusText.toLowerCase().includes('safari') ||
                                    statusText.toLowerCase().includes('chrome') ||
                                    statusText.toLowerCase().includes('browser'));

  // Check if this is a suggestion message (these should not trigger the banner)
  const isSuggestionMessage = statusText.includes('💡') ||
                             statusText.toLowerCase().includes('note:') ||
                             statusText.toLowerCase().includes('tip:') ||
                             (statusText.toLowerCase().includes('close') && statusText.toLowerCase().includes('tab')) ||
                             (statusText.toLowerCase().includes('disable') && statusText.toLowerCase().includes('access'));

  // Only show conflict notification for definitive conflicts, not suggestions or diagnostic info
  if ((isDefinitiveConflict || isBrowserConflictMessage) && !isSuggestionMessage) {
    const currentTime = Date.now();
    // Only show notification if enough time has passed since last one (avoid spam)
    if (currentTime - internalState.lastConflictCheck > 5000) { // 5 second cooldown
      internalState.lastConflictCheck = currentTime;

      // Extract useful conflict information
      let conflictDetails = statusText;
      if (statusText.toLowerCase().includes('safari') || statusText.toLowerCase().includes('chrome')) {
        conflictDetails = 'Safari or Chrome is actively using the microphone for dictation';
      } else if (statusText.toLowerCase().includes('browser')) {
        conflictDetails = 'Web browser is actively using the microphone for dictation';
      } else if (statusText.toLowerCase().includes('another application')) {
        conflictDetails = 'Another application is using the microphone';
      }

      // Show the prominent conflict banner
      conflictNotificationManager.showConflictBanner(conflictDetails);
    }
  }

  // Log suggestion messages for debugging but don't show banner
  if (isSuggestionMessage) {
    console.log('Conflict suggestion received:', statusText);
  }
}

// Hide conflict notification (for external use)
export function hideConflictNotification() {
  conflictNotificationManager.hideConflictBanner();
}

// Check if conflict notification is visible
export function isConflictNotificationVisible() {
  return conflictNotificationManager.isConflictVisible();
}