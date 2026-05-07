import os
import shutil
import uuid
import sys
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
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

@app.get("/api/translations")
async def get_translations():
    pairs_dict = {}
    for src, tgt in fw_srt.TRANSLATION_PAIRS:
        if src not in pairs_dict:
            pairs_dict[src] = []
        pairs_dict[src].append(tgt)
    # Map Swiss German (gsw) to same options as German
    if 'de' in pairs_dict:
        pairs_dict['gsw'] = pairs_dict['de']
    return pairs_dict


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(None),
    file_path: str = Form(None),
    model: str = Form("large-v3-turbo"),
    lang: str = Form(None),
    offset: str = Form(""),
    device: str = Form("cpu"),
    compute_type: str = Form("int8"),
    translate_to: str = Form(None)
):
    try:
        logging.info(f"Received transcription request. Model={model}")
        
        temp_filename = None
        
        # Determine source: Direct path or Uploaded file
        if file_path and os.path.exists(file_path):
            if os.environ.get("DESKTOP_MODE") != "1":
                return JSONResponse(status_code=403, content={"type": "error", "message": "Direct file paths are only allowed in Desktop mode."})
            logging.info(f"Using local file path: {file_path}")
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
        return JSONResponse(status_code=400, content={"type": "error", "message": f"Failed to setup transcription: {str(e)}"})

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
                compute_type=compute_type,
                translate_to=translate_to if translate_to else None
            )
            
            for item in generator:
                if item["type"] == "complete":
                    # Send the download URL with the original filename as a query param
                    generated_filename = os.path.basename(item["path"])
                    original_name = os.path.basename(file_path) if file_path else file.filename
                    original_srt_name = os.path.splitext(original_name)[0] + ".srt"
                    
                    result = {"type": "complete", "url": f"/download/{generated_filename}?download_name={original_srt_name}"}
                    
                    # Include translated file URL if available
                    if "translated_path" in item:
                        trans_filename = os.path.basename(item["translated_path"])
                        trans_srt_name = os.path.splitext(original_name)[0] + f"_{translate_to}.srt"
                        result["translated_url"] = f"/download/{trans_filename}?download_name={trans_srt_name}"
                    
                    yield json.dumps(result) + "\n"
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
