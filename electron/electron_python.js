// electron_python.js
// Handles Python backend process communication

const { PythonShell } = require('python-shell');
const { store } = require('./electron_app_init'); // Assuming this is still needed for config
const path = require('path');
const { app } = require('electron');
const fs = require('fs');

let pythonShell = null;
let actualAvailableLLMs = []; // To store models received from Python
// currentProofingActiveState and isFirstResponseChunkInStream removed as UI updates for expansion areas
// are now handled by PROOF_STREAM messages via renderer_ipc.js

/**
 * Get the path to the Python backend executable
 * In development: use Python directly
 * In production: use bundled executable
 */
function getPythonBackendPath() {
  const isDev = !app.isPackaged;

  if (isDev) {
    // Development mode - use Python directly
    return {
      mode: 'python',
      scriptPath: path.join(__dirname, '..'), // Go up one level from electron/ to root
      script: 'main.py'
    };
  } else {
    // Production mode - use bundled executable
    const resourcesPath = process.resourcesPath;
    const backendPath = path.join(resourcesPath, 'CitrixTranscriberBackend.app', 'Contents', 'MacOS', 'citrix-transcriber-backend');

    // Check if bundled backend exists
    if (fs.existsSync(backendPath)) {
      return {
        mode: 'executable',
        executablePath: backendPath
      };
    } else {
      // Fallback to Python if executable not found
      console.warn('Bundled backend not found, falling back to Python');
      return {
        mode: 'python',
        scriptPath: resourcesPath,
        script: 'main.py'
      };
    }
  }
}

function startPythonShell(onMessage, onError, onClose) {
  const backendConfig = getPythonBackendPath();

  console.log('[ElectronPython] Starting Python backend with config:', backendConfig);

  if (backendConfig.mode === 'executable') {
    // Use spawn for executable
    const { spawn } = require('child_process');

    console.log('[ElectronPython] Launching bundled executable:', backendConfig.executablePath);

    const pythonProcess = spawn(backendConfig.executablePath, [], {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: path.dirname(backendConfig.executablePath)
    });

    // Create a PythonShell-like interface for the executable
    pythonShell = {
      childProcess: pythonProcess,
      send: (message) => {
        if (pythonProcess.stdin.writable) {
          pythonProcess.stdin.write(message + '\n');
        }
      },
      kill: () => {
        pythonProcess.kill();
      },
      terminated: false
    };

    // Handle stdout (messages from Python)
    pythonProcess.stdout.on('data', (data) => {
      const messages = data.toString().split('\n').filter(msg => msg.trim());
      messages.forEach(message => {
        // Only log non-AUDIO_AMP messages to reduce console spam
        if (!message.startsWith('AUDIO_AMP:')) {
          console.log('[ElectronPython] Raw message from Python:', `'${message}'`);
        }
        if (onMessage) onMessage(message);
      });
    });

    // Handle stderr (errors from Python)
    pythonProcess.stderr.on('data', (data) => {
      const errorMessage = data.toString();
      console.log('[Python STDERR]', errorMessage);
      if (onError) onError(errorMessage);
    });

    // Handle process exit
    pythonProcess.on('close', (code) => {
      console.log(`[ElectronPython] Python process exited with code ${code}`);
      pythonShell.terminated = true;
      if (onClose) onClose(code);
    });

    pythonProcess.on('error', (error) => {
      console.error('[ElectronPython] Failed to start Python process:', error);
      if (onError) onError(error.message);
    });

  } else {
    // Use PythonShell for development
    const options = {
      mode: 'text',
      pythonPath: '/Users/travisgerrard/Documents/Apps/CitrixTranscriberPython/whisper_env/bin/python',
      pythonOptions: ['-u'],
      scriptPath: backendConfig.scriptPath
    };

    console.log('[ElectronPython] Starting PythonShell with options:', options);

    pythonShell = new PythonShell(backendConfig.script, options);

    pythonShell.on('message', (message) => {
      // Only log non-AUDIO_AMP messages to reduce console spam
      if (!message.startsWith('AUDIO_AMP:')) {
        console.log('[ElectronPython] Raw message from Python:', `'${message}'`);
      }
      if (onMessage) onMessage(message);
    });

    pythonShell.on('stderr', (stderr) => {
      console.log('[Python STDERR]', stderr);
      if (onError) onError(stderr);
    });

    pythonShell.on('close', () => {
      console.log('[ElectronPython] Python shell closed');
      if (onClose) onClose();
    });

    pythonShell.on('error', (error) => {
      console.error('[ElectronPython] Python shell error:', error);
      if (onError) onError(error.message);
    });
  }

  return pythonShell;
}

