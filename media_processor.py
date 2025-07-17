
import subprocess, tempfile, json, os
from PIL import Image
import pytesseract
from utils import has_goyda

# ---- Voice ----
def voice_to_text(ogg_path: str) -> str:
    wav_path = tempfile.mktemp(suffix=".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", wav_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    # vosk
    result_json = subprocess.check_output(
        ["vosk-transcriber", "-m", "vosk-model-small-ru", wav_path, "--json"]
    )
    os.remove(wav_path)
    data = json.loads(result_json)
    return " ".join(seg["text"] for seg in data.get("segments", []))

def detect_goyda_in_voice(ogg_path: str) -> bool:
    return has_goyda(voice_to_text(ogg_path))

# ---- OCR ----
def image_to_text(img_path: str) -> str:
    img = Image.open(img_path)
    return pytesseract.image_to_string(img, lang="rus+eng")

def detect_goyda_in_image(img_path: str) -> bool:
    return has_goyda(image_to_text(img_path))
