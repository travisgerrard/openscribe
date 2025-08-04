# CitrixTranscriber File Reorganization Plan

## 📋 Executive Summary

This plan outlines a comprehensive reorganization of the CitrixTranscriber codebase to improve maintainability, scalability, and developer experience. The reorganization will separate concerns into logical directories while maintaining full functionality.

## 🎯 Goals

- **Improve maintainability** by organizing files by functionality and technology
- **Enhance developer experience** with clear separation of concerns
- **Prepare for scaling** as the project grows in complexity
- **Maintain zero functionality regression** during migration
- **Preserve git history** for all moved files

## 📊 Current State Analysis

### Current Root Directory Structure
```
CitrixTranscriber/
├── audio_handler.py
├── config.py
├── electron-python.js
├── hotkey_manager.py
├── index.html
├── llm_handler.py
├── main.js
├── main.py
├── medical_text_formatter.py
├── memory_monitor.py
├── proofing.html
├── proofing.js
├── renderer_conflict_ui.js
├── renderer_ipc.js
├── renderer_state.js
├── settings_manager.py
├── style.css
├── text_processing_utils.js
├── transcription_handler.py
├── utils.py
├── tests/
├── docs/
└── various config files...
```

### Issues with Current Structure
- **Mixed technologies**: Python, JavaScript, HTML, CSS all in root
- **Unclear boundaries**: Main process vs renderer process files intermixed
- **Cognitive overload**: 20+ files in root directory
- **Scaling limitations**: Hard to add new features without cluttering
- **Onboarding friction**: New developers struggle to orient

## 🏗️ Proposed New Structure

```
CitrixTranscriber/
├── src/
│   ├── main/                           # Electron main process
│   │   ├── main.js                     # Entry point
│   │   ├── electron-python.js          # Python bridge
│   │   └── lifecycle/                  # App lifecycle management
│   │       └── app-lifecycle.js
│   │
│   ├── renderer/                       # Electron renderer process
│   │   ├── main-window/               # Main application window
│   │   │   ├── index.html
│   │   │   ├── style.css
│   │   │   ├── js/
│   │   │   │   ├── renderer_state.js
│   │   │   │   ├── renderer_ipc.js
│   │   │   │   └── renderer_conflict_ui.js
│   │   │   └── components/            # Reusable UI components
│   │   │
│   │   ├── proofing-window/           # Proofing window
│   │   │   ├── proofing.html
│   │   │   ├── proofing.js
│   │   │   └── proofing.css
│   │   │
│   │   └── shared/                    # Shared renderer utilities
│   │       ├── text_processing_utils.js
│   │       └── ui-helpers.js
│   │
│   ├── backend/                       # Python backend
│   │   ├── main.py                    # Entry point
│   │   ├── handlers/                  # Core functionality handlers
│   │   │   ├── audio_handler.py
│   │   │   ├── llm_handler.py
│   │   │   ├── transcription_handler.py
│   │   │   └── hotkey_manager.py
│   │   ├── formatters/                # Text processing & formatting
│   │   │   └── medical_text_formatter.py
│   │   ├── core/                      # Core system components
│   │   │   ├── memory_monitor.py
│   │   │   └── settings_manager.py
│   │   └── utils/                     # Backend utilities
│   │       └── utils.py
│   │
│   └── shared/                        # Cross-platform shared code
│       ├── types/                     # TypeScript definitions
│       └── constants/                 # Shared constants
│
├── config/                            # Configuration files
│   ├── config.py
│   ├── user_settings.json
│   └── app-config.json
│
├── tests/                             # Test suite (already good!)
│   ├── test_status_indicators.py
│   ├── test_dictation_workflow.py
│   ├── test_ui_synchronization.py
│   └── test_conflict_notification.py
│
├── docs/                              # Documentation
│   ├── architecture.md
│   ├── technical.md
│   ├── status.md
│   └── file-reorganization-plan.md
│
├── scripts/                           # Build & utility scripts
│   ├── build.js
│   └── dev-server.js
│
├── assets/                            # Static assets
│   ├── icons/
│   └── images/
│
└── [root config files]                # package.json, .gitignore, etc.
```

## 🚀 Migration Plan

### Phase 1: Preparation (1 hour)
1. **Create new directory structure**
   ```bash
   mkdir -p src/{main,renderer,backend,shared}
   mkdir -p src/main/lifecycle
   mkdir -p src/renderer/{main-window,proofing-window,shared}
   mkdir -p src/renderer/main-window/{js,components}
   mkdir -p src/backend/{handlers,formatters,core,utils}
   mkdir -p src/shared/{types,constants}
   mkdir -p config scripts assets/icons
   ```

2. **Create migration branch**
   ```bash
   git checkout -b feature/file-reorganization
   ```

3. **Run full test suite** to establish baseline
   ```bash
   python run_all_tests.py
   ```

### Phase 2: Backend Migration (30 minutes)
1. **Move Python files with git history preservation**
   ```bash
   git mv main.py src/backend/
   git mv audio_handler.py src/backend/handlers/
   git mv llm_handler.py src/backend/handlers/
   git mv transcription_handler.py src/backend/handlers/
   git mv hotkey_manager.py src/backend/handlers/
   git mv medical_text_formatter.py src/backend/formatters/
   git mv memory_monitor.py src/backend/core/
   git mv settings_manager.py src/backend/core/
   git mv utils.py src/backend/utils/
   ```

