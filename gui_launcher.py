import os
import sys
import threading
import uvicorn
import webview
from app import app
import time
import logging

# Setup logging to file
log_file = os.path.join(os.path.expanduser("~"), "captionary_debug.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.info("Starting up...")

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
    if sys.platform.startswith('win'):
        ffmpeg_name = 'ffmpeg.exe'
    else:
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

if __name__ == "__main__":
    multiprocessing.freeze_support()
    setup_environment()
    
    HOST = "127.0.0.1"
    PORT = 8000
    URL = f"http://{HOST}:{PORT}"
    
    # Start server in a Daemon thread so it closes when main thread closes
    t = threading.Thread(target=start_server, args=(HOST, PORT))
    t.daemon = True
    t.start()
    
    # Give server a moment to start
    time.sleep(1)
    
    api = JSApi()
    # Create the native window
    webview.create_window('Captionary', URL, width=1024, height=768, js_api=api)
    webview.start()
