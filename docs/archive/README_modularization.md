# Modularization of electron_main.js

The original `electron_main.js` was split into several logical modules for clarity, maintainability, and scalability. Each new file encapsulates a distinct concern of the Electron app.

## New Files

- **electron_app_init.js**: App initialization, Electron imports, persistent settings, migration logic.
- **electron_tray.js**: Tray icon management and menu actions.
- **electron_windows.js**: Main window and proofing window management.
- **electron_python.js**: Python backend process communication.
- **electron_ipc.js**: IPC handlers for renderer-main process communication.
- **electron_lifecycle.js**: Electron app lifecycle events.
- **main.js**: New entry point that wires up all modules.

See `electron_main_breakdown.md` for a summary of what each file does.
