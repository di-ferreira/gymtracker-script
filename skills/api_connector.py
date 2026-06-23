import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_RATE_LIMITER: Dict[str, float] = {}
_MIN_INTERVAL: float = 2.0


def _rate_limit(endpoint_key: str) -> None:
    last = _RATE_LIMITER.get(endpoint_key, 0.0)
    elapsed = time.time() - last
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _RATE_LIMITER[endpoint_key] = time.time()


def api_login(base_url: str, email: str, password: str) -> str:
    url = f"{base_url.rstrip('/')}/api/v1/auth/login"
    _rate_limit("login")
    resp = httpx.post(url, json={"email": email, "password": password}, timeout=15)
    resp.raise_for_status()
    token = resp.json()["access_token"]
    logger.info("Autenticação na API realizada com sucesso")
    return token


def api_get_muscle_groups(base_url: str, token: str) -> List[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/v1/admin/catalog/muscle-groups/"
    headers = {"Authorization": f"Bearer {token}"}
    _rate_limit("muscle_groups")
    resp = httpx.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data: List[Dict[str, Any]] = resp.json()
    logger.info("Grupos musculares carregados: %d registros", len(data))
    return data


def api_get_movement_groups(base_url: str, token: str) -> List[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/v1/admin/catalog/movement-groups/"
    headers = {"Authorization": f"Bearer {token}"}
    _rate_limit("movement_groups")
    resp = httpx.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data: List[Dict[str, Any]] = resp.json()
    logger.info("Grupos de movimento carregados: %d registros", len(data))
    return data


def api_upload_media(
    base_url: str,
    token: str,
    file_path: Path,
    folder: str = "exercises",
) -> str:
    url = f"{base_url.rstrip('/')}/api/v1/admin/media/upload?folder={folder}"
    headers = {"Authorization": f"Bearer {token}"}
    _rate_limit("upload")

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "image/gif")}
        resp = httpx.post(url, headers=headers, files=files, timeout=120)

    resp.raise_for_status()
    data = resp.json()
    media_url: str = data.get("url", "")
    logger.info("Mídia enviada: %s -> %s", file_path.name, media_url)
    return media_url


def api_create_exercise(
    base_url: str,
    token: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/v1/admin/catalog/exercises/"
    headers = {"Authorization": f"Bearer {token}"}
    _rate_limit("create_exercise")

    resp = httpx.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data: Dict[str, Any] = resp.json()
    logger.info("Exercício criado: %s (id=%s)", payload.get("name", ""), data.get("id", ""))
    return data
