import os
import sys
import logging
import traceback

# Setup logging immediately to catch import errors
log_file = os.path.join(os.path.expanduser("~"), "captionary_debug.log")
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Global exception hook to catch crashes
def exception_hook(exc_type, exc_value, exc_traceback):
    logging.critical("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = exception_hook

logging.info("Starting up - Phase 1: Imports")

try:
    import threading
    import time
    import uvicorn
    import webview
    # Delay app import to ensure logging is active
    from app import app
    logging.info("Imports successful")
except Exception as e:
    logging.critical(f"Failed to import dependencies: {e}", exc_info=True)
    # Ensure usage of exception hook or manual msgbox
    sys.excepthook(type(e), e, e.__traceback__)
    sys.exit(1)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        path = None
        if hasattr(sys, '_MEIPASS'):
            path = os.path.join(sys._MEIPASS, relative_path)
            logging.debug(f"MEIPASS found: {sys._MEIPASS}")
        elif getattr(sys, 'frozen', False):
            # Onedir mode: resources are usually next to the executable
            base = os.path.dirname(sys.executable)
            path = os.path.join(base, relative_path)
            logging.debug(f"Frozen mode: {base}")
        else:
            path = os.path.join(os.path.abspath("."), relative_path)
            logging.debug(f"Dev mode: {os.path.abspath('.')}")
        
        logging.debug(f"Resolved {relative_path} to {path}")
        return path
    except Exception as e:
        logging.error(f"Error resolving path: {e}")
        return relative_path

def setup_environment():
    """ Configure environment to use bundled ffmpeg """
    ffmpeg_name = 'ffmpeg'
    
    ffmpeg_path = resource_path(ffmpeg_name)
    
    # Check if in standard location, or MacOS Frameworks (common for .app bundles)
    if not os.path.exists(ffmpeg_path) and sys.platform == 'darwin' and getattr(sys, 'frozen', False):
         # Try looking in ../Frameworks/ (relative to MacOS/Executable)
         # sys.executable is .../Contents/MacOS/Captionary
         # Frameworks is .../Contents/Frameworks/
         frameworks_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", "Frameworks", ffmpeg_name))
         if os.path.exists(frameworks_path):
             ffmpeg_path = frameworks_path

    if os.path.exists(ffmpeg_path):
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]
        print(f"Added bundled ffmpeg to PATH: {ffmpeg_dir}")

def start_server(host, port):
    """ Start the Uvicorn server """
    try:
        logging.info(f"Attempting to start server on {host}:{port}")
        uvicorn.run(app, host=host, port=port, log_level="error")
    except Exception as e:
        logging.critical(f"Server crashed: {e}", exc_info=True)

class JSApi:
    def save_file(self, content, filename):
        try:
            file_types = ('Subtitle Files (*.srt)', 'All files (*.*)')
            # webview.windows[0] might not be ready if called too early, but here window exists
            result = webview.windows[0].create_file_dialog(webview.SAVE_DIALOG, save_filename=filename, file_types=file_types)
            if result:
                # result is the path string
                with open(result, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
        except Exception as e:
            logging.error(f"Error saving file: {e}")
        return False

    def pick_file(self):
        try:
            file_types = ('Media Files (*.mp4;*.mp3;*.wav;*.mkv;*.mov;*.avi;*.flac;*.ogg;*.webm;*.m4a)', 'All files (*.*)')
            result = webview.windows[0].create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
            if result:
                return result[0] # Returns a tuple/list
        except Exception as e:
            logging.error(f"Error picking file: {e}")
        return None

import multiprocessing
import socket
import urllib.request

if __name__ == "__main__":
    multiprocessing.freeze_support()
    setup_environment()
    
    # Signal to app.py that it is running via local desktop wrapper
    os.environ["DESKTOP_MODE"] = "1"
    
    HOST = "127.0.0.1"
    
    # Find an open port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, 0))
    PORT = s.getsockname()[1]
    s.close()
    
    URL = f"http://{HOST}:{PORT}"
    
    # Start server in a Daemon thread so it closes when main thread closes
    t = threading.Thread(target=start_server, args=(HOST, PORT))
    t.daemon = True
    t.start()
    
    # Wait for server to be ready
    for _ in range(50):
        try:
            req = urllib.request.urlopen(URL)
            if req.getcode() == 200:
                break
        except Exception:
            time.sleep(0.1)
    
    api = JSApi()
    # Create the native window
    webview.create_window('Captionary', URL, width=1024, height=768, js_api=api)
    webview.start()
