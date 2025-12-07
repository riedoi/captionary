import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
import json
from fastapi.responses import FileResponse, StreamingResponse
import fw_srt

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

@app.get("/download/{filename}")
async def download_file(filename: str, background_tasks: BackgroundTasks, download_name: str = None):
    file_path = os.path.join(os.getcwd(), filename)
    if os.path.exists(file_path):
        # Default to the filename on disk if no custom name is provided
        display_name = download_name if download_name else filename
        
        # Schedule file deletion after the response is sent
        background_tasks.add_task(os.remove, file_path)
        
        return FileResponse(file_path, filename=display_name, media_type="application/x-subrip")
    return {"error": "File not found"}

@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    model: str = Form("medium"),
    lang: str = Form(None),
    offset: str = Form(""),
    device: str = Form("cpu"),
    compute_type: str = Form("int8")
):
    # Save uploaded file temporarily using a unique ID
    file_ext = os.path.splitext(file.filename)[1]
    file_id = str(uuid.uuid4())
    temp_filename = f"{file_id}{file_ext}"
    
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    async def event_generator():
        try:
            # Run transcription
            generator = fw_srt.transcribe_file(
                temp_filename,
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
                    original_srt_name = os.path.splitext(file.filename)[0] + ".srt"
                    yield json.dumps({"type": "complete", "url": f"/download/{generated_filename}?download_name={original_srt_name}"}) + "\n"
                else:
                    yield json.dumps(item) + "\n"
                    
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"
        finally:
            # Cleanup uploaded file
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
