import os
import sys
import shutil
import urllib.request
import zipfile
import tarfile
import ssl

# Bypass SSL check for some legacy python environments if needed, generally good practice to have context
ssl._create_default_https_context = ssl._create_unverified_context

def download_file(url, target_path):
    print(f"Downloading {url}...")
    with urllib.request.urlopen(url) as response, open(target_path, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    print("Download complete.")

def extract_ffmpeg(archive_path, extract_to="."):
    print(f"Extracting {archive_path}...")
    
    if archive_path.endswith('.zip'):
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            # zip_ref.extractall(extract_to) 
            # We need to find the ffmpeg.exe inside
            for member in zip_ref.namelist():
                if member.endswith('ffmpeg.exe'):
                    source = zip_ref.open(member)
                    target = open(os.path.join(extract_to, 'ffmpeg.exe'), "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)
                    print("Extracted ffmpeg.exe")
                    
    elif archive_path.endswith('.7z') or archive_path.endswith('.dmg'):
        print("Complex archive format, please use .zip or .tar.gz sources")
        
    else: # tar.gz, tar.xz etc (Mac/Linux)
        # Python's tarfile module handles .tar.gz, .tgz, .tar.xz (if lzma module present)
        try:
            with tarfile.open(archive_path, "r:*") as tar:
                for member in tar.getmembers():
                    if member.name.endswith('/ffmpeg') or member.name == 'ffmpeg':
                        member.name = os.path.basename(member.name) # flattened
                        tar.extract(member, path=extract_to)
                        print("Extracted ffmpeg")
                        # Make executable
                        os.chmod(os.path.join(extract_to, 'ffmpeg'), 0o755)
        except Exception as e:
            print(f"Error extracting tar: {e}")

def main():
    # URLs for static builds
    # Windows: Gyan.dev (git-master)
    WIN_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    
    # Mac: Evermeet.cx (ffmpeg-109638-g2c5a7... is specific, stick to 'ffmpeg-latest.zip' equivalent? 
    # Evermeet 404s sometimes. 
    # Let's use the reliable builds from 'osxexperts' or just 'evermeet' static link.
    # Actually evermeet.cx is the standard. https://evermeet.cx/ffmpeg/ffmpeg-6.0.zip
    MAC_URL = "https://evermeet.cx/ffmpeg/ffmpeg-6.0.zip" 

    target_dir = os.getcwd()
    
    if sys.platform.startswith('win'):
        print("Detected Windows.")
        archive_name = "ffmpeg-release-essentials.zip"
        download_file(WIN_URL, archive_name)
        extract_ffmpeg(archive_name, target_dir)
        os.remove(archive_name)
        
    elif sys.platform.startswith('darwin'):
        print("Detected macOS.")
        archive_name = "ffmpeg-mac.zip"
        download_file(MAC_URL, archive_name)
        
        # Evermeet zip contains just the binary usually
        with zipfile.ZipFile(archive_name, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
            
        # Ensure executable
        if os.path.exists("ffmpeg"):
            os.chmod("ffmpeg", 0o755)
            print("Extracted ffmpeg")
            
        os.remove(archive_name)
        
    else:
        print("Linux/Other not strictly supported by this specific script currently for bundling.")

if __name__ == "__main__":
    main()
