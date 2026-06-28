import time
import re
from groq import Groq
from config import settings
from core.logger import setup_logger

logger = setup_logger("ModelManager")

class ModelManager:
    def __init__(self) -> None:
        self.client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

    def execute_completion(self, messages: list, temperature: float = 0.0) -> str:
        if not self.client:
            raise Exception("Chave Groq API não configurada.")
            
        # OTIMIZAÇÃO DE TOKENS: Remove os IDs do calendário para economizar cota diária (TPD)
        cleaned_messages = []
        for msg in messages:
            content = msg.get("content", "")
            if content and "Resultado da ferramenta" in content:
                # Remove os padrões de ID longos como (ID: e0vqdpt556b2...)
                content = re.sub(r'\(ID: [a-zA-Z0-9_@\.-]+\)', '', content)
            cleaned_messages.append({"role": msg["role"], "content": content})
            
        # Tentativa 1: Modelo Primário
        try:
            response = self.client.chat.completions.create(
                model=settings.MODEL_PRIMARY,
                messages=cleaned_messages,
                temperature=temperature,
                timeout=settings.DEFAULT_TIMEOUT
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Falha no modelo primário ({settings.MODEL_PRIMARY}): {e}. Tentando fallback...")
            
            # Tentativa 2: Fallback para Modelo Secundário
            try:
                print(f"🔄 [FALLBACK] Disparando modelo secundário: {settings.MODEL_SECONDARY}...")
                time.sleep(1) # Backoff de segurança para evitar concorrência (RPM)
                
                response = self.client.chat.completions.create(
                    model=settings.MODEL_SECONDARY,
                    messages=cleaned_messages,
                    temperature=temperature,
                    timeout=settings.DEFAULT_TIMEOUT
                )
                return response.choices[0].message.content
            except Exception as critical_err:
                print(f"❌ [APOCALYPSE ERROR] O motor secundário também falhou: {critical_err}")
                logger.error(f"Erro crítico em ambos os modelos: {critical_err}")
                raise Exception("Todos os motores de IA estão indisponíveis ou com limite excedido no momento.")
                
    def transcrever_audio(self, filename: str, audio_bytes: bytes) -> str:
        if not self.client:
            raise Exception("Groq indisponível.")
        transcricao = self.client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model="whisper-large-v3",
            response_format="json"
        )
        return transcricao.text

model_manager = ModelManager()