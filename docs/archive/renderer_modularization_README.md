# Renderer Modularization README

## Purpose
This README documents the modularization of the renderer process in CitrixTranscriber. The goal is to improve code maintainability, readability, and scalability by separating concerns into focused modules.

## File Structure

- `renderer.js` — Entry point; imports and initializes modules.
- `renderer_ui.js` — DOM element references and UI variables.
- `renderer_state.js` — UI state management and status indicator logic.
- `renderer_waveform.js` — Waveform/canvas drawing logic.
- `renderer_ipc.js` — IPC handlers and backend communication.
- `renderer_utils.js` — Logging and utility functions.

## How to Use
- Only `renderer.js` should be loaded as a script in your HTML (with `type="module"`).
- All renderer logic now lives in the new modules; do not add business logic to `renderer.js`.
- When adding features, update the relevant module or create a new one if needed.

## Example
```javascript
// renderer.js
import { drawWaveform } from './renderer_waveform.js';
import { registerIPCHandlers } from './renderer_ipc.js';
import { logMessage } from './renderer_utils.js';

registerIPCHandlers();
drawWaveform();
logMessage('Renderer process started.');
```

## Troubleshooting
- If you see import errors, ensure your environment supports ES6 modules and all paths are correct.
- If UI elements are not updating, check that the relevant references are exported from `renderer_ui.js` and imported where needed.
- If IPC handlers are not firing, ensure `registerIPCHandlers()` is called from `renderer.js`.

## Further Improvements
- Consider modularizing large modules further as features grow.
- Add tests for each module to ensure robustness.

---

*Last updated: 2025-05-17*
