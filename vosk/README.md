# Vosk Directory

This directory is for the Vosk speech recognition model.

## About Vosk

Vosk is an offline speech recognition toolkit that provides:
- Wake word detection
- Voice activity detection
- Offline speech recognition capabilities

## Model Download

The Vosk model will be automatically downloaded by the application when needed.

## Manual Installation

If automatic download fails, you can manually download a Vosk model:

1. Visit: https://alphacephei.com/vosk/models
2. Download a model suitable for your language (e.g., `vosk-model-small-en-us-0.15`)
3. Extract the model files to this directory

## Directory Structure

The Vosk model should contain:
- `am/` - Acoustic model files
- `conf/` - Configuration files
- `graph/` - Language model files
- `ivector/` - i-vector files (if available)
- `README` - Model information

## Supported Languages

Vosk supports many languages. Choose a model appropriate for your primary language:
- English: `vosk-model-small-en-us-0.15`
- Spanish: `vosk-model-small-es-0.42`
- French: `vosk-model-small-fr-0.22`
- German: `vosk-model-small-de-0.15`
- And many more...

## Troubleshooting

- **Model not found**: Ensure the model is properly extracted to this directory
- **Poor recognition**: Try a larger model for better accuracy
- **Language issues**: Download a model for your specific language 