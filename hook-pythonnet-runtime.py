
import sys
import os

# This hook runs before any other python code in the frozen app
# Its job is to help clr_loader find Python.Runtime.dll

if getattr(sys, 'frozen', False):
    # We are in a PyInstaller bundle
    bundle_dir = sys._MEIPASS
    
    # Check if we have the DLL in the bundle root or a subdir
    dll_name = "Python.Runtime.dll"
    potential_paths = [
        os.path.join(bundle_dir, dll_name),
        os.path.join(bundle_dir, "pythonnet", "runtime", dll_name)
    ]
    
    found_dll = None
    for p in potential_paths:
        if os.path.exists(p):
            found_dll = p
            break
            
    if found_dll:
        # Crucial fallback: Set the environment variable that pythonnet/clr_loader *might* check
        # Or more effectively, we can try to pre-load it?
        # Actually, pythonnet 3.0 uses clr_loader. 
        # clr_loader.get_coreclr() or similar is what eventually fails.
        
        # Strategy 1: Add directory to PATH so LoadLibrary finds it
        os.environ["PATH"] = os.path.dirname(found_dll) + os.pathsep + os.environ["PATH"]
        
        # Strategy 2: Set PYTHONNET_PYDLL environment variable (used by some loader versions)
        os.environ["PYTHONNET_PYDLL"] = found_dll
        
        # Strategy 3: Explicitly set the location for pythonnet if it supports it
        # (Older versions did, 3.0 relies on clr_loader finding it)
        
    else:
        # Log this failure? We can't easily log here unless we setup logging again
        pass
