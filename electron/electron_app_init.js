// electron_app_init.js
// Handles app initialization, config, and persistent settings

const Store = require('electron-store');

// Initialize electron-store
const store = new Store({
  defaults: {
    selectedProofingModel: 'default-proofing-model',
    selectedLetterModel: 'default-letter-model',
    proofingPrompt: 'You are proofreading text that will be entered into a medical chart by a doctor.\nEnsure the text is grammatically correct, concise, and maintains clinical accuracy.\nOrganize distinct ideas into individual paragraphs and concise sentences.\nReturn only the corrected version without adding any extra comments or context.\n\nExample:\nInput:\nThe patient states she has been experiencing headaches for the past two weeks. no associated nausea or vomiting. Labs were normal but we are waiting for imaging results.\n\nOutput:\n- The patient reports experiencing headaches for the past two weeks.\n- There is no associated nausea or vomiting.\n- Laboratory results were normal; imaging results are pending.',
    letterPrompt: 'You are proofreading text that will be sent from a primary care doctor to his patient. Ensure the text is grammatically correct, concise, and maintains clinical accuracy. Return only the corrected version without adding any extra comments or context.',
    wakeWords: {
      dictate: ['note'],
      proofread: ['proof'],
      letter: ['letter']
    }
  },
  migrations: {
    '1.0.0-migrateWakeWords': store => {
      const wakeWords = store.get('wakeWords');
      if (Array.isArray(wakeWords)) {
        store.set('wakeWords', {
          dictate: wakeWords,
          proofread: [],
          letter: []
        });
      } else if (typeof wakeWords !== 'object' || wakeWords === null || !Object.prototype.hasOwnProperty.call(wakeWords, 'dictate')) {
        store.set('wakeWords', {
          dictate: ['note'],
          proofread: ['proof'],
          letter: ['letter']
        });
      }
    }
  }
});

module.exports = { store };
