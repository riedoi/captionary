import os
import shutil
import uuid
import sys
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import json
import fw_srt
import logging

# Setup logging
log_file = os.path.join(os.path.expanduser("~"), "captionary_app.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info(f"App started. Python: {sys.version}")
logging.info(f"FFmpeg path: {shutil.which('ffmpeg')}")

app = FastAPI()

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    elif getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Mount static files
static_dir = resource_path("static")
if not os.path.exists(static_dir):
    # Fallback for dev mode where 'static' might be in CWD
    static_dir = "static"
    
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_index():
    index_path = os.path.join(static_dir, "index.html")
    return FileResponse(index_path)

@app.get("/download/{filename}")
async def download_file(filename: str, background_tasks: BackgroundTasks, download_name: str = None):
    file_path = os.path.join(tempfile.gettempdir(), filename)
    if os.path.exists(file_path):
        # Default to the filename on disk if no custom name is provided
        display_name = download_name if download_name else filename
        
        # Schedule file deletion after the response is sent
        background_tasks.add_task(os.remove, file_path)
        
        return FileResponse(file_path, filename=display_name, media_type="application/x-subrip")
    return {"error": "File not found"}


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(None),
    file_path: str = Form(None),
    model: str = Form("medium"),
    lang: str = Form(None),
    offset: str = Form(""),
    device: str = Form("cpu"),
    compute_type: str = Form("int8")
):
    try:
        logging.info(f"Received transcription request. Model={model}")
        
        temp_filename = None
        
        # Determine source: Direct path or Uploaded file
        if file_path and os.path.exists(file_path):
            logging.info(f"Using local file path: {file_path}")
            # We can use the file directly, but to keep logic consistent (and safe from modifying original),
            # we might just pass this path to the transcriber.
            # However, the transcriber reads from disk.
            # Let's just use this path explicitly.
            process_path = file_path
            
        elif file:
            logging.info(f"Using uploaded file: {file.filename}")
            # Save uploaded file temporarily using a unique ID in system temp dir
            file_ext = os.path.splitext(file.filename)[1]
            file_id = str(uuid.uuid4())
            
            # Use system temp directory!
            temp_dir = tempfile.gettempdir()
            temp_filename = os.path.join(temp_dir, f"{file_id}{file_ext}")
            
            logging.info(f"Saving temporary file to {temp_filename}")
            
            with open(temp_filename, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            logging.info("File saved successfully.")
            process_path = temp_filename
        else:
             return {"type": "error", "message": "No file provided."}
        
    except Exception as e:
        logging.error(f"Error saving file: {e}", exc_info=True)
        return {"type": "error", "message": f"Failed to save file: {e}"} # Return JSON error, implies 200 OK but handled by JS? 
        # Actually returning a dict here might break the expectation of StreamingResponse if JS expects stream. 
        # But if we error here, we haven't started stream. JS check for !response.ok will see 200 OK but json body? 
        # Better to return JSONResponse with status 500 or just raise HTTPException.
        # But for debug, let's just raise it after logging.
        raise e

    async def event_generator():
        try:
            logging.info("Starting transcription generator...")
            # Run transcription
            generator = fw_srt.transcribe_file(
                process_path,
                model_size=model,
                lang=lang if lang else None,
                offset_str=offset,
                device=device,
                compute_type=compute_type
            )
            
            for item in generator:
                if item["type"] == "complete":
                    # Send the download URL with the original filename as a query param
                    generated_filename = os.path.basename(item["path"])
                    original_name = os.path.basename(file_path) if file_path else file.filename
                    original_srt_name = os.path.splitext(original_name)[0] + ".srt"
                    yield json.dumps({"type": "complete", "url": f"/download/{generated_filename}?download_name={original_srt_name}"}) + "\n"
                else:
                    yield json.dumps(item) + "\n"
                    
        except Exception as e:
            logging.error(f"Transcription error: {e}", exc_info=True)
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"
        finally:
            # Cleanup only if we created a temp file (i.e. it was an upload)
            if temp_filename and os.path.exists(temp_filename):
                os.remove(temp_filename)

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