function getPythonShell() {
  return pythonShell;
}

function startPythonBackend(mainWindow) {
  const options = {
    mode: 'text',
    pythonPath: '/Users/travisgerrard/Documents/Apps/CitrixTranscriberPython/whisper_env/bin/python', // Use conda environment
    pythonOptions: ['-u'], // Unbuffered output
    scriptPath: path.join(__dirname, '..') // Path to main.py (go up from electron/ to root)
  };
  pythonShell = new PythonShell('main.py', options);

  pythonShell.on('message', function (message) {
    // Only log non-AUDIO_AMP messages to reduce console spam
    if (!message.startsWith('AUDIO_AMP:')) {
      console.log(`[ElectronPython] Raw message from Python: '${message}'`);
    }

    if (typeof message !== 'string') {
      console.warn('[ElectronPython] Received non-string message from Python:', message);
      return;
    }

    const trimmedMessage = message.trim();

    // Handle GET_CONFIG request from Python
    if (trimmedMessage === 'GET_CONFIG') {
      console.log('[ElectronPython] Processing GET_CONFIG');
      const pythonConfig = {
        wakeWords: store.get('wakeWords', { dictate: [], proofread: [], letter: [] }),
        proofingPrompt: store.get('proofingPrompt'),
        letterPrompt: store.get('letterPrompt'),
        selectedProofingModel: store.get('selectedProofingModel'),
        selectedLetterModel: store.get('selectedLetterModel'),
        selectedAsrModel: store.get('selectedAsrModel') // Ensure ASR model is also sent
      };
      if (pythonShell && pythonShell.stdin && !pythonShell.stdin.destroyed) {
        pythonShell.send(`CONFIG:${JSON.stringify(pythonConfig)}\n`);
        console.log('[ElectronPython] Sent CONFIG to Python.');
      } else {
        console.error('[ElectronPython] Python shell not available for sending CONFIG.');
      }
      return;
    }

    // Handle STATE messages from Python
    if (trimmedMessage.startsWith('STATE:')) {
      console.log('[ElectronPython] Processing STATE message.');
      try {
        const stateContent = trimmedMessage.substring('STATE:'.length);

        // Find the end of the JSON by looking for the closing brace
        let jsonEndIndex = -1;
        let braceCount = 0;
        let inString = false;
        let escapeNext = false;

        for (let i = 0; i < stateContent.length; i++) {
          const char = stateContent[i];

          if (escapeNext) {
            escapeNext = false;
            continue;
          }

          if (char === '\\') {
            escapeNext = true;
            continue;
          }

          if (char === '"') {
            inString = !inString;
            continue;
          }

          if (!inString) {
            if (char === '{') {
              braceCount++;
            } else if (char === '}') {
              braceCount--;
              if (braceCount === 0) {
                jsonEndIndex = i + 1;
                break;
              }
            }
          }
        }

        const stateJson = jsonEndIndex > 0 ? stateContent.substring(0, jsonEndIndex) : stateContent;
        console.log('[ElectronPython] Extracted JSON:', stateJson);

        const state = JSON.parse(stateJson);
        // const mainWin = mainWindow; // mainWindow is from the startPythonBackend closure

        if (mainWindow) {
          const shouldBeOnTop = state.isDictating || state.isProofingActive;
          if (mainWindow.isAlwaysOnTop() !== shouldBeOnTop) {
            mainWindow.setAlwaysOnTop(shouldBeOnTop);
          }
          if (state.isDictating && !mainWindow.isVisible()) {
            mainWindow.show();
          }
          if (mainWindow.webContents && !mainWindow.webContents.isDestroyed()) {
            try {
              const dictationUpdateData = {
                type: 'dictation_status_update',
                isDictating: state.isDictating,
                audioState: state.audioState,
                programActive: state.programActive,
                currentMode: state.currentMode
              };
              mainWindow.webContents.send('ui-update', dictationUpdateData);
            } catch (error) {
              console.error('[ElectronPython] Error sending UI update:', error.message);
            }
          }
        }
      } catch (e) {
        console.error('[ElectronPython] Error parsing STATE message:', e, trimmedMessage);
      }
      return;
    }

    // Handle PYTHON_BACKEND_READY
    if (trimmedMessage === 'PYTHON_BACKEND_READY') {
      console.log('[ElectronPython] PYTHON_BACKEND_READY detected. Requesting models list...');
      if (pythonShell && pythonShell.stdin && !pythonShell.stdin.destroyed) {
        pythonShell.send('MODELS_REQUEST\n');
        console.log('[ElectronPython] MODELS_REQUEST sent to Python.');
      } else {
        console.error('[ElectronPython] Python shell not available for sending MODELS_REQUEST.');
      }
      return;
    }

    // Handle MODELS_LIST
    if (trimmedMessage.startsWith('MODELS_LIST:')) {
      console.log('[ElectronPython] Processing MODELS_LIST message.');
      try {
        const modelsJson = trimmedMessage.substring('MODELS_LIST:'.length);
        actualAvailableLLMs = JSON.parse(modelsJson);
        console.log('[ElectronPython] Received and stored available LLMs:', actualAvailableLLMs);
      } catch (e) {
        console.error('[ElectronPython] Error parsing MODELS_LIST:', e, trimmedMessage);
        actualAvailableLLMs = [];
      }
      return;
    }

    // Handle STATUS messages for tray icon updates
    if (trimmedMessage.startsWith('STATUS:')) {
      const { setTrayIconByState } = require('./electron_tray');
      const statusContent = trimmedMessage.substring('STATUS:'.length);
      const firstColonIndex = statusContent.indexOf(':');

      if (firstColonIndex !== -1) {
        const color = statusContent.substring(0, firstColonIndex);
        const messageText = statusContent.substring(firstColonIndex + 1);
        console.log('[ElectronPython] STATUS message color:', color);

        // Only update tray icon for very specific state-changing messages
        let shouldUpdateTray = false;
        let trayState = 'inactive';

        if (color === 'blue' && messageText.includes('Listening for activation words')) {
          trayState = 'activation';
          shouldUpdateTray = true;
        } else if (color === 'green' && (messageText.includes('Listening for dictation') || messageText.includes('Dictation started'))) {
          trayState = 'dictation';
          shouldUpdateTray = true;
        } else if (color === 'orange' && (messageText.includes('Loading') || messageText.includes('Processing'))) {
          trayState = 'processing';
          shouldUpdateTray = true;
        } else if ((color === 'grey' || color === 'gray') && (messageText.includes('Microphone is not listening') || messageText.includes('Shutdown complete'))) {
          trayState = 'inactive';
          shouldUpdateTray = true;
        }

        if (shouldUpdateTray) {
          console.log('[ElectronPython] Updating tray icon to state:', trayState);
          setTrayIconByState(trayState);
        } else {
          console.log('[ElectronPython] Not updating tray icon for this STATUS message');
        }
      }

      // Continue to forward to renderer for UI updates
    }

    // Fall-through for other messages - forward to renderer
    // Only log non-AUDIO_AMP forwarding to reduce console spam
    if (!trimmedMessage.startsWith('AUDIO_AMP:')) {
      console.log(`[ElectronPython] Forwarding unhandled message to renderer: '${trimmedMessage}'`);
    }
    // const mainWin = mainWindow; // mainWindow is from the startPythonBackend closure
    if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isDestroyed()) {
      try {
        mainWindow.webContents.send('from-python', trimmedMessage);
      } catch (error) {
        console.error('[ElectronPython] Error sending message to renderer:', error.message);
      }
    } else {
      // Don't log warnings during shutdown - this is expected
      if (mainWindow && mainWindow.webContents && mainWindow.webContents.isDestroyed()) {
        // Window is being destroyed, this is normal during shutdown
      } else {
        console.warn('[ElectronPython] mainWindow or webContents not available for forwarding unhandled message.');
      }
    }
  });

  pythonShell.on('stderr', function (stderr) {
    console.error('[Python STDERR]', stderr);
    const mainWin = mainWindow; // Use the mainWindow parameter passed to startPythonBackend
    if (mainWin && mainWin.webContents && !mainWin.webContents.isDestroyed()) {
      try {
        mainWin.webContents.send('python-stderr', stderr);
      } catch (error) {
        console.error('[ElectronPython] Error sending stderr to renderer:', error.message);
      }
    }
  });

  pythonShell.on('error', function (err) {
    console.error('[PythonShell Error]', err);
  });

  pythonShell.on('close', function () {
    console.log('[PythonShell] Process finished.');
    pythonShell = null;
  });

  // Handle shutdown signals from Python
  pythonShell.on('message', function (message) {
    if (message && message.trim() === 'BACKEND_SHUTDOWN_FINALIZED') {
      console.log('[ElectronPython] Python backend shutdown finalized');
      pythonShell = null;
    }
  });
}

