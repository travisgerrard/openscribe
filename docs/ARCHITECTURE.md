# CitrixTranscriber Architecture Reference

## 🏗️ Overview

CitrixTranscriber is an Electron-based medical transcription application with a Python backend for ML processing. The app uses MLX models for text processing and includes wake word detection, speech recognition, and LLM-based proofreading.

## 📁 Project Structure

```
CitrixTranscriber/
├── main.js                     # Electron entry point (modular)
├── electron_main.js             # Main Electron process (monolithic backup)
├── package.json                 # Node.js dependencies
├── requirements.txt             # Python dependencies
├── 
├── 🐍 PYTHON BACKEND
├── main.py                      # Python entry point & main event loop
├── config.py                    # Configuration & settings
├── llm_handler.py              # MLX model loading & text processing
├── transcription_handler.py    # Speech recognition (Whisper)
├── audio_handler.py            # Audio capture & wake word detection
├── hotkey_manager.py           # Global hotkey handling
├── memory_monitor.py           # Memory usage tracking
├── utils.py                    # Logging utilities
├── 
├── 🖥️ ELECTRON FRONTEND
├── index.html                  # Main UI window
├── settings.html               # Settings window
├── preload.js                  # Main window preload script
├── settings_preload.js         # Settings window preload script
├── 
├── 📜 FRONTEND SCRIPTS
├── renderer_ipc.js             # IPC message handling & routing
├── renderer_expansion_ui.js    # Expandable UI areas (thinking/response)
├── proofing.js                 # Proofing window logic (unused?)
├── style.css                   # Main UI styles
├── 
├── 🔧 MODULAR ELECTRON (Alternative)
├── electron_windows.js         # Window management
├── electron_python.js          # Python process communication  
├── electron_ipc.js             # IPC handlers
├── electron_tray.js            # System tray management
├── electron_lifecycle.js       # App lifecycle events
└── electron_app_init.js        # App initialization
```

## 🔄 Data Flow Architecture

### 1. Audio Processing Pipeline
```
Microphone → AudioHandler → VoskModel → TranscriptionHandler → Main App
                ↓
            Wake Word Detection → Hotkey Trigger
```

### 2. LLM Processing Pipeline  
```
User Input → LLMHandler → MLX Model → Streaming Output → Frontend Display
                ↓
            Response Chunks → IPC → Renderer → UI Update
```

### 3. IPC Communication Flow
```
Python Backend ←→ Electron Main ←→ Renderer Process
       ↓              ↓              ↓
   stdout/stdin    IPC Messages   DOM Updates
```

## 🧩 Core Components

### Python Backend (`main.py`)

**Purpose**: Orchestrates all ML processing, audio handling, and business logic

**Key Classes**:
- `Application`: Main coordinator class
- `LLMHandler`: MLX model management
- `AudioHandler`: Audio capture & wake word detection  
- `TranscriptionHandler`: Speech-to-text conversion
- `HotkeyManager`: Global keyboard shortcuts

**Communication**: Sends status messages to Electron via stdout

### Electron Main Process (`electron_main.js` or modular)

**Purpose**: Bridge between Python backend and frontend UI

**Key Responsibilities**:
- Spawn & manage Python subprocess
- Handle IPC communication  
- Manage windows (main, settings)
- System tray integration
- Settings persistence

### Frontend Renderer (`renderer_*.js`)

**Purpose**: User interface and real-time status display

**Key Files**:
- `renderer_ipc.js`: Message routing & UI updates
- `renderer_expansion_ui.js`: Dynamic content areas
- `style.css`: UI styling & layout

## 🗣️ IPC Message Protocol

### Python → Electron → Renderer

| Message Type | Format | Purpose |
|--------------|--------|---------|
| Status | `STATUS:color:message` | General status updates |
| Thinking Stream | `STATUS:blue:PROOF_STREAM:thinking:content` | LLM thinking process |
| Response Stream | `STATUS:blue:PROOF_STREAM:chunk:content` | LLM response chunks |
| Stream End | `STATUS:black:PROOF_STREAM:end` | End of streaming |
| Transcription | `TRANSCRIPTION:type:text` | Speech recognition results |
| Models List | `MODELS_LIST:json` | Available LLM models |
| App State | `STATE:json` | Overall app state |

### Renderer → Electron → Python

| Action | IPC Channel | Python Command |
|--------|-------------|----------------|
| Start Dictation | `to-python` | `start_dictate` |
| Stop Dictation | `stop-dictation` | `STOP_DICTATION` |
| Proofread Text | `to-python` | `PROOFREAD:text:prompt` |
| Change Model | `to-python` | `CHANGE_MODEL:model_key` |

## 🎯 Current Streaming Issue

### Problem
LLM generates proper bullet points with newlines in Python, but frontend displays as single line.

### Debug Points
1. **Backend**: Check `PROOF_STREAM:chunk:` messages contain `\n`
2. **IPC**: Verify newlines pass through Electron unchanged  
3. **Frontend**: Ensure `textContent` vs `innerHTML` preserves newlines
4. **CSS**: Confirm `white-space: pre-wrap` is applied

### Data Flow for Streaming
```
MLX Model → LLMHandler → stdout → Electron → IPC → Renderer → DOM
    ↓           ↓           ↓         ↓      ↓        ↓
  chunk     PROOF_STREAM  forward   send   handle   display
```

## 🛠️ Refactoring Opportunities

### 1. **Simplify IPC Architecture**
- **Current**: Complex message parsing with multiple formats
- **Proposed**: Standardized JSON message protocol
- **Benefit**: Easier debugging, less parsing errors

### 2. **Consolidate Electron Files**  
- **Current**: Split between monolithic and modular approaches
- **Proposed**: Choose one consistent architecture
- **Benefit**: Reduce confusion, easier maintenance

### 3. **Centralize Frontend State**
- **Current**: State scattered across multiple JS files
- **Proposed**: Single state management system
- **Benefit**: Predictable UI updates, easier debugging

### 4. **Separate UI Components**
- **Current**: Mixed concerns in single files
- **Proposed**: Component-based architecture
- **Benefit**: Reusable components, clearer separation

### 5. **Standardize Error Handling**
- **Current**: Inconsistent error reporting
- **Proposed**: Centralized error handling with user-friendly messages
- **Benefit**: Better user experience, easier debugging

## 🔍 Debug Strategies

### 1. **Backend Logging**
```python
log_text("DEBUG_CATEGORY", f"Message: {data}")
```

### 2. **IPC Message Tracing**
```javascript
console.log(`[IPC] ${direction}: ${message}`);
```

### 3. **Frontend State Inspection**
```javascript
console.log(`[UI] State: ${JSON.stringify(state)}`);
```

### 4. **Memory & Performance**
```python
memory_monitor.log_operation(operation, details)
```

## 🚀 Future Improvements

1. **TypeScript Migration**: Add type safety to frontend
2. **Component Library**: Create reusable UI components  
3. **State Management**: Implement Redux or similar
4. **Testing**: Add unit & integration tests
5. **Documentation**: Auto-generate API docs
6. **Performance**: Optimize streaming & memory usage
7. **Configuration**: Runtime config without restart

---

**Last Updated**: 2025-06-02
**Maintainer**: AI Assistant + User
**Status**: Living document - update as architecture evolves 