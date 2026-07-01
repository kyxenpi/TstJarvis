import os
import warnings
import requests

OCR_API_KEY = os.environ.get("OCR_SPACE_API_KEY")
if not OCR_API_KEY:
    warnings.warn("OCR_SPACE_API_KEY não definida. OCR pode falhar.")
    OCR_API_KEY = "helloworld"


def read_image(image_input: str):
    url = "https://api.ocr.space/parse/image"

    payload = {
        'apikey': OCR_API_KEY,
        'language': 'por',
        'isOverlayRequired': False
    }

    try:
        if image_input.startswith(("http://", "https://")):
            payload['url'] = image_input
            response = requests.post(url, data=payload, timeout=30)
        else:
            if not os.path.exists(image_input):
                return {"success": False, "output": f"Arquivo não encontrado: {image_input}"}

            with open(image_input, 'rb') as image_file:
                files = {'file': image_file}
                response = requests.post(url, data=payload, files=files, timeout=30)

        result = response.json()

        if result.get("IsErroredOnProcessing"):
            return {"success": False, "output": result.get("ErrorMessage", ["Erro desconhecido"])[0]}

        parsed_results = result.get("ParsedResults", [])
        if parsed_results:
            texto = parsed_results[0].get("ParsedText", "").strip()
            if texto:
                return {"success": True, "output": texto}
            return {"success": False, "output": "Nenhum texto encontrado na imagem."}

        return {"success": False, "output": "Nenhum resultado retornado pela API."}

    except requests.Timeout:
        return {"success": False, "output": "Timeout ao processar OCR (30s)."}
    except Exception as e:
        return {"success": False, "output": f"Erro no OCR: {str(e)}"}
