// renderer_ipc.js
// Handles IPC communication with Electron main and backend

import { logMessage } from './renderer_utils.js';
import { updateStatusIndicator, handleStatusMessage } from './renderer_state.js';
import { amplitudes } from './renderer_ui.js';
import { handleUiUpdate } from './renderer_expansion_ui.js';

export function registerIPCHandlers() {
  let isFirstThinkingMessageForStream = true;
  // New UI update handler for expansion areas
  if (window.electronAPI && window.electronAPI.on) {
    // Ensure to remove previous listener if any, to prevent multiple registrations during hot-reloads
    window.electronAPI.removeListener('ui-update');
    window.electronAPI.on('ui-update', (data) => {
      logMessage(`UI Update received: ${JSON.stringify(data)}`, 'ipc');
      if (data && typeof data.type !== 'undefined') {
        if (data.type === 'dictation_status_update') {
          logMessage(`Handling dictation_status_update: isDictating=${data.isDictating}, activationStatus=${data.activationStatus}`, 'ipc');

          // Clear previous content when starting a new dictation session
          if (data.isDictating === true) {
            logMessage('New dictation session starting via status update, clearing previous content.', 'ipc');
            handleUiUpdate({ type: 'clear_all_content' });
            isFirstThinkingMessageForStream = true; // Reset for the next proofing session
          }

          // Pass the data directly since field names now match expected format
          updateStatusIndicator(data);
        } else {
          // For other types like 'show_thinking', 'append_response_chunk', 'hide_expansion_areas'
          handleUiUpdate(data);
        }
      } else {
        logMessage(`Received ui-update with invalid or missing data.type: ${JSON.stringify(data)}`, 'warn');
      }
    });
  } else {
    logMessage('window.electronAPI.on not available for ui-update.', 'error');
  }

  // Python message handler
  if (window.electronAPI && window.electronAPI.handleFromPython) {
    window.electronAPI.handleFromPython((message) => {
      if (!message.startsWith('AUDIO_AMP:')) {
        console.log('[IPC_FROM_PYTHON_RAW]', message); // Log non-AUDIO_AMP messages
        logMessage(message, 'py'); // Only log non-AUDIO_AMP to UI log as well
      }
      if (message.startsWith('STATUS:')) {
        const fullStatusMessage = message.substring(7); // Remove "STATUS:" prefix. e.g., "black:PROOF_STREAM:chunk:Hello" or "green:Listening..."

        const firstColorColonIndex = fullStatusMessage.indexOf(':');
        if (firstColorColonIndex === -1) {
          // Fallback for status messages without a color prefix (should not happen with current Python backend)
          logMessage(`General Status (no color prefix): ${fullStatusMessage}`, 'ipc');
          // If it might be a PROOF_STREAM message without color, handle it here or ignore
          if (fullStatusMessage.startsWith('PROOF_STREAM:')) {
            // Basic handling if PROOF_STREAM appears without color, adjust as needed
            const proofStreamData = fullStatusMessage.substring(13);
            const streamType = proofStreamData.split(':')[0];
            logMessage(`Attempting to handle PROOF_STREAM without color: ${streamType}`, 'warn');
          } // else it's a general status message without color
          return;
        }

        // const color = fullStatusMessage.substring(0, firstColorColonIndex); // Color is available if needed
        const messageAfterColor = fullStatusMessage.substring(firstColorColonIndex + 1); // e.g., "PROOF_STREAM:chunk:Hello" or "Listening..."

        if (messageAfterColor.startsWith('PROOF_STREAM:')) {
          const proofStreamData = messageAfterColor.substring(13); // Remove "PROOF_STREAM:"
          let streamType, streamPayload;

          const payloadColonIndex = proofStreamData.indexOf(':');
          if (payloadColonIndex !== -1) {
            streamType = proofStreamData.substring(0, payloadColonIndex);
            streamPayload = proofStreamData.substring(payloadColonIndex + 1);
          } else {
            streamType = proofStreamData; // For "end"
            streamPayload = '';
          }

          logMessage(`Proof Stream: Type='${streamType}', Payload='${streamPayload.substring(0, 100)}...'`, 'ipc');

          if (streamType === 'thinking') {
            // Unescape newlines from IPC transmission
            const unescapedThinking = streamPayload.replace(/\\n/g, '\n').replace(/\\r/g, '\r');

            if (isFirstThinkingMessageForStream) {
              handleUiUpdate({ type: 'initialize_thinking_area', textContent: unescapedThinking });
              isFirstThinkingMessageForStream = false;
            } else {
              handleUiUpdate({ type: 'append_thinking_content', textContent: unescapedThinking });
            }
          } else if (streamType === 'chunk') {
            // Unescape newlines from IPC transmission
            const unescapedChunk = streamPayload.replace(/\\n/g, '\n').replace(/\\r/g, '\r');

            // Ensure response area is shown when first chunk arrives
            const responseArea = document.getElementById('response-area');
            if (responseArea && responseArea.style.display !== 'block') {
              handleUiUpdate({ type: 'show_response_stream_start' });
            }

            handleUiUpdate({ type: 'append_response_chunk', chunk: unescapedChunk });
          } else if (streamType === 'end') {
            logMessage('Proof Stream: End of stream received from backend. Response complete.', 'ipc');
            isFirstThinkingMessageForStream = true; // Reset for the next proofing session
            // Expansion areas remain visible until new dictation starts.
          } else {
            logMessage(`Unknown Proof Stream type: '${streamType}' from data: '${proofStreamData}'`, 'warn');
          }
        } else {
          // Original behavior for non-PROOF_STREAM status messages (e.g., "Listening...")
          logMessage(`General Status: ${fullStatusMessage}`, 'ipc'); // Log the full message after "STATUS:"

          // Extract color and message for conflict detection
          const color = fullStatusMessage.substring(0, firstColorColonIndex);
          const statusText = messageAfterColor;

          // Check for microphone conflicts and show prominent notifications
          handleStatusMessage(statusText, color);
        }
      } else if (message.startsWith('TRANSCRIPTION:')) {
        const parts = message.split(':', 3);
        const type = parts[1];
        const text = parts[2];
        logMessage(`Transcription (${type}): ${text}`);

        // Display proofed transcription in the main window response area (only for actual proofing sessions)
        if (type === 'PROOFED' && text) {
          console.log('[TRANSCRIPTION_DEBUG] PROOFED message received:', JSON.stringify(text));

          // CRITICAL FIX: Check if response area already has streaming content
          const responseArea = document.getElementById('response-area');
          const hasStreamingContent = responseArea && responseArea.textContent && responseArea.textContent.length > 0;

          if (hasStreamingContent) {
            console.log('[TRANSCRIPTION_DEBUG] Response area has streaming content, NOT overriding with PROOFED');
            // Don't override streaming content with TRANSCRIPTION:PROOFED
            return;
          }

          console.log('[TRANSCRIPTION_DEBUG] Setting PROOFED content in response area');

          // Show the response area and set the proofed text with preserved formatting
          handleUiUpdate({ type: 'show_response_stream_start' });

          // Convert newlines to HTML for proper display while preserving dash formatting
          const formattedText = text.replace(/\n/g, '<br>');

          // Set the innerHTML directly to show the formatted text
          if (responseArea) {
            responseArea.innerHTML = formattedText;
            responseArea.style.display = 'block';
            console.log('[TRANSCRIPTION_DEBUG] PROOFED content set, length:', formattedText.length);
          }

          // Update window height to accommodate the content
          handleUiUpdate({ type: 'show_response_stream_start' });
        }
      } else if (message.startsWith('FINAL_TRANSCRIPT:')) {
        // Handle regular dictation final transcripts
        const transcriptText = message.substring(17); // Remove "FINAL_TRANSCRIPT:" prefix
        logMessage(`Final Transcript: ${transcriptText}`);

        console.log('[FINAL_TRANSCRIPT_DEBUG] Final transcript received:', JSON.stringify(transcriptText));

        // CRITICAL FIX: Check if response area already has streaming content
        const responseArea = document.getElementById('response-area');
        const hasStreamingContent = responseArea && responseArea.textContent && responseArea.textContent.length > 0;

        if (hasStreamingContent) {
          console.log('[FINAL_TRANSCRIPT_DEBUG] Response area has streaming content, NOT overriding with final transcript');
          // Don't override streaming content with FINAL_TRANSCRIPT
          return;
        }

        console.log('[FINAL_TRANSCRIPT_DEBUG] Setting final transcript in response area');

        // Display the final transcript in the response area
        handleUiUpdate({ type: 'show_response_stream_start' });

        if (responseArea) {
          responseArea.textContent = transcriptText;
          responseArea.style.display = 'block';
          console.log('[FINAL_TRANSCRIPT_DEBUG] Final transcript set, length:', transcriptText.length);
        }

        // Update window height to accommodate the content
        handleUiUpdate({ type: 'show_response_stream_start' });
      } else if (message.startsWith('STATE:')) {
        try {
          const stateData = JSON.parse(message.substring(6));
          updateStatusIndicator(stateData);
          // If new dictation is starting, hide any existing proofing expansion areas.
          // But DON'T clear if we just completed a transcription/proofing and are going back to activation state
          if (stateData.isDictating === true) {
            logMessage('New dictation started, clearing all previous content and hiding expansion areas.', 'ipc');
            handleUiUpdate({ type: 'clear_all_content' });
            isFirstThinkingMessageForStream = true; // Reset for the next proofing session
          }
          // Don't automatically clear when going from processing to activation - let content remain visible
        } catch (e) {
          logMessage(`Error parsing state JSON: ${e}`, 'error');
        }
      } else if (message.startsWith('AUDIO_AMP:')) {
        try {
          const amplitudeValue = parseInt(message.split(':')[1], 10);
          if (!isNaN(amplitudeValue)) {
            amplitudes.push(amplitudeValue);
            if (amplitudes.length > 100) {
              amplitudes.shift();
            }
          }
        } catch(e) {
          logMessage(`Error parsing amplitude: ${e}`, 'error');
        }
      } else if (message.startsWith('HOTKEYS:')) {
        logMessage(`Received Hotkeys: ${message.substring(8)}`);
      } else if (message === 'BACKEND_READY') {
        logMessage('Python backend is ready.');
      } else if (message === 'SHUTDOWN_SIGNAL') {
        logMessage('Python backend is shutting down.');
        updateStatusIndicator({ audioState: 'inactive', programActive: false });
      }
    });
  }

  // Python stderr handler
  if (window.electronAPI && window.electronAPI.handlePythonStderr) {
    window.electronAPI.handlePythonStderr((errorMessage) => {
      logMessage(errorMessage, 'error');
      console.log('Python Stderr received in renderer:', errorMessage);
      if (errorMessage.toLowerCase().includes('error')) {
        const statusDot = document.getElementById('status-dot');
        if (statusDot) {
          statusDot.style.backgroundColor = '#ff3b30';
          statusDot.style.boxShadow = '0 0 5px #ff3b30';
        }
        // Stop drawing waveform on error
        // (currentAudioState is managed in state module)
      }
    });
  }

  // Clean up IPC listeners on window unload
  window.addEventListener('beforeunload', () => {
    if (window.electronAPI && window.electronAPI.removeListener) {
      window.electronAPI.removeListener('from-python');
      window.electronAPI.removeListener('python-stderr');
    }
    logMessage('Renderer process cleaning up listeners.');
  });
}