2. **Update Python imports** in all moved files
3. **Test backend functionality**

### Phase 3: Main Process Migration (20 minutes)
1. **Move main process files**
   ```bash
   git mv main.js src/main/
   git mv electron-python.js src/main/
   ```

2. **Update require paths** in main process files
3. **Update package.json main entry point**

### Phase 4: Renderer Migration (45 minutes)
1. **Move main window files**
   ```bash
   git mv index.html src/renderer/main-window/
   git mv style.css src/renderer/main-window/
   git mv renderer_*.js src/renderer/main-window/js/
   ```

2. **Move proofing window files**
   ```bash
   git mv proofing.html src/renderer/proofing-window/
   git mv proofing.js src/renderer/proofing-window/
   ```

3. **Move shared renderer utilities**
   ```bash
   git mv text_processing_utils.js src/renderer/shared/
   ```

4. **Update all import/require paths** in renderer files
5. **Update HTML script/link references**

### Phase 5: Configuration Migration (15 minutes)
1. **Move configuration files**
   ```bash
   git mv config.py config/
   git mv user_settings.json config/ (if exists)
   ```

2. **Update configuration paths** in all files that reference them

### Phase 6: Testing & Validation (30 minutes)
1. **Run comprehensive test suite**
   ```bash
   python run_all_tests.py
   ```

2. **Manual testing checklist**:
   - [ ] Application starts successfully
   - [ ] Audio processing works
   - [ ] Wake word detection functions
   - [ ] Dictation workflow complete
   - [ ] Proofing window opens and functions
   - [ ] Settings load/save correctly
   - [ ] All hotkeys work
   - [ ] Microphone conflict detection active

3. **Fix any broken paths or imports**

### Phase 7: Build Configuration Updates (20 minutes)
1. **Update package.json**
   - Main entry point
   - Build scripts
   - File paths

2. **Update any bundler/build tool configs**
3. **Test build process**

## 📋 File Movement Mapping

| Current Location | New Location | Notes |
|------------------|--------------|-------|
| `main.py` | `src/backend/main.py` | Backend entry point |
| `main.js` | `src/main/main.js` | Electron main entry |
| `index.html` | `src/renderer/main-window/index.html` | Main UI |
| `style.css` | `src/renderer/main-window/style.css` | Main styles |
| `proofing.html` | `src/renderer/proofing-window/proofing.html` | Proofing UI |
| `proofing.js` | `src/renderer/proofing-window/proofing.js` | Proofing logic |
| `renderer_*.js` | `src/renderer/main-window/js/` | Renderer scripts |
| `*_handler.py` | `src/backend/handlers/` | Backend handlers |
| `config.py` | `config/config.py` | Configuration |
| `text_processing_utils.js` | `src/renderer/shared/` | Shared utilities |

## ⚠️ Risk Assessment & Mitigation

### High Risk Areas
1. **Import path updates** - Many files import from each other
   - **Mitigation**: Systematic approach, test after each subsystem
   - **Rollback**: Git history preservation allows easy revert

2. **Electron build process** - Main/renderer entry points change
   - **Mitigation**: Update package.json and test build immediately
   - **Rollback**: Keep original package.json as backup

3. **Python module imports** - Backend files import each other
   - **Mitigation**: Use relative imports where possible
   - **Rollback**: Systematic testing of backend functionality

### Medium Risk Areas
1. **Test file paths** - Tests may reference old paths
   - **Mitigation**: Run tests after each phase
   - **Fix**: Update test imports and file references

2. **Asset references** - HTML/CSS may reference assets
   - **Mitigation**: Inventory all asset references first
   - **Fix**: Update paths systematically

## 🎁 Benefits After Reorganization

### Developer Experience
- **Faster orientation** for new developers
- **Clear separation** of frontend/backend concerns
- **Easier feature development** with logical file groupings
- **Better IDE support** with proper directory structure

### Maintainability
- **Reduced cognitive load** when finding files
- **Easier refactoring** with clear boundaries
- **Better code organization** follows industry standards
- **Scalable structure** for future growth

### Build & Deployment
- **Improved bundling** opportunities
- **Better tree-shaking** for smaller builds
- **Clearer asset management**
- **Professional project structure**

## 📝 Post-Migration Tasks

1. **Update documentation** to reflect new structure
2. **Add README files** to each major directory explaining purpose
3. **Create developer onboarding guide** referencing new structure
4. **Update .cursorrules** with new directory guidelines
5. **Consider adding** `tsconfig.json` for better TypeScript support

## 🕒 Estimated Timeline

- **Total time**: ~3 hours
- **Can be done incrementally** over multiple sessions
- **Each phase is testable** individually
- **Rollback possible** at any point

## ✅ Success Criteria

- [ ] All tests pass after reorganization
- [ ] Application functions identically to before
- [ ] Git history preserved for all moved files
- [ ] Build process works without modification
- [ ] New directory structure is intuitive and logical
- [ ] Import/export paths are clean and consistent

---

*This plan will be executed when ready, ensuring zero functionality regression while dramatically improving code organization and maintainability.* 