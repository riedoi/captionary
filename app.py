import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form
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
async def download_file(filename: str):
    file_path = os.path.join(os.getcwd(), filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename, media_type="application/x-subrip")
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
    # Save uploaded file temporarily
    temp_filename = file.filename
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
                    # Send the download URL instead of the path
                    filename = os.path.basename(item["path"])
                    yield json.dumps({"type": "complete", "url": f"/download/{filename}"}) + "\n"
                else:
                    yield json.dumps(item) + "\n"
                    
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"
        finally:
            # Cleanup uploaded file
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
