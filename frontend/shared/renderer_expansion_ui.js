const BASE_WINDOW_HEIGHT = 120; // Assuming current compact window height is around this. Adjust if necessary.
const ELEMENT_PADDING_MARGIN = 20; // Combined vertical padding/margin for each new section

let mainThinkingAreaDiv = null; // The main container div for thinking area (e.g., <div id="thinking-area">)
let thinkingHeader = null;
let thinkingContentArea = null; // Where the actual thinking text goes (e.g., <div id="thinking-content">)
let responseArea = null;

function getElementHeight(element) {
  if (!element || window.getComputedStyle(element).display === 'none') {
    return 0;
  }
  // Use scrollHeight to get the full content height, even if overflowing
  return element.scrollHeight;
}

function updateMainWindowHeight() {
  let newHeight = BASE_WINDOW_HEIGHT;
  // Use thinkingContentArea for height calculation of the text part
  const thinkingContentHeight = (mainThinkingAreaDiv && mainThinkingAreaDiv.classList.contains('collapsed')) ? 0 : getElementHeight(thinkingContentArea);
  const thinkingHeaderHeight = getElementHeight(thinkingHeader);
  const responseHeight = getElementHeight(responseArea);

  console.log(`[UI_RESIZE] Initial newHeight: ${newHeight}`);
  console.log(`[UI_RESIZE] thinkingHeader display: ${thinkingHeader ? thinkingHeader.style.display : 'null'}, thinkingHeaderHeight: ${thinkingHeaderHeight}`);
  console.log(`[UI_RESIZE] thinkingContentArea display: ${thinkingContentArea ? thinkingContentArea.style.display : 'null'}, thinkingContentHeight: ${thinkingContentHeight}`);
  console.log(`[UI_RESIZE] responseArea display: ${responseArea ? responseArea.style.display : 'null'}, responseHeight: ${responseHeight}`);

  if (mainThinkingAreaDiv && mainThinkingAreaDiv.style.display === 'block') {
    newHeight += thinkingHeaderHeight; // Always add header height if thinking area is visible
    if (!mainThinkingAreaDiv.classList.contains('collapsed')) {
      newHeight += thinkingContentHeight; // Add content height only if not collapsed
    }
    newHeight += ELEMENT_PADDING_MARGIN; // Add padding for the thinking area block
    console.log(`[UI_RESIZE] After thinking area, newHeight: ${newHeight}`);
  }

  if (responseHeight > 0) {
    newHeight += responseHeight + ELEMENT_PADDING_MARGIN;
    console.log(`[UI_RESIZE] After responseHeight, newHeight: ${newHeight}`);
  }

  // Add some buffer, especially if scrollbars might appear and disappear
  if (thinkingContentHeight > 0 || responseHeight > 0) {
    newHeight += 10; // Buffer
    console.log(`[UI_RESIZE] After buffer, newHeight: ${newHeight}`);
  }

  const finalHeightToSet = Math.round(newHeight);
  console.log(`[UI_RESIZE] Final height to set: ${finalHeightToSet}`);

  if (window.electronAPI && typeof window.electronAPI.resizeWindow === 'function') {
    window.electronAPI.resizeWindow({ height: finalHeightToSet });
  } else {
    console.error('[UI_RESIZE] window.electronAPI.resizeWindow not available.');
  }
}

export function initializeExpansionUi() {
  mainThinkingAreaDiv = document.getElementById('thinking-area');
  thinkingHeader = document.getElementById('thinking-header');
  thinkingContentArea = document.getElementById('thinking-content');
  responseArea = document.getElementById('response-area');

  if (!mainThinkingAreaDiv || !thinkingHeader || !thinkingContentArea || !responseArea) {
    console.error('Could not find all required thinking/response areas/header in the DOM.');
    mainThinkingAreaDiv = null; // Nullify if any part is missing to prevent errors
    thinkingContentArea = null;
    responseArea = null;
    return;
  }

  thinkingHeader.addEventListener('click', () => {
    if (mainThinkingAreaDiv) {
      mainThinkingAreaDiv.classList.toggle('collapsed');
      updateMainWindowHeight(); // Update height after toggling collapse
    }
  });

  console.log('Expansion UI initialized with collapsible thinking area.');
}

