// proofing.js
// Registers IPC handlers and updates proofing window DOM

console.log('[Proofing] proofing.js script loaded (top-level)');

// Import text processing utilities
import {
  appendChunk,
  normaliseResponse,
  deduplicateHyphenPairs,
  deduplicateWordPairs,
  formatThinkingContent
} from './text_processing_utils.js';

// Add event listener for DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
  // Initialize collapsible thinking section
  const thinkingBox = document.getElementById('proof-thinking');
  if (thinkingBox) {
    thinkingBox.addEventListener('click', function() {
      this.classList.toggle('collapsed');

      // Update toggle text
      const toggleEl = this.querySelector('.thinking-toggle');
      if (toggleEl) {
        toggleEl.textContent = this.classList.contains('collapsed')
          ? 'Click to expand'
          : 'Click to collapse';
      }
    });
  }

  // -----------------------------------------------------------------------
  // Note: Text processing utilities have been moved to text_processing_utils.js
  // and are imported at the top of this file
  // -----------------------------------------------------------------------

  // Function to parse and separate thinking and response content
  // (Note: This function is now imported from text_processing_utils.js)

  // Format thinking content with tidy paragraphs
  // (Note: This function is now imported from text_processing_utils.js)

  // Format response content with bullet points
  // (Note: This function is now imported from text_processing_utils.js)

  // Debug logging for environment
  if (typeof window !== 'undefined') {
    if (window._proofingPreloadLoaded) {
      console.log('[Proofing] Detected _proofingPreloadLoaded = true (preload ran)');
    } else {
      console.warn('[Proofing] _proofingPreloadLoaded NOT set (preload may not have run)');
    }

    if (typeof window.electronAPI !== 'undefined') {
      console.log('[Proofing] window.electronAPI is available:', Object.keys(window.electronAPI));
    } else {
      console.warn('[Proofing] window.electronAPI is NOT available');
    }
  }

  // Global state for streaming
  // eslint-disable-next-line no-unused-vars
  let isNewSession = true;
  // Note: proofedChunks and chunkBuffer are no longer used after refactoring

  // DOM elements
  let proofThinking = null;
  let proofMessage = null;

  /**
     * Initialize the proofing window DOM and set up event listeners
     */
  function initializeProofing() {
    console.log('[Proofing] Initializing proofing window...');

    // Get DOM elements
    proofThinking = document.getElementById('proof-thinking');
    proofMessage = document.getElementById('proof-message');

    if (!proofThinking || !proofMessage) {
      console.error('[Proofing] Could not find required DOM elements');
      return;
    }

    // Signal readiness to backend for proofing stream
    if (window.electronAPI?.send) {
      window.electronAPI.send('proofing-ready');
      console.log('[Proofing] Sent proofing-ready to backend');
    } else {
      console.warn('[Proofing] electronAPI.send not available');
    }
  }

  /**
     * Return plain‑text output (dash‑led lines) for easy EMR copy/paste
     * @param {string} text
     * @returns {string}
     */
  function formatProofedOutput(text) {
    if (!text) return '';

    // Keep it simple: just convert newlines to <br> tags
    // Don't try to create HTML lists - preserve exact dash formatting for clipboard
    return text.replace(/\n/g, '<br>');
  }

  // Initialize when DOM is loaded
  window.addEventListener('DOMContentLoaded', () => {
    console.log('[Proofing] DOMContentLoaded fired in proofing.js');

    // Log environment info
    if (typeof window.electronAPI !== 'undefined') {
      console.log('[Proofing] electronAPI available at DOMContentLoaded:', Object.keys(window.electronAPI));
    } else {
      console.warn('[Proofing] electronAPI NOT available at DOMContentLoaded');
    }

    // Check for required IPC methods
    if (!window.electronAPI && !(window.require && window.require('electron'))) {
      console.warn('[Proofing] window.electronAPI is not available. Proofing streaming will not work.');
      console.log('[Proofing] typeof window.electronAPI:', typeof window.electronAPI);
      console.log('[Proofing] typeof window.require:', typeof window.require);
      return;
    }

    // Initialize the proofing window
    initializeProofing();

    // ---------------------------------------------------------------------------
    // Handler for streamed proofing text via IPC  (refactored 2025‑05‑20)
    // ---------------------------------------------------------------------------
    //  ▸ Parses model output that arrives as raw chunks.
    //  ▸ Keeps state so that text between <think> … </think> streams into the
    //    "thinking" box, while everything after </think> streams into the
    //    response box. No back‑end tagging required.
    // ---------------------------------------------------------------------------

    // Local streaming state
    const streamState = {
      section: 'pre',      // 'pre' | 'thinking' | 'response'
      thinking: '',
      response: '',
      tail: ''             // holds partial tags that span chunks
    };

    // Push current buffers into the DOM
    function flushDOM() {
      // Thinking
      if (proofThinking) {
        const thinkingEl = proofThinking.querySelector('.thinking-text');
        if (thinkingEl) {
          thinkingEl.innerHTML =
                        formatThinkingContent(streamState.thinking.trim());
          // If we just wrote real content, remove any placeholder
          const placeholder = proofThinking.querySelector('.thinking-toggle');
          if (placeholder && streamState.thinking.trim().length) {
            placeholder.style.display = 'none';
          }
        }
        // Collapse the box when empty
        proofThinking.classList.toggle(
          'collapsed',
          streamState.thinking.trim().length === 0
        );
        // Auto‑scroll to the newest line while streaming - only if window is visible/focused
        if (!proofThinking.classList.contains('collapsed') &&
                    !document.hidden &&
                    document.hasFocus()) {
          // Smooth scroll to bottom with a slight delay to allow DOM updates
          setTimeout(() => {
            proofThinking.scrollTop = proofThinking.scrollHeight;
          }, 10);
        }
      }

      // Response
      if (proofMessage) {
        let cleaned = streamState.response;
        cleaned = deduplicateHyphenPairs(cleaned);
        cleaned = deduplicateWordPairs(cleaned);
        cleaned = normaliseResponse(cleaned);
        proofMessage.innerHTML = formatProofedOutput(cleaned);
        // Keep the latest bullets in view - only if window is visible/focused
        if (!document.hidden && document.hasFocus()) {
          setTimeout(() => {
            proofMessage.scrollTop = proofMessage.scrollHeight;
          }, 10);
        }
      }
    }

    // Main chunk handler
    function handleProofStream(_event, data) {
      // Guard
      if (!data || typeof data.chunk === 'undefined') return;

      // --- Session boundary detection -----------------------------------
      // 1) Explicit end marker sent by back‑end – keep content visible
      if (data.section === 'end') {
        // Collapse the thinking box so only the response remains visible
        if (proofThinking) proofThinking.classList.add('collapsed');

        // Reset the state machine to PRE so the next <think> starts cleanly
        // (buffers stay intact so the user can still copy them)
        streamState.section = 'pre';
        streamState.tail    = '';

        // Do *not* wipe the buffers – user may want to copy the final text
        // Simply mark the session finished.
        isNewSession = true;
        return; // nothing else to process
      }

      // 2) Heuristic: brand‑new <think> while we are still in a non‑thinking state
      //    from a previous session. Treat as implicit new session.
      if (
        streamState.section !== 'thinking' &&   // any non‑thinking state
                data.chunk && String(data.chunk).includes('<think>')
      ) {
        console.log('[Proofing] Detected implicit new session via <think> tag');

        // Reset parser state
        streamState.section  = 'pre';
        streamState.tail     = '';
        // Clear internal buffers so the new proof starts clean
        streamState.thinking = '';
        streamState.response = '';

        // Wipe previous DOM content
        if (proofThinking) {
          const thinkingEl = proofThinking.querySelector('.thinking-text');
          if (thinkingEl) thinkingEl.innerHTML = '';
          proofThinking.classList.add('collapsed');
        }
        if (proofMessage) {
          proofMessage.innerHTML = '';
        }
      }
      // -------------------------------------------------------------------

      // Start‑of‑session housekeeping
      if (data.session_start) {
        streamState.section  = 'pre';
        streamState.thinking = '';
        streamState.response = '';
        streamState.tail     = '';
        flushDOM();
        // Clear previous DOM content so each proof starts fresh
        if (proofThinking) {
          const thinkingEl = proofThinking.querySelector('.thinking-text');
          if (thinkingEl) thinkingEl.innerHTML = '';
          proofThinking.classList.add('collapsed');
        }
        if (proofMessage) {
          proofMessage.innerHTML = '';
        }
      }

      // Coalesce with any leftover partial tag
      let chunk = String(data.chunk);
      chunk = streamState.tail + chunk;
      streamState.tail = '';

      // --- Stateful parse loop ---------------------------------------------
      while (chunk.length) {
        if (streamState.section === 'pre') {
          const idx = chunk.indexOf('<think>');
          if (idx === -1) {
            // Haven't seen opening tag yet – keep for next tick
            streamState.tail = chunk;
            chunk = '';
          } else {
            // Drop anything before <think> and enter thinking mode
            chunk = chunk.slice(idx + 7); // 7 = length of '<think>'
            streamState.section = 'thinking';
          }
        } else if (streamState.section === 'thinking') {
          const idx = chunk.indexOf('</think>');
          if (idx === -1) {
            // Whole chunk is thinking text
            streamState.thinking = appendChunk(streamState.thinking, chunk);
            chunk = '';
          } else {
            // Up to closing tag is thinking, the rest is response
            streamState.thinking = appendChunk(streamState.thinking, chunk.slice(0, idx));
            chunk = chunk.slice(idx + 8); // 8 = length of '</think>'
            streamState.section = 'response';
          }
        } else {
          // response mode – everything is response
          streamState.response = appendChunk(streamState.response, chunk);
          chunk = '';
        }
      }
      // ----------------------------------------------------------------------

      flushDOM();

      // End‑of‑message clean‑up (optional protocol flag)
      if (data.message || data.final) {
        streamState.section  = 'pre';
        streamState.tail     = '';
        isNewSession         = true;
      }
    }
    // ---------------------------------------------------------------------------
    // End refactored streaming handler
    // ---------------------------------------------------------------------------

    // Register the IPC handler for proof-stream events
    try {
      if (window.electronAPI?.on) {
        console.log('[Proofing] Registering proof-stream handler via window.electronAPI');
        window.electronAPI.on('proof-stream', (event, data) => {
          try {
            console.log('[Proofing] proof-stream event received (electronAPI):', data);
            handleProofStream(event, data);
          } catch (handlerErr) {
            console.error('[Proofing] Error in proof-stream handler:', handlerErr, data);
          }
        });
      } else if (window.require) {
        // Fallback for non-contextBridge environments
        console.log('[Proofing] Registering proof-stream handler via ipcRenderer fallback');
        const { ipcRenderer } = window.require('electron');
        ipcRenderer.on('proof-stream', (event, data) => {
          try {
            console.log('[Proofing] proof-stream event received (fallback):', data);
            handleProofStream(event, data);
          } catch (handlerErr) {
            console.error('[Proofing] Error in fallback proof-stream handler:', handlerErr, data);
          }
        });
      } else {
        console.error('[Proofing] No IPC method available for communication');
      }
    } catch (err) {
      console.error('[Proofing] Failed to register proof-stream handler:', err);
    }
    // Re‑compute scroll on window resize
    window.addEventListener('resize', () => {
      if (proofMessage) {
        proofMessage.scrollTop = proofMessage.scrollHeight;
      }
    });
  }); // End of DOMContentLoaded event listener
}); // End of outer document DOMContentLoaded listener
