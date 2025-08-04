# electron_main.js Modular Breakdown

This document describes each new file created from splitting the original `electron_main.js` into logical modules for clarity and maintainability.

---

## electron_app_init.js
**Purpose:** Handles app initialization, Electron imports, persistent settings, and migration logic.

---

## electron_tray.js
**Purpose:** Handles tray icon management, including icon state (color) and tray menu actions.

---

## electron_windows.js
**Purpose:** Manages the main floating window and the proofing window, including creation, positioning, pinning, and visibility helpers.

---

## electron_python.js
**Purpose:** Handles starting and managing the Python backend process, including message and event handlers for communication with the Python side.

---

## electron_ipc.js
**Purpose:** Handles all IPC communication between the renderer process and the Electron main process (e.g., dictation/proofing commands, always-on-top toggling, tray state changes, settings loading/saving, etc).

---

## electron_lifecycle.js
**Purpose:** Handles Electron app lifecycle events, such as startup (`whenReady`), window-all-closed, and related logic.

---

**Note:** Each file should be imported as needed in a new, minimal `main.js` (or similar) entry point, which simply wires up the modules.
