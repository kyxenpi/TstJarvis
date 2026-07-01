import time
import re
from typing import Generator
from groq import Groq
from config import settings
from core.logger import setup_logger

logger = setup_logger("ModelManager")

class ModelManager:
    def __init__(self) -> None:
        self.client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

    def _clean_messages(self, messages: list) -> list:
        cleaned = []
        for msg in messages:
            content = msg.get("content", "")
            if content and "Resultado da ferramenta" in content:
                content = re.sub(r'\(ID: [a-zA-Z0-9_@\.-]+\)', '', content)
            cleaned.append({"role": msg["role"], "content": content})
        return cleaned

    def execute_completion(self, messages: list, temperature: float = 0.0) -> str:
        if not self.client:
            raise Exception("Chave Groq API não configurada.")

        cleaned = self._clean_messages(messages)
        try:
            response = self.client.chat.completions.create(
                model=settings.MODEL_PRIMARY,
                messages=cleaned,
                temperature=temperature,
                timeout=settings.DEFAULT_TIMEOUT
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Falha no modelo primário ({settings.MODEL_PRIMARY}): {e}. Tentando fallback...")
            try:
                print(f"🔄 [FALLBACK] Disparando modelo secundário: {settings.MODEL_SECONDARY}...")
                time.sleep(1)
                response = self.client.chat.completions.create(
                    model=settings.MODEL_SECONDARY,
                    messages=cleaned,
                    temperature=temperature,
                    timeout=settings.DEFAULT_TIMEOUT
                )
                return response.choices[0].message.content
            except Exception as critical_err:
                print(f"❌ [APOCALYPSE ERROR] O motor secundário também falhou: {critical_err}")
                logger.error(f"Erro crítico em ambos os modelos: {critical_err}")
                raise Exception("Todos os motores de IA estão indisponíveis ou com limite excedido no momento.")

    def stream_completion(self, messages: list, temperature: float = 0.0) -> Generator[str, None, None]:
        if not self.client:
            raise Exception("Chave Groq API não configurada.")

        cleaned = self._clean_messages(messages)

        def _stream(model: str):
            stream = self.client.chat.completions.create(
                model=model,
                messages=cleaned,
                temperature=temperature,
                timeout=settings.DEFAULT_TIMEOUT,
                stream=True
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content

        used_fallback = False
        try:
            yield from _stream(settings.MODEL_PRIMARY)
        except Exception as e:
            logger.warning(f"Falha no stream primário ({settings.MODEL_PRIMARY}): {e}. Tentando fallback...")
            used_fallback = True

        if used_fallback:
            try:
                print(f"🔄 [FALLBACK STREAM] Disparando modelo secundário: {settings.MODEL_SECONDARY}...")
                time.sleep(1)
                yield from _stream(settings.MODEL_SECONDARY)
            except Exception as critical_err:
                print(f"❌ [APOCALYPSE ERROR] Stream secundário também falhou: {critical_err}")
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
