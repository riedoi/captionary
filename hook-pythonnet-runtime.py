
import sys
import os

# This hook runs before any other python code in the frozen app
# Its job is to help clr_loader find Python.Runtime.dll

if getattr(sys, 'frozen', False):
    # We are in a PyInstaller bundle
    bundle_dir = sys._MEIPASS
    
    # Check if we have the DLL in the bundle root or a subdir
    dll_name = "Python.Runtime.dll"
    # [FIX] Aggressively find the Python DLL (e.g. python310.dll) in the bundle root
    # pythonnet needs this to initialize the Python engine from C# side
    python_dll = None
    for file in os.listdir(bundle_dir):
        if file.lower().startswith("python") and file.lower().endswith(".dll") and "runtime" not in file.lower():
            python_dll = os.path.join(bundle_dir, file)
            break
            
    if python_dll:
        os.environ["PYTHONNET_PYDLL"] = python_dll
        # Also add bundle dir to PATH just in case
        os.environ["PATH"] = bundle_dir + os.pathsep + os.environ["PATH"]
    
    # Also help find Python.Runtime.dll which defines the Loader
    dll_name = "Python.Runtime.dll"
    potential_paths = [
        os.path.join(bundle_dir, dll_name),
        os.path.join(bundle_dir, "pythonnet", "runtime", dll_name)
    ]
    
    found_runtime_dll = None
    for p in potential_paths:
        if os.path.exists(p):
            found_runtime_dll = p
            break

    if found_runtime_dll:
        # Some loaders verify this
        os.environ["PYTHONNET_RUNTIME_DLL"] = found_runtime_dll 
