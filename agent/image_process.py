# tools/image_process.py

import os
import requests

def read_image(image_input: str):
    """
    Processa uma imagem usando a API do OCR.Space.
    Aceita tanto um caminho de arquivo local quanto uma URL da internet.
    """
    url = "https://api.ocr.space/parse/image"
    
    # Busca a chave das variáveis de ambiente. Se não encontrar, usa 'helloworld' como padrão.
    api_key = os.environ.get("OCR_SPACE_API_KEY")
    
    payload = {
        'apikey': api_key,
        'language': 'por',  # Configurado para Português
        'isOverlayRequired': False
    }
    
    try:
        # Verifica se o input é uma URL da internet
        if image_input.startswith("http://") or image_input.startswith("https://"):
            payload['url'] = image_input
            response = requests.post(url, data=payload)
        
        # Caso contrário, trata como um arquivo local
        else:
            if not os.path.exists(image_input):
                return {
                    "success": False,
                    "output": f"Arquivo não encontrado no caminho: {image_input}"
                }
                
            with open(image_input, 'rb') as image_file:
                files = {'file': image_file}
                response = requests.post(url, data=payload, files=files)
        
        # Processa a resposta da API
        result = response.json()
        
        if result.get("IsErroredOnProcessing"):
            return {
                "success": False,
                "output": result.get("ErrorMessage")[0]
            }
            
        parsed_results = result.get("ParsedResults", [])
        if parsed_results:
            texto = parsed_results[0].get("ParsedText", "")
            return {
                "success": True,
                "output": texto
            }
        else:
            return {
                "success": False,
                "output": "Nenhum texto foi encontrado ou processado."
            }
            
    except Exception as e:
        return {
            "success": False,
            "output": f"Erro ao processar o OCR: {str(e)}"
        }

# Código de teste para quando você rodar esse arquivo diretamente
if __name__ == "__main__":
    # Teste 1: Usando a URL que você passou
    url_teste = "https://www.educlub.com.br/rails/active_storage/blobs/proxy/eyJfcmFpbHMiOnsiZGF0YSI6NDQ4MjEsInB1ciI6ImJsb2JfaWQifX0=--398fcdac6f75290503777aff68ca5e5f16f13241/Texto%20com%20si%CC%81labas%20simples%20para%20alfabetizac%CC%A7a%CC%83o%201.png"
    
    print("Testando OCR via URL...")
    resultado_url = read_image(url_teste)
    print(f"Sucesso: {resultado_url['success']}\nTexto:\n{resultado_url['output']}")
    
    # Teste 2: Se quiser testar local, basta descomentar as linhas abaixo:
    # print("\nTestando OCR via Arquivo Local...")
    # resultado_local = read_image("caminho/para/sua/imagem.png")
    # print(resultado_local)