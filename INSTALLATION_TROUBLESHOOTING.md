# Installation Troubleshooting Guide

## 🚨 Common Issues and Solutions

### Issue 1: Mock Transcription Instead of Real Transcription

**Symptoms:**
- You see messages like `[MOCK PARAKEET TRANSCRIPTION] Test transcription result`
- Speech recognition isn't working
- No actual transcription occurs

**Root Cause:**
The application is trying to use a Parakeet model for transcription, but the required `parakeet_mlx` library isn't installed.

**Solutions:**

#### Option A: Install the Missing Library (Recommended)
```bash
# Install the required parakeet-mlx library
python3 -m pip install parakeet-mlx

# Or install all dependencies at once
python3 -m pip install -r requirements.txt
```

#### Option B: Switch to Whisper (Easier, More Reliable)
1. Open the application settings
2. Go to the "ASR Model" section
3. Select "Whisper (large-v3-turbo) - Recommended" instead of Parakeet
4. Save settings and restart the application

#### Option C: Force Default Model
If the above doesn't work, manually set the default model:
```bash
# Edit user_settings.json and change:
"selectedAsrModel": "mlx-community/whisper-large-v3-turbo"
```

### Issue 2: Missing Python Dependencies

**Symptoms:**
- `ModuleNotFoundError: No module named 'phonetics'` (or other modules)
- Application crashes on startup
- Import errors in terminal

**Solution:**
```bash
# Install all required Python dependencies
python3 -m pip install -r requirements.txt

# If you get permission errors, use:
python3 -m pip install --user -r requirements.txt
```

### Issue 3: Audio Input Not Working

**Symptoms:**
- No audio is being recorded
- Microphone permissions denied
- Audio devices not detected

**Solutions:**

#### macOS:
1. Go to System Preferences > Security & Privacy > Privacy > Microphone
2. Ensure your terminal/IDE has microphone access
3. Check that your microphone is set as the default input device

#### Windows:
1. Right-click the speaker icon in taskbar
2. Select "Open Sound settings"
3. Ensure your microphone is set as default and working

#### Linux:
1. Check audio device permissions
2. Ensure PulseAudio or ALSA is running
3. Test microphone with: `arecord -d 5 test.wav`

### Issue 4: Model Download Failures

**Symptoms:**
- Models fail to download
- "Model not found" errors
- Slow or interrupted downloads

**Solutions:**

#### Check Internet Connection:
```bash
# Test connection to Hugging Face
curl -I https://huggingface.co

# Test connection to GitHub
curl -I https://github.com
```

#### Use Alternative Download Method:
```bash
# Set environment variable for better download handling
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DISABLE_TELEMETRY=1

# Then run the application
npm start
```

#### Manual Model Download:
If automatic download fails, you can manually download models:
```bash
# Create models directory
mkdir -p models

# Download Whisper model manually
git lfs install
git clone https://huggingface.co/mlx-community/whisper-large-v3-turbo models/whisper-large-v3-turbo
```

### Issue 5: Memory Issues

**Symptoms:**
- Application crashes with "out of memory" errors
- Slow performance
- System becomes unresponsive

**Solutions:**

#### Reduce Memory Usage:
```bash
# Set light mode to avoid heavy model loads
export CT_LIGHT_MODE=1

# Start the application
npm start
```

#### Use Smaller Models:
1. In settings, select smaller models:
   - Use "Qwen3-8B-4bit" instead of "Qwen3-14B-4bit-AWQ"
   - Use "Whisper (large-v3-turbo)" instead of larger models

#### Check System Resources:
```bash
# Check available RAM
free -h  # Linux
vm_stat   # macOS
wmic computersystem get TotalPhysicalMemory  # Windows

# Ensure you have at least 8GB free RAM for basic operation
# 16GB+ recommended for optimal performance
```

## 🔧 Quick Fix Checklist

If you're experiencing issues, try these steps in order:

1. ✅ **Install Python dependencies:**
   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. ✅ **Check audio permissions** (especially on macOS)

3. ✅ **Switch to Whisper model** in settings instead of Parakeet

4. ✅ **Set light mode** if you have memory constraints:
   ```bash
   export CT_LIGHT_MODE=1
   npm start
   ```

5. ✅ **Check system resources** (RAM, disk space)

6. ✅ **Restart the application** after making changes

## 📱 Platform-Specific Notes

### macOS
- **Microphone permissions** are the most common issue
- **Rosetta 2** may be needed for Intel Macs
- **Python 3.11+** recommended for best compatibility

### Windows
- **Python 3.11+** required
- **Visual C++ Redistributable** may be needed
- **WSL2** works well for development

### Linux
- **Python 3.11+** required
- **System packages** may need to be installed:
  ```bash
  sudo apt-get install portaudio19-dev python3-dev
  ```

## 🆘 Getting Help

If you're still experiencing issues:

1. **Check the logs** in `transcript_log.txt`
2. **Look for error messages** in the terminal
3. **Try the troubleshooting steps** above
4. **Check system requirements** in the main README
5. **Open an issue** on GitHub with:
   - Your operating system and version
   - Python version (`python3 --version`)
   - Node.js version (`node --version`)
   - Complete error messages
   - Steps to reproduce the issue

## 🎯 Recommended Configuration

For the most reliable experience:

- **ASR Model:** `mlx-community/whisper-large-v3-turbo`
- **Proofing Model:** `mlx-community/Qwen3-8B-4bit`
- **Letter Model:** `mlx-community/Qwen3-8B-4bit`
- **Python Version:** 3.11+
- **RAM:** 16GB+
- **Storage:** 20GB+ free space

This configuration provides excellent transcription quality while maintaining good performance and reliability.
