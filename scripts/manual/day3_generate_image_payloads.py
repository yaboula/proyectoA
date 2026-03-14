import base64
import io
import json

from PIL import Image


def make_png_b64() -> str:
    img = Image.new("RGB", (2, 2), color=(20, 120, 220))
    out = io.BytesIO()
    img.save(out, format="PNG")
    return base64.b64encode(out.getvalue()).decode("ascii")


def make_jpg_b64() -> str:
    img = Image.new("RGB", (2, 2), color=(200, 80, 40))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=90)
    return base64.b64encode(out.getvalue()).decode("ascii")


def main() -> None:
    payloads = {
        "signature_png": make_png_b64(),
        "photo_jpg": make_jpg_b64(),
    }
    print(json.dumps(payloads, ensure_ascii=True))


if __name__ == "__main__":
    main()
