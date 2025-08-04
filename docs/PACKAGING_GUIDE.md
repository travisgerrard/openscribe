# 📦 CitrixTranscriber Packaging Guide

This guide explains how to package CitrixTranscriber into a single distributable file that users can easily install and run.

## 🎯 **Goal**

Create a **single DMG installer** that contains everything needed to run CitrixTranscriber on any macOS system, without requiring:
- Python installation
- Node.js installation  
- Complex setup procedures
- Technical knowledge

## 🏗️ **Packaging Architecture**

### **Two-Stage Build Process**

1. **Stage 1: Python Backend** 
   - PyInstaller bundles Python + dependencies into standalone executable
   - Includes: Vosk, MLX, all Python libraries
   - Output: `CitrixTranscriberBackend.app`

2. **Stage 2: Electron Frontend**
   - Electron Builder packages frontend + Python backend
   - Creates macOS app bundle and DMG installer
   - Output: `Citrix Transcriber.dmg`

## 🚀 **Quick Start**

### **Automated Build (Recommended)**

```bash
# Run the complete build process
./build.sh
```

That's it! The script handles everything automatically.

### **Manual Build (Advanced)**

```bash
# 1. Build Python backend
npm run build:python

# 2. Build Electron app
npm run build:electron

# 3. Or build both
npm run build
```

## 📋 **Prerequisites**

### **Development Environment**
- macOS (for building macOS apps)
- Python 3.12+ with virtual environment activated
- Node.js 18+ with npm
- All project dependencies installed

### **Required Tools**
- PyInstaller (installed automatically)
- Electron Builder (installed automatically)
- Xcode Command Line Tools

## 🔧 **Build Configuration**

### **PyInstaller Configuration** (`build_backend.spec`)
- Bundles Python backend into standalone executable
- Includes all required libraries (Vosk, MLX, etc.)
- Handles model files and configuration
- Creates macOS app bundle with proper permissions

### **Electron Builder Configuration** (`package.json`)
- Packages Electron frontend with Python backend
- Creates DMG installer with drag-to-install interface
- Handles code signing and notarization settings
- Configures app permissions and entitlements

## 📁 **Build Output**

After successful build, you'll find:

```
dist/
├── CitrixTranscriberBackend.app/          # Python backend executable
├── mac/
│   └── Citrix Transcriber.app/            # Complete macOS app
└── Citrix Transcriber-1.0.0.dmg          # DMG installer
```

### **Distribution Files**

**For End Users:**
- `Citrix Transcriber-1.0.0.dmg` - **This is what you share!**

**For Development:**
- `mac/Citrix Transcriber.app/` - App bundle for testing

## 👥 **End User Installation**

### **Installation Process**
1. Download `Citrix Transcriber-1.0.0.dmg`
2. Double-click to mount the DMG
3. Drag "Citrix Transcriber" to Applications folder
4. Eject the DMG
5. Launch from Applications

### **First Run**
- macOS will ask for microphone permission (required)
- macOS will ask for accessibility permission (required for hotkeys)
- App will download models on first use (requires internet)
- No other setup needed!

## 🔒 **Code Signing & Security**

### **Development Builds**
- Uses ad-hoc signing (works on developer machine)
- May show security warnings on other machines

### **Distribution Builds** (Future Enhancement)
- Requires Apple Developer account ($99/year)
- Code signing prevents security warnings
- Notarization allows automatic updates

## 📊 **Build Optimization**

### **Size Optimization**
- Python backend: ~200-300 MB
- Electron frontend: ~100-200 MB
- Models downloaded separately: ~500 MB - 2 GB
- **Total DMG size: ~300-500 MB**

### **Performance Optimization**
- UPX compression enabled for Python executable
- Electron packaging excludes development files
- Models cached locally after first download

## 🧪 **Testing the Build**

### **Local Testing**
```bash
# Test the built app
open "dist/mac/Citrix Transcriber.app"
```

### **Distribution Testing**
1. Copy DMG to a different Mac (or VM)
2. Install from DMG (drag to Applications)
3. Run app and test all functionality
4. Verify models download correctly
5. Test dictation workflow end-to-end

## 🐛 **Troubleshooting**

### **Common Build Issues**

**Python Backend Build Fails:**
```bash
# Check dependencies
pip list | grep -E "(vosk|mlx|pyaudio)"

# Clean rebuild
rm -rf dist/ build/
pyinstaller build_backend.spec --clean
```

**Electron Build Fails:**
```bash
# Check Node dependencies
npm audit

# Clean rebuild
rm -rf node_modules/ dist/
npm install
npm run build:electron
```

**App Won't Launch:**
- Check console logs: Console.app → search "Citrix"
- Verify entitlements.mac.plist is correct
- Ensure Python backend executable has correct permissions

### **Runtime Issues**

**Models Don't Download:**
- Check internet connection
- Verify Hugging Face Hub access
- Clear model cache: `~/Library/Application Support/CitrixTranscriber/`

**Microphone Not Working:**
- Check System Preferences → Security & Privacy → Microphone
- Ensure "Citrix Transcriber" is enabled

**Hotkeys Not Working:**
- Check System Preferences → Security & Privacy → Accessibility
- Ensure "Citrix Transcriber" is enabled

## 📈 **Advanced Configuration**

### **Custom Model Bundling**
To bundle models with the app (larger file, no download):

1. Download models to `models/` directory
2. Update `build_backend.spec` to include models
3. Modify app to use bundled models

### **Cross-Platform Builds**

**Windows:**
```bash
npm run build -- --win
```

**Linux:**
```bash
npm run build -- --linux
```

### **CI/CD Integration**
The build process can be automated with GitHub Actions or similar CI/CD systems for automatic releases.

## 🎉 **Success Criteria**

### **A Successful Build Should:**
- ✅ Create a working DMG installer
- ✅ Launch without requiring Python/Node installation
- ✅ Download models automatically on first run
- ✅ Work on clean macOS systems
- ✅ Pass all functionality tests

### **Ready for Distribution When:**
- ✅ DMG installs cleanly on test machine
- ✅ All dictation features work end-to-end
- ✅ No crashes during normal usage
- ✅ File size is reasonable (< 1 GB)
- ✅ Performance is acceptable

## 📞 **Support**

### **For Build Issues:**
1. Check this guide
2. Review build logs for errors
3. Test on clean environment
4. Check dependencies and versions

### **For Distribution Issues:**
1. Test on different macOS versions
2. Verify code signing status
3. Check app permissions and entitlements
4. Test installation process

---

**Happy Packaging! 📦✨**

*This packaging setup transforms a complex Python + Electron application into a simple drag-and-drop installer that anyone can use.* 