// Function to format thinking content with automatic line breaks
function formatThinkingContent(text) {
  if (!text) return text;

  // First, handle any existing \n characters
  let formatted = text.replace(/\\n/g, '\n');

  // Add line breaks after sentences (. ! ?) followed by space and capital letter
  formatted = formatted.replace(/([.!?])\s+([A-Z])/g, '$1\n$2');

  // Add line breaks after certain phrases that typically end thoughts
  formatted = formatted.replace(/\.\s*(Next,|Also,|Additionally,|Furthermore,|However,|Therefore,|Thus,|Finally,|In conclusion,|Looking at|Checking|Now,)/g, '.\n$1');

  // Add line breaks before common thinking transitions
  formatted = formatted.replace(/\s+(Next,|Also,|Additionally,|Furthermore,|However,|Therefore,|Thus,|Finally,|In conclusion,|Looking at|Checking|Now,)/g, '\n$1');

  // Clean up multiple consecutive newlines
  formatted = formatted.replace(/\n\s*\n\s*\n/g, '\n\n');

  return formatted;
}

export function handleUiUpdate(data) {
  // Check if mainThinkingAreaDiv is available (implies all parts were found)
  if (!mainThinkingAreaDiv || !thinkingContentArea || !responseArea) return;

  switch (data.type) {
  case 'initialize_thinking_area': {
    mainThinkingAreaDiv.style.display = 'block'; // Show the main thinking container
    if (mainThinkingAreaDiv.classList.contains('collapsed')) {
      mainThinkingAreaDiv.classList.remove('collapsed'); // Default to expanded for new thoughts
    }
    // Process newlines in initial thinking content
    const initialText = data.textContent || 'Processing...';
    thinkingContentArea.textContent = formatThinkingContent(initialText);
    responseArea.innerHTML = '';
    responseArea.style.display = 'none';
    break;
  }
  case 'append_thinking_content': {
    if (mainThinkingAreaDiv.style.display !== 'block') {
      mainThinkingAreaDiv.style.display = 'block';
    }
    if (mainThinkingAreaDiv.classList.contains('collapsed')) {
      // Optionally, one could decide to auto-expand if content is appended while collapsed.
      // For now, it appends to hidden content.
    }
    // Process newlines in appended thinking content
    const appendText = formatThinkingContent(data.textContent);
    thinkingContentArea.textContent += appendText; // Append processed thinking text to content area

    // Auto-scroll thinking area to show new content
    if (!mainThinkingAreaDiv.classList.contains('collapsed')) {
      setTimeout(() => {
        thinkingContentArea.scrollTop = thinkingContentArea.scrollHeight;
      }, 10);
    }

    if (responseArea.style.display !== 'none') {
      responseArea.style.display = 'none';
      responseArea.innerHTML = '';
    }
    break;
  }
  case 'show_response_stream_start':
    // mainThinkingAreaDiv state (collapsed/expanded) is preserved.
    responseArea.innerHTML = '';
    responseArea.textContent = ''; // Clear both innerHTML and textContent
    responseArea.style.display = 'block';
    console.log('[RESPONSE_DEBUG] Response area cleared and shown');
    console.log('[RESPONSE_DEBUG] Response area display after setting:', responseArea.style.display);
    console.log('[RESPONSE_DEBUG] Response area visibility:', window.getComputedStyle(responseArea).visibility);
    console.log('[RESPONSE_DEBUG] Response area height:', responseArea.offsetHeight);
    break;
  case 'append_response_chunk':
    // Ensure response area is visible and append the chunk
    if (responseArea.style.display !== 'block') {
      responseArea.style.display = 'block';
    }

    // Simple concatenation - CSS handles newlines with white-space: pre-wrap
    responseArea.textContent += data.chunk;
    break;
  case 'clear_response':
    responseArea.innerHTML = '';
    responseArea.textContent = '';
    console.log('[RESPONSE_DEBUG] Response area cleared');
    break;
  case 'hide_expansion_areas':
    mainThinkingAreaDiv.style.display = 'none'; // Hide the main thinking container
    responseArea.style.display = 'none';
    thinkingContentArea.innerHTML = '';
    responseArea.innerHTML = '';
    responseArea.textContent = '';
    break;
  case 'clear_all_content':
    // More thorough cleanup for new dictation sessions
    if (mainThinkingAreaDiv) {
      mainThinkingAreaDiv.style.display = 'none';
      mainThinkingAreaDiv.classList.remove('collapsed'); // Reset to expanded state for next session
    }
    if (responseArea) {
      responseArea.style.display = 'none';
      responseArea.innerHTML = '';
      responseArea.textContent = '';
    }
    if (thinkingContentArea) {
      thinkingContentArea.innerHTML = '';
      thinkingContentArea.textContent = '';
    }
    console.log('[RESPONSE_DEBUG] All content cleared');
    break;
  default:
    console.warn('Unknown UI update type:', data.type);
    break;
  }
  updateMainWindowHeight();
}
