# Renderer Modularization Breakdown

This document explains the modular structure of the renderer process as of the May 2025 refactor. Each module is responsible for a specific concern, improving maintainability and scalability.

## Module Overview

| File                   | Responsibility                                        |
|------------------------|------------------------------------------------------|
| renderer.js            | Entry point. Imports and initializes all modules.     |
| renderer_ui.js         | DOM element references and UI variables.              |
| renderer_state.js      | UI state management and status indicator updates.     |
| renderer_waveform.js   | Waveform drawing and canvas manipulation.             |
| renderer_ipc.js        | IPC communication and backend event handling.         |
| renderer_utils.js      | Logging and utility functions.                        |

## Module Details

### renderer.js
- Imports all modules.
- Calls initialization functions (registers IPC handlers, starts waveform loop).
- Contains no business or UI logic.

### renderer_ui.js
- Exports references to DOM elements (status dot, buttons, canvas, etc.).
- Exports UI variables (e.g., amplitudes array, canvas context).

### renderer_state.js
- Exports `updateStatusIndicator(state)` for updating UI based on backend state.
- Manages UI state variables (e.g., `currentAudioState`).
- Notifies main process to update tray icon as needed.

### renderer_waveform.js
- Exports waveform drawing functions: `drawWaveform`, `clearCanvas`, etc.
- Handles drawing the waveform and flatline based on audio state.
- Uses amplitudes from `renderer_ui.js` and state from `renderer_state.js`.

### renderer_ipc.js
- Registers IPC event handlers for communication with Electron main and Python backend.
- Handles proof-stream, audio state, transcription, hotkeys, and errors.
- Cleans up listeners on window unload.

### renderer_utils.js
- Exports `logMessage()` for logging to UI and console.
- Can contain other shared helpers.

---

## How to Extend
- Add new UI elements to `renderer_ui.js`.
- Add new backend or IPC logic to `renderer_ipc.js`.
- Update state logic in `renderer_state.js`.
- Add new waveform visualizations in `renderer_waveform.js`.
- Add new utilities to `renderer_utils.js`.

---

## Migration Notes
- All renderer logic previously in `renderer.js` is now split across these modules.
- Only `renderer.js` should be loaded as a script in your HTML; it will import the rest.
- Ensure your build process (if any) supports ES6 modules.
