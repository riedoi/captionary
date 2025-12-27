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
        "clr" # Windows specific for pythonnet but harmless to list here? actually might error if not found. Let's be minimal.
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
        
        # MacOS Specifics
        "--osx-bundle-identifier=com.riedoi.captionary",
        
        # Collect all explicit faster-whisper data just in case
        "--collect-all=faster_whisper",
        
        "gui_launcher.py"
    ]
    
    for imp in hidden_imports:
        cmd.append(f"--hidden-import={imp}")
        
    # Additional hooks or options could go here
    
    print(f"Running command: {' '.join(cmd)}")
    subprocess.check_call(cmd)

if __name__ == "__main__":
    build()
