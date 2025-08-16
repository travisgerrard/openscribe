## Stdout Contract (Essential)

Backend messages sent to Electron via stdout must begin with one of these prefixes:

- PYTHON_BACKEND_READY
- GET_CONFIG
- MODELS:            // one JSON summary at startup
- MODEL_SELECTED:    // changes only (mode:id)
- STATE:             // JSON state snapshots
- STATUS:            // status messages (color:text)
- FINAL_TRANSCRIPT:  // dictation final text
- DICTATION_PREVIEW: // full text before LLM in proof mode
- TRANSCRIPTION:     // PROOFED or LETTER final text

Any other console diagnostics should be written to the rotating log file via `log_text()` and suppressed from stdout when `MINIMAL_TERMINAL_OUTPUT` is enabled.

### Runtime verbosity control

- `CT_VERBOSE=1` disables minimal terminal mode (prints all `log_text` labels to stdout).
- `CT_LOG_WHITELIST="LABEL1,LABEL2"` adds additional labels to the terminal whitelist without code edits.

This contract reduces console noise while keeping UI and Electron logic stable.
# IPC Protocol Specification

## Overview
This document defines the standardized Inter-Process Communication (IPC) protocol between the Python backend and Electron frontend for CitrixTranscriber.

## Message Flow
```
Python Backend → electron_python.js → renderer_ipc.js → UI Components
```

## Message Format
All messages follow a standardized JSON format:

```
TYPE:PAYLOAD
```

Where:
- `TYPE`: One of the defined message types below
- `PAYLOAD`: JSON string containing the message data

## Message Types

### 1. STATUS Messages
**Format**: `STATUS:{"color": "string", "message": "string"}`

**Purpose**: General status updates for the UI

**Colors**: `blue`, `green`, `orange`, `red`, `grey`, `yellow`

**Example**:
```
STATUS:{"color": "blue", "message": "Listening for activation words..."}
```

### 2. STATE Messages  
**Format**: `STATE:{"programActive": boolean, "audioState": "string", "isDictating": boolean, "isProofingActive": boolean, "canDictate": boolean, "currentMode": "string|null"}`

**Purpose**: Application state synchronization

**audioState values**: `activation`, `dictation`, `processing`

**currentMode values**: `dictate`, `proofread`, `letter`, `null`

**Example**:
```
STATE:{"programActive": true, "audioState": "activation", "isDictating": false, "isProofingActive": false, "canDictate": true, "currentMode": null}
```

### 3. TRANSCRIPT Messages
**Format**: `TRANSCRIPT:{"type": "string", "text": "string", "duration": number}`

**Purpose**: Transcription results

**Types**: `final`, `proofed`, `letter`, `error`

**Example**:
```
TRANSCRIPT:{"type": "final", "text": "Hello world", "duration": 1.5}
```

### 4. STREAM Messages
**Format**: `STREAM:{"section": "string", "content": "string", "isComplete": boolean}`

**Purpose**: Streaming content (thinking/response)

**Sections**: `thinking`, `response`

**Example**:
```
STREAM:{"section": "thinking", "content": "Processing the request...", "isComplete": false}
```

### 5. CONFIG Messages
**Format**: `CONFIG_REQUEST` or `CONFIG_RESPONSE:{"config": object}`

**Purpose**: Configuration exchange

**Example**:
```
CONFIG_REQUEST
CONFIG_RESPONSE:{"selectedAsrModel": "whisper-large", "proofingPrompt": "..."}
```

### 6. CONTROL Messages
**Format**: `CONTROL:{"command": "string", "data": object}`

**Purpose**: Control commands

**Commands**: `stop_dictation`, `abort_dictation`, `toggle_active`, `restart`, `shutdown`

**Example**:
```
CONTROL:{"command": "stop_dictation", "data": {}}
```

### 7. ERROR Messages
**Format**: `ERROR:{"type": "string", "message": "string", "details": object}`

**Purpose**: Error reporting

**Types**: `validation`, `processing`, `system`, `ipc`

**Example**:
```
ERROR:{"type": "ipc", "message": "Invalid message format", "details": {"received": "malformed_msg"}}
```

### 8. AUDIO Messages
**Format**: `AUDIO:{"type": "string", "data": object}`

**Purpose**: Audio-related data

**Types**: `amplitude`, `volume`

**Example**:
```
AUDIO:{"type": "amplitude", "data": {"value": 85}}
```

### 9. SYSTEM Messages
**Format**: `SYSTEM:{"event": "string", "data": object}`

**Purpose**: System events

**Events**: `ready`, `shutdown`, `restart`, `hotkeys`

**Example**:
```
SYSTEM:{"event": "ready", "data": {}}
```

## Validation Rules

### Required Fields
All messages must have valid TYPE and properly formatted JSON PAYLOAD.

### Message Size Limits
- STATUS messages: Max 500 characters
- TRANSCRIPT messages: Max 50KB  
- STREAM messages: Max 10KB per chunk
- ERROR messages: Max 1KB

### Encoding
All messages must be UTF-8 encoded.

## Error Handling

### Invalid Message Format
If a message doesn't follow the protocol:
1. Log the invalid message
2. Send ERROR message back to sender
3. Continue processing other messages

### Missing Handlers
If no handler exists for a message type:
1. Log unknown message type
2. Send ERROR message indicating unknown type
3. Continue processing

### Validation Failures
If message payload fails validation:
1. Log validation details
2. Send ERROR message with validation info
3. Continue processing

## Testing Requirements

### Unit Tests
Each message type must have:
- Valid message creation test
- Invalid message handling test
- Payload validation test

### Integration Tests  
- End-to-end message flow tests
- State synchronization tests
- Error recovery tests

### Performance Tests
- Message throughput tests
- Large payload handling tests
- Memory usage tests

## Implementation Notes

### Python Backend
- Use `IPCManager` class to handle all message creation/validation
- All outbound messages go through `send_message(type, payload)`
- All inbound messages go through `handle_message(raw_message)`

### Electron Frontend
- Use `IPCHandler` class for message processing
- Validate all incoming messages against schema
- Route messages to appropriate UI handlers

### Migration Strategy
1. Implement new protocol alongside existing (dual support)
2. Migrate message types one by one
3. Remove old protocol once all types migrated
4. Add comprehensive tests throughout process

## Backward Compatibility

During migration, support both old and new formats:
- Detect message format automatically
- Convert old format to new format internally
- Log warnings for deprecated formats
- Remove old format support after migration complete 