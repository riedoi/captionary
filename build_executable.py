import os
import sys
import subprocess
import platform

def build():
    # 1. Define paths
    base_dir = os.getcwd()
    dist_dir = os.path.join(base_dir, "dist")
    build_dir = os.path.join(base_dir, "build")
    
    # 2. Check for dependencies
    # We expect ffmpeg to be in the root (downloaded by script)
    ffmpeg_binary = "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"
    if not os.path.exists(ffmpeg_binary):
        print(f"Error: {ffmpeg_binary} not found. Run scripts/download_ffmpeg.py first.")
        sys.exit(1)
        
    # 2.5 Generate Icons
    icon_file = None
    try:
        from PIL import Image
        img_path = os.path.join(base_dir, "static", "logo.png")
        if os.path.exists(img_path):
            img = Image.open(img_path)
            if sys.platform.startswith("win"):
                icon_file = os.path.join(base_dir, "Captionary.ico")
                img.save(icon_file, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
                print(f"Generated Windows icon: {icon_file}")
            elif sys.platform.startswith("darwin"):
                icon_file = os.path.join(base_dir, "Captionary.icns")
                # Pillow might support ICNS writing
                img.save(icon_file, format="ICNS") 
                print(f"Generated macOS icon: {icon_file}")
    except Exception as e:
        print(f"Warning: Failed to generate icon: {e}")
        # On Mac, PyInstaller might handle PNG directly in newer versions
        if sys.platform.startswith("darwin"):
             icon_file = os.path.join(base_dir, "static", "logo.png")

    # 3. Construct PyInstaller command
    app_name = "Captionary"
    
    # Hidden imports often needed for uvicorn/fastapi/engine
    hidden_imports = [
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "engineio.async_drivers.asgi",
        "faster_whisper",
        "webview",
        "clr", # Windows specific for pythonnet but harmless to list here? actually might error if not found. Let's be minimal.
        "PIL", # Ensure Pillow is available in the bundle if we used it? No, build-time only.
        "setuptools"
    ]
    
    # OS Specific hidden imports for pywebview
    if sys.platform.startswith("win"):
        hidden_imports.append("webview.platforms.winforms")
    elif sys.platform.startswith("darwin"):
        hidden_imports.append("webview.platforms.cocoa")
        
    hidden_imports.append("python-multipart")
    
    # Find faster_whisper assets
    import faster_whisper
    fw_path = os.path.dirname(faster_whisper.__file__)
    assets_path = os.path.join(fw_path, "assets")

    # [FIX] Manually locate Python.Runtime.dll and .deps.json for pythonnet/clr_loader on Windows
    python_runtime_dll = None
    python_runtime_json = None
    python_runtime_config = None
    if sys.platform.startswith("win"):
        try:
            import pythonnet
            pynet_path = os.path.dirname(pythonnet.__file__)
            # Try 3.0+ location
            dll_path = os.path.join(pynet_path, "runtime", "Python.Runtime.dll")
            json_path = os.path.join(pynet_path, "runtime", "Python.Runtime.deps.json")
            
            if os.path.exists(dll_path):
                python_runtime_dll = dll_path
            if os.path.exists(json_path):
                python_runtime_json = json_path
                
            if not python_runtime_dll:
                # Fallback search
                for root, dirs, files in os.walk(sys.prefix):
                    if "Python.Runtime.dll" in files:
                        python_runtime_dll = os.path.join(root, "Python.Runtime.dll")
                    if "Python.Runtime.deps.json" in files:
                        python_runtime_json = os.path.join(root, "Python.Runtime.deps.json")
                    if python_runtime_dll and python_runtime_json:
                        break
            
            if python_runtime_dll:
                print(f"Found Python.Runtime.dll at: {python_runtime_dll}")
            if python_runtime_json:
                 print(f"Found Python.Runtime.deps.json at: {python_runtime_json}")

            # [FIX] Also look for runtimeconfig.json (Critical for .NET 6+ initialization)
            # Usually named Python.Runtime.runtimeconfig.json
            config_path = os.path.join(pynet_path, "runtime", "Python.Runtime.runtimeconfig.json")
            if os.path.exists(config_path):
                python_runtime_config = config_path
            else:
                 # Fallback search
                 for root, dirs, files in os.walk(sys.prefix):
                    if "Python.Runtime.runtimeconfig.json" in files:
                        python_runtime_config = os.path.join(root, "Python.Runtime.runtimeconfig.json")
                        break
            
            if python_runtime_config:
                print(f"Found Python.Runtime.runtimeconfig.json at: {python_runtime_config}")

        except ImportError:
            print("Warning: pythonnet not installed in build environment?")
    
    cmd = [
        "pyinstaller",
        "--name=" + app_name,
        "--clean",
        "--onedir",
        "--windowed", # No terminal window
        # "--console", # Explicitly enable console
        # Add data files (source:dest)
        f"--add-data=static{os.pathsep}static",
        f"--add-data={assets_path}{os.pathsep}faster_whisper{os.sep}assets",
        # Add binary
        f"--add-binary={ffmpeg_binary}{os.pathsep}.",
        
        # [FIX] Add Python.Runtime.dll to pythonnet/runtime AND root to be safe
        *( [f"--add-binary={python_runtime_dll}{os.pathsep}pythonnet{os.sep}runtime"] if python_runtime_dll else [] ),
        *( [f"--add-binary={python_runtime_dll}{os.pathsep}."] if python_runtime_dll else [] ),
        # [FIX] Also add the .deps.json config file if found (common requirement for 3.0+)
        *( [f"--add-data={python_runtime_json}{os.pathsep}pythonnet{os.sep}runtime"] if python_runtime_json else [] ),
        *( [f"--add-data={python_runtime_json}{os.pathsep}."] if python_runtime_json else [] ),
        # [FIX] Add .runtimeconfig.json (Critical for .NET host policy)
        *( [f"--add-data={python_runtime_config}{os.pathsep}pythonnet{os.sep}runtime"] if python_runtime_config else [] ),
        *( [f"--add-data={python_runtime_config}{os.pathsep}."] if python_runtime_config else [] ),

        "--osx-bundle-identifier=com.riedoi.captionary",
        
        # [FIX] Runtime hook to help pythonnet find dependencies
        "--runtime-hook=hook-pythonnet-runtime.py",
        
        # Collect all explicit faster-whisper data just in case
        "--collect-all=faster_whisper",
        "--collect-all=ctranslate2",
        "--collect-all=pythonnet",
        "--collect-all=clr_loader",
        
        "gui_launcher.py"
    ]
    
    if icon_file and os.path.exists(icon_file):
        cmd.append(f"--icon={icon_file}")
    
    for imp in hidden_imports:
        cmd.append(f"--hidden-import={imp}")
        
    # Additional hooks or options could go here
    
    print(f"Running command: {' '.join(cmd)}")
    subprocess.check_call(cmd)

if __name__ == "__main__":
    build()
