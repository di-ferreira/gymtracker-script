import base64
import io
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List

import httpx
from PIL import Image

from skills.media_processor import extract_gif_frames

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um especialista em biomecânica, cinesiologia e exercícios físicos.
Sua função é analisar imagens/GIFs de exercícios e retornar informações estruturadas.

Analise o GIF (ou seus frames) e o nome do arquivo para identificar o exercício.
Retorna APENAS um objeto JSON válido, sem markdown, sem comentários, sem texto extra:

{
  "nome_exercicio": "Nome padronizado e comercial do exercício em português",
  "grupo_muscular": "Descreva os músculos principais e secundários ativados",
  "modo_execucao": "Passo a passo detalhado de como realizar o movimento corretamente",
  "dicas_seguranca": "Alertas sobre postura, erros comuns a evitar e recomendações de segurança",
  "tags": ["tag1", "tag2", "tag3"]
}

Use tags relevantes como: pernas, costas, peito, ombros, braços, abdomen, gluteos,
quadriceps, posterior, costa, superior, inferior, fullbody, hipertrofia, resistencia,
calistenia, funcional, maquina, halteres, barra, cabo, elastico, smith, casa, academia,
basico, intermediario, avancado."""


class BaseAIClient(ABC):
    def __init__(self, rate_limit: int = 15):
        self.rate_limit = rate_limit
        self._last_call_time = 0.0
        self._min_interval = 60.0 / max(rate_limit, 1)

    def _wait_rate_limit(self) -> None:
        elapsed = time.time() - self._last_call_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call_time = time.time()

    @abstractmethod
    def analyze_exercise(self, gif_path: Path, file_name: str) -> Dict[str, Any]:
        ...

    @staticmethod
    def _parse_json_response(raw: str) -> Dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start : end + 1]
        return json.loads(text)


class CloudAIClient(BaseAIClient):
    def __init__(
        self,
        provider: str = "openai",
        api_key: str = "",
        model: str = "",
        rate_limit: int = 15,
    ):
        super().__init__(rate_limit)
        self.provider = provider.lower()
        self.api_key = api_key

        if self.provider == "openai":
            import openai
            self._client = openai.OpenAI(api_key=api_key)
            self.model = model or "gpt-4o"
        elif self.provider == "google":
            from google import genai
            self._client = genai.Client(api_key=api_key)
            self.model = model or "gemini-2.5-flash"
        else:
            raise ValueError(f"Provedor cloud inválido: {self.provider}")

    def analyze_exercise(self, gif_path: Path, file_name: str) -> Dict[str, Any]:
        self._wait_rate_limit()
        if self.provider == "openai":
            return self._analyze_openai(gif_path, file_name)
        return self._analyze_google(gif_path, file_name)

    def _analyze_openai(self, gif_path: Path, file_name: str) -> Dict[str, Any]:
        with open(gif_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        data_url = f"data:image/gif;base64,{b64}"

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Analise o exercício no arquivo: {file_name}",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                    ],
                },
            ],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        return self._parse_json_response(raw)

    def _analyze_google(self, gif_path: Path, file_name: str) -> Dict[str, Any]:
        from google.genai import types

        file_ref = self._client.files.upload(file=gif_path)

        response = self._client.models.generate_content(
            model=self.model,
            contents=[
                SYSTEM_PROMPT,
                f"Analise o exercício no arquivo: {file_name}",
                file_ref,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return self._parse_json_response(response.text)


class LocalAIClient(BaseAIClient):
    def __init__(
        self,
        api_url: str = "http://localhost:11434/v1/chat/completions",
        model: str = "llama3.2-vision",
        rate_limit: int = 15,
    ):
        super().__init__(rate_limit)
        self.api_url = api_url
        self.model = model

    def analyze_exercise(self, gif_path: Path, file_name: str) -> Dict[str, Any]:
        self._wait_rate_limit()

        frames: List[Image.Image] = extract_gif_frames(gif_path, max_frames=3)
        content: List[Dict[str, Any]] = [
            {"type": "text", "text": f"Analise o exercício no arquivo: {file_name}"}
        ]

        for frame in frames:
            buf = io.BytesIO()
            frame.save(buf, format="JPEG", quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                }
            )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
        }

        with httpx.Client(timeout=120) as client:
            resp = client.post(self.api_url, json=payload)
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]

        return self._parse_json_response(raw)


def create_ai_client() -> BaseAIClient:
    mode = os.getenv("AI_MODE", "cloud").lower()
    rate_limit = int(os.getenv("AI_RATE_LIMIT", "15"))

    if mode == "cloud":
        provider = os.getenv("AI_PROVIDER", "openai").lower()
        if provider == "openai":
            return CloudAIClient(
                provider="openai",
                api_key=os.getenv("OPENAI_API_KEY", ""),
                model=os.getenv("AI_MODEL", ""),
                rate_limit=rate_limit,
            )
        elif provider == "google":
            return CloudAIClient(
                provider="google",
                api_key=os.getenv("GOOGLE_API_KEY", ""),
                model=os.getenv("AI_MODEL", ""),
                rate_limit=rate_limit,
            )
        else:
            raise ValueError(f"AI_PROVIDER inválido: {provider}")

    elif mode == "local":
        return LocalAIClient(
            api_url=os.getenv(
                "LOCAL_API_URL", "http://localhost:11434/v1/chat/completions"
            ),
            model=os.getenv("LOCAL_MODEL", "llama3.2-vision"),
            rate_limit=rate_limit,
        )

    else:
        raise ValueError(f"AI_MODE inválido: {mode}. Use 'cloud' ou 'local'.")
