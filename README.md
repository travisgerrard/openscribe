# Professional Transcriber

A professional-grade speech-to-text transcription application with AI-powered proofreading and formatting capabilities. Built with Python, Electron, and modern AI models.

## Features

- **Real-time Speech Recognition**: Powered by Whisper and Parakeet models
- **AI-Powered Proofreading**: Advanced language models for text correction and formatting
- **Custom Vocabulary Training**: Learn and automatically correct specialized terminology
- **Hotkey Support**: Global hotkeys for quick access to all features
- **Cross-platform**: Works on macOS, Windows, and Linux
- **Professional UI**: Clean, modern interface with Electron frontend

## Use Cases

- Professional documentation
- Meeting transcriptions
- Report writing
- General dictation tasks
- Any scenario requiring accurate speech-to-text conversion

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- macOS (primary platform), Windows, or Linux

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/professional-transcriber.git
   cd professional-transcriber
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Node.js dependencies**
   ```bash
   npm install
   ```

4. **Download required models**
   
   **Important**: The application requires AI models to function. You have two options:
   
   **Option A: Automatic Download (Recommended)**
   - Run the application: `npm start`
   - The app will automatically download required models on first run
   - This may take 10-30 minutes depending on your internet connection
   
   **Option B: Manual Download**
- Create the required directories in the project root:
  ```bash
  mkdir -p models vosk
  ```

- Download the following models:
  - **Speech Recognition**: `mlx-community/parakeet-tdt-0.6b-v2` (~1.5GB)
    - Place in `models/mlx-community/parakeet-tdt-0.6b-v2/`
  - **Text Processing**: `mlx-community/Qwen3-14B-4bit-AWQ` (~8GB)
    - Place in `models/mlx-community/Qwen3-14B-4bit-AWQ/`
  - **Alternative**: `mlx-community/Qwen3-8B-4bit` (~4GB)
    - Place in `models/mlx-community/Qwen3-8B-4bit/`
  - **Wake Word Detection**: Vosk model (~100MB)
    - Download from: https://alphacephei.com/vosk/models
    - Extract to `vosk/` directory (e.g., `vosk-model-small-en-us-0.15`)
   
   **Note**: Models are large files (5-15GB total). Ensure you have sufficient disk space and a stable internet connection.

### Running the Application

```bash
# Start the application
npm start
```

**First Run**: The application will automatically download required AI models (5-15GB). This may take 10-30 minutes. You'll see progress indicators during the download.

**Subsequent Runs**: The application will start immediately using the cached models.

## Usage

### Basic Dictation

1. Press `Cmd+Shift+A` (macOS) to toggle the application active
2. Press `Cmd+Shift+D` to start dictation
3. Speak clearly into your microphone
4. The transcribed text will appear in the interface
5. Press `Cmd+Shift+S` to stop dictation

### Proofreading

1. Select text in any application
2. Press `Cmd+Shift+P` to proofread the selected text
3. The corrected version will be copied to your clipboard

### Custom Vocabulary

1. Open the settings panel
2. Navigate to the Vocabulary section
3. Add custom terms and their variations
4. The system will automatically learn and correct these terms

## Configuration

### Hotkeys

Default hotkeys (macOS):
- `Cmd+Shift+A`: Toggle application active/inactive
- `Cmd+Shift+D`: Start dictation
- `Cmd+Shift+P`: Start proofreading
- `Cmd+Shift+L`: Start letter mode
- `Cmd+Shift+S`: Stop dictation
- `Cmd+Shift+R`: Restart application
- `Cmd+Shift+H`: Show hotkeys
- `Cmd+Shift+M`: Toggle mini mode

### Wake Words

You can also use voice commands:
- Say "note" or "dictate" to start dictation
- Say "proof" or "proofread" to start proofreading
- Say "letter" to start letter mode

## Architecture

The application consists of several key components:

- **Python Backend**: Handles audio processing, transcription, and AI operations
- **Electron Frontend**: Provides the user interface
- **Audio Handler**: Manages microphone input and audio processing
- **Transcription Handler**: Coordinates speech recognition
- **LLM Handler**: Manages AI-powered text processing
- **Vocabulary Manager**: Handles custom terminology learning

## Development

### Project Structure

```
professional-transcriber/
├── src/                    # Python source code
│   ├── audio/             # Audio processing
│   ├── config/            # Configuration management
│   ├── llm/               # AI model handling
│   ├── vocabulary/        # Custom vocabulary system
│   └── utils/             # Utility functions
├── frontend/              # Electron frontend
├── tests/                 # Test suite
├── docs/                  # Documentation
└── scripts/               # Build and utility scripts
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/
```

### Building

```bash
# Build for development
npm run build:python
npm run build:electron

# Build for distribution
npm run dist
```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Privacy

This application processes audio locally on your machine. No audio data is sent to external servers unless you explicitly configure cloud-based models.

## Troubleshooting

### Common Issues

**Models not downloading automatically:**
- Check your internet connection
- Ensure you have sufficient disk space (at least 20GB free)
- Try running the application with administrator privileges
- Check firewall settings that might block downloads

**Vosk model not found:**
- Download Vosk model from: https://alphacephei.com/vosk/models
- Extract the model files to the `vosk/` directory
- Ensure the directory structure is correct (e.g., `vosk/vosk-model-small-en-us-0.15/`)

**Application crashes on startup:**
- Verify Python 3.8+ and Node.js 16+ are installed
- Check that all dependencies are installed: `pip install -r requirements.txt && npm install`
- Ensure models are properly downloaded to the `models/` directory

**Poor transcription quality:**
- Use a good quality microphone
- Speak clearly and at a normal pace
- Reduce background noise
- Check microphone permissions in your OS settings

### Getting Help

- **Issues**: Report bugs and request features on [GitHub Issues](https://github.com/yourusername/professional-transcriber/issues)
- **Discussions**: Join the conversation on [GitHub Discussions](https://github.com/yourusername/professional-transcriber/discussions)
- **Documentation**: Check the [docs/](docs/) directory for detailed documentation

## Acknowledgments

- Built with [Whisper](https://github.com/openai/whisper) for speech recognition
- Powered by [MLX](https://github.com/ml-explore/mlx) for efficient AI model inference
- UI built with [Electron](https://electronjs.org/)

## Roadmap

- [ ] Cloud model support
- [ ] Multi-language support
- [ ] Advanced formatting options
- [ ] Plugin system
- [ ] Mobile companion app

---

**Note**: This is an open-source project. For professional use, please ensure compliance with your organization's security and privacy policies. 