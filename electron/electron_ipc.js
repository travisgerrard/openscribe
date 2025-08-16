// electron_ipc.js
// Handles IPC handlers for renderer-main process communication

const { ipcMain } = require('electron');
const { setTrayIconByState } = require('./electron_tray');
const { store } = require('./electron_app_init'); // For accessing electron-store
const { getActualAvailableLLMs, getPythonShell } = require('./electron_python'); // To get models from Python

function initializeIpcHandlers() {
  // Handle tray icon state updates from renderer
  ipcMain.on('set-tray-state', (_event, state) => {
    // Defensive logging for debugging
    console.log('[IPC] set-tray-state received:', state);
    setTrayIconByState(state);
  });

  // Handle stop dictation (process audio) command
  ipcMain.on('stop-dictation', (_event) => {
    console.log('[IPC] stop-dictation received');
    const pythonShell = getPythonShell();
    if (pythonShell && pythonShell.send) {
      pythonShell.send('STOP_DICTATION');
      console.log('[IPC] STOP_DICTATION command sent to Python backend');
    } else {
      console.error('[IPC] Python shell not available for STOP_DICTATION command');
    }
  });

  // Handle abort dictation (discard audio) command
  ipcMain.on('abort-dictation', (_event) => {
    console.log('[IPC] abort-dictation received');
    const pythonShell = getPythonShell();
    if (pythonShell && pythonShell.send) {
      pythonShell.send('ABORT_DICTATION');
      console.log('[IPC] ABORT_DICTATION command sent to Python backend');
    } else {
      console.error('[IPC] Python shell not available for ABORT_DICTATION command');
    }
  });

  // Add other ipcMain.on handlers here if needed in the future

  // Handle settings saving
  ipcMain.on('save-settings', (_event, settings) => {
    console.log('[IPC] save-settings received:', settings);
    if (settings) {
      // Save wake words
      if (settings.wakeWords) {
        store.set('wakeWords', settings.wakeWords);
      }
      // Save prompts
      if (settings.proofingPrompt) {
        store.set('proofingPrompt', settings.proofingPrompt);
      }
      if (settings.letterPrompt) {
        store.set('letterPrompt', settings.letterPrompt);
      }
      // Save model selections
      if (settings.selectedProofingModel) {
        store.set('selectedProofingModel', settings.selectedProofingModel);
      }
      if (settings.selectedLetterModel) {
        store.set('selectedLetterModel', settings.selectedLetterModel);
      }
      // Save ASR model selection
      if (settings.selectedAsrModel) {
        store.set('selectedAsrModel', settings.selectedAsrModel);
      }
      console.log('[IPC] Settings saved to store.');

      // Proactively push updated config to Python backend so model changes take effect immediately
      try {
        const pythonShell = getPythonShell();
        if (pythonShell && pythonShell.send) {
          const configPayload = {
            wakeWords: store.get('wakeWords', { dictate: [], proofread: [], letter: [] }),
            proofingPrompt: store.get('proofingPrompt', ''),
            letterPrompt: store.get('letterPrompt', ''),
            selectedProofingModel: store.get('selectedProofingModel', ''),
            selectedLetterModel: store.get('selectedLetterModel', '')
          };
          const savedAsrModel = store.get('selectedAsrModel');
          if (savedAsrModel) {
            configPayload.selectedAsrModel = savedAsrModel;
          }
          const msg = `CONFIG:${JSON.stringify(configPayload)}`;
          pythonShell.send(msg);
          console.log('[IPC] Pushed updated CONFIG to Python backend.');
        } else {
          console.warn('[IPC] Python shell not available to push updated CONFIG. It will apply on next launch.');
        }
      } catch (e) {
        console.error('[IPC] Error pushing updated CONFIG to Python backend:', e);
      }
    }
  });

  // Handle settings loading
  ipcMain.handle('load-settings', async () => {
    const settings = {
      wakeWords: store.get('wakeWords', { dictate: [], proofread: [], letter: [] }),
      proofingPrompt: store.get('proofingPrompt', ''),
      letterPrompt: store.get('letterPrompt', ''),
      selectedProofingModel: store.get('selectedProofingModel', ''),
      selectedLetterModel: store.get('selectedLetterModel', ''),
      selectedAsrModel: store.get('selectedAsrModel', '')
    };
    console.log('[IPC] load-settings: returning', settings);
    return settings;
  });

  // Handle request for available models
  ipcMain.handle('get-available-models', async () => {
    console.log('[IPC] get-available-models: Attempting to fetch. Current actualAvailableLLMs from electron_python.js:', getActualAvailableLLMs());
    const models = getActualAvailableLLMs(); // Get models from Python via electron_python.js
    if (!models || models.length === 0) {
      console.warn('[IPC] get-available-models: No models returned from Python or list is empty. Check Python startup and MODELS_LIST message.');
      // Optionally return a default or error indicator to the settings UI
      return [{ id: '', name: 'Error: No models loaded' }];
    }
    console.log('[IPC] get-available-models: returning', models);
    return models;
  });

  // Handle vocabulary API calls
  ipcMain.handle('vocabulary-api', async (_event, command, data = {}) => {
    console.log('[IPC] vocabulary-api received:', command, data);

    try {
      const pythonShell = getPythonShell();
      if (!pythonShell || !pythonShell.send) {
        console.error('[IPC] Python shell not available for vocabulary API');
        return { success: false, error: 'Python backend not available' };
      }

      // Send vocabulary command to Python backend
      return new Promise((resolve) => {
        const messageId = `vocab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

        // Set up one-time listener for the response
        const responseHandler = (message) => {
          if (message.startsWith(`VOCAB_RESPONSE:${messageId}:`)) {
            pythonShell.removeListener('message', responseHandler);
            try {
              const response = JSON.parse(message.split(`VOCAB_RESPONSE:${messageId}:`)[1]);
              resolve(response);
            } catch (error) {
              console.error('[IPC] Error parsing vocabulary response:', error);
              resolve({ success: false, error: 'Invalid response format' });
            }
          }
        };

        pythonShell.on('message', responseHandler);

        // Send the command with message ID
        const vocabularyMessage = `VOCABULARY_API:${messageId}:${JSON.stringify({ command, data })}`;
        pythonShell.send(vocabularyMessage);

        // Set timeout for response
        setTimeout(() => {
          pythonShell.removeListener('message', responseHandler);
          resolve({ success: false, error: 'Vocabulary API timeout' });
        }, 5000);
      });

    } catch (error) {
      console.error('[IPC] Error in vocabulary API:', error);
      return { success: false, error: error.message };
    }
  });

  console.log('[IPC] IPC Handlers Initialized');
}

module.exports = { initializeIpcHandlers };
