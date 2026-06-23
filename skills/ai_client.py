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
from skills.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class BaseAIClient(ABC):
    def __init__(self, rate_limit: int = 15, use_few_shot: bool = False):
        self.rate_limit = rate_limit
        self.use_few_shot = use_few_shot
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

    def _process_response(
        self, raw: str, file_name: str
    ) -> Dict[str, Any]:
        try:
            data = self._parse_json_response(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("JSON inválido retornado pela IA: %s", e)
            return PromptBuilder.fallback_from_filename(file_name)

        valid, errors = PromptBuilder.validate_response(data)
        if valid:
            return data

        logger.info("Campos a reparar na resposta da IA: %s", errors)
        return PromptBuilder.repair_partial_response(data, file_name)


class CloudAIClient(BaseAIClient):
    def __init__(
        self,
        provider: str = "openai",
        api_key: str = "",
        model: str = "",
        rate_limit: int = 15,
        use_few_shot: bool = False,
    ):
        super().__init__(rate_limit, use_few_shot)
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
        system = PromptBuilder.build_system_prompt(include_few_shot=self.use_few_shot)

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": PromptBuilder.build_user_message(file_name),
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
        return self._process_response(raw, file_name)

    def _analyze_google(self, gif_path: Path, file_name: str) -> Dict[str, Any]:
        from google.genai import types

        file_ref = self._client.files.upload(file=gif_path)
        system = PromptBuilder.build_system_prompt(include_few_shot=self.use_few_shot)

        response = self._client.models.generate_content(
            model=self.model,
            contents=[
                system,
                PromptBuilder.build_user_message(file_name),
                file_ref,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return self._process_response(response.text, file_name)


class LocalAIClient(BaseAIClient):
    def __init__(
        self,
        api_url: str = "http://localhost:11434/v1/chat/completions",
        model: str = "llama3.2-vision",
        rate_limit: int = 15,
        use_few_shot: bool = False,
    ):
        super().__init__(rate_limit, use_few_shot)
        self.api_url = api_url
        self.model = model

    def analyze_exercise(self, gif_path: Path, file_name: str) -> Dict[str, Any]:
        self._wait_rate_limit()

        frames: List[Image.Image] = extract_gif_frames(gif_path, max_frames=3)
        content: List[Dict[str, Any]] = [
            {"type": "text", "text": PromptBuilder.build_user_message(file_name)}
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

        system = PromptBuilder.build_system_prompt(include_few_shot=self.use_few_shot)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
        }

        with httpx.Client(timeout=120) as client:
            resp = client.post(self.api_url, json=payload)
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]

        return self._process_response(raw, file_name)


def create_ai_client() -> BaseAIClient:
    mode = os.getenv("AI_MODE", "cloud").lower()
    rate_limit = int(os.getenv("AI_RATE_LIMIT", "15"))
    use_few_shot = os.getenv("AI_USE_FEW_SHOT", "false").lower() == "true"

    if mode == "cloud":
        provider = os.getenv("AI_PROVIDER", "openai").lower()
        if provider == "openai":
            return CloudAIClient(
                provider="openai",
                api_key=os.getenv("OPENAI_API_KEY", ""),
                model=os.getenv("AI_MODEL", ""),
                rate_limit=rate_limit,
                use_few_shot=use_few_shot,
            )
        elif provider == "google":
            return CloudAIClient(
                provider="google",
                api_key=os.getenv("GOOGLE_API_KEY", ""),
                model=os.getenv("AI_MODEL", ""),
                rate_limit=rate_limit,
                use_few_shot=use_few_shot,
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
            use_few_shot=use_few_shot,
        )

    else:
        raise ValueError(f"AI_MODE inválido: {mode}. Use 'cloud' ou 'local'.")