function shutdownPythonBackend() {
  console.log('[ElectronPython] Initiating Python backend shutdown');

  if (!pythonShell) {
    console.log('[ElectronPython] Python shell already null, nothing to shutdown');
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      console.log('[ElectronPython] Shutdown timeout, force killing Python process');
      if (pythonShell && !pythonShell.killed) {
        pythonShell.kill('SIGTERM');

        // Final force kill if needed
        setTimeout(() => {
          if (pythonShell && !pythonShell.killed) {
            console.log('[ElectronPython] Force killing with SIGKILL');
            pythonShell.kill('SIGKILL');
          }
          pythonShell = null;
          resolve();
        }, 2000);
      } else {
        pythonShell = null;
        resolve();
      }
    }, 5000); // 5 second timeout

    // Listen for proper shutdown confirmation
    const shutdownListener = (message) => {
      if (message && message.trim() === 'BACKEND_SHUTDOWN_FINALIZED') {
        console.log('[ElectronPython] Python backend confirmed shutdown');
        clearTimeout(timeout);
        pythonShell = null;
        resolve();
      }
    };

    if (pythonShell) {
      pythonShell.on('message', shutdownListener);

      // Send shutdown command
      if (pythonShell.stdin && !pythonShell.stdin.destroyed) {
        console.log('[ElectronPython] Sending SHUTDOWN command to Python');
        pythonShell.send('SHUTDOWN');
      } else {
        console.log('[ElectronPython] Python stdin not available, force killing');
        clearTimeout(timeout);
        if (!pythonShell.killed) {
          pythonShell.kill('SIGTERM');
        }
        pythonShell = null;
        resolve();
      }
    } else {
      clearTimeout(timeout);
      resolve();
    }
  });
}

function getActualAvailableLLMs() {
  return actualAvailableLLMs;
}

module.exports = { startPythonShell, getPythonShell, pythonShell, getActualAvailableLLMs, shutdownPythonBackend, startPythonBackend };