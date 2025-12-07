from fastapi.testclient import TestClient
from app import app
import os
import io

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"

def test_static_files():
    response = client.get("/static/style.css")
    assert response.status_code == 200

def test_download_endpoint_no_file():
    response = client.get("/download/nonexistent.srt")
    assert response.json() == {"error": "File not found"}
