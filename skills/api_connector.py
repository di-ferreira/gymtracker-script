import logging
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


def _build_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def api_login(base_url: str, email: str, password: str) -> str:
    url = _build_url(base_url, "/api/v1/auth/login")
    _rate_limit("login")
    resp = httpx.post(url, json={"email": email, "password": password}, timeout=15)
    resp.raise_for_status()
    token = resp.json()["access_token"]
    logger.info("Autenticação na API realizada com sucesso")
    return token


def api_get_equipment(base_url: str, token: str) -> List[Dict[str, Any]]:
    url = _build_url(base_url, "/api/v1/admin/catalog/equipment/")
    headers = {"Authorization": f"Bearer {token}"}
    _rate_limit("equipment")
    resp = httpx.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data: List[Dict[str, Any]] = resp.json()
    logger.info("Equipamentos carregados: %d registros", len(data))
    return data


def api_create_equipment(
    base_url: str,
    token: str,
    name: str,
    description: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    url = _build_url(base_url, "/api/v1/admin/catalog/equipment/")
    headers = {"Authorization": f"Bearer {token}"}
    payload: Dict[str, Any] = {"name": name}
    if description:
        payload["description"] = description
    if category:
        payload["category"] = category
    _rate_limit("create_equipment")
    resp = httpx.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    data: Dict[str, Any] = resp.json()
    logger.info("Equipamento criado: %s (id=%s)", name, data.get("id", ""))
    return data


def api_get_muscle_groups(base_url: str, token: str) -> List[Dict[str, Any]]:
    url = _build_url(base_url, "/api/v1/admin/catalog/muscle-groups/")
    headers = {"Authorization": f"Bearer {token}"}
    _rate_limit("muscle_groups")
    resp = httpx.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data: List[Dict[str, Any]] = resp.json()
    logger.info("Grupos musculares carregados: %d registros", len(data))
    return data


def api_create_muscle_group(
    base_url: str, token: str, name: str, description: Optional[str] = None
) -> Dict[str, Any]:
    url = _build_url(base_url, "/api/v1/admin/catalog/muscle-groups/")
    headers = {"Authorization": f"Bearer {token}"}
    payload: Dict[str, Any] = {"name": name}
    if description:
        payload["description"] = description
    _rate_limit("create_muscle_group")
    resp = httpx.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    data: Dict[str, Any] = resp.json()
    logger.info("Grupo muscular criado: %s (id=%s)", name, data.get("id", ""))
    return data


def api_get_movement_groups(base_url: str, token: str) -> List[Dict[str, Any]]:
    url = _build_url(base_url, "/api/v1/admin/catalog/movement-groups/")
    headers = {"Authorization": f"Bearer {token}"}
    _rate_limit("movement_groups")
    resp = httpx.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data: List[Dict[str, Any]] = resp.json()
    logger.info("Grupos de movimento carregados: %d registros", len(data))
    return data


def api_create_movement_group(
    base_url: str, token: str, name: str, description: Optional[str] = None
) -> Dict[str, Any]:
    url = _build_url(base_url, "/api/v1/admin/catalog/movement-groups/")
    headers = {"Authorization": f"Bearer {token}"}
    payload: Dict[str, Any] = {"name": name}
    if description:
        payload["description"] = description
    _rate_limit("create_movement_group")
    resp = httpx.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    data: Dict[str, Any] = resp.json()
    logger.info("Grupo de movimento criado: %s (id=%s)", name, data.get("id", ""))
    return data


def api_get_exercises(
    base_url: str, token: str, page_size: int = 100
) -> List[Dict[str, Any]]:
    url = _build_url(base_url, "/api/v1/admin/catalog/exercises/")
    headers = {"Authorization": f"Bearer {token}"}
    all_exercises: List[Dict[str, Any]] = []
    skip = 0

    while True:
        _rate_limit("exercises")
        resp = httpx.get(
            f"{url}?skip={skip}&limit={page_size}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        page: List[Dict[str, Any]] = resp.json()
        if not page:
            break
        all_exercises.extend(page)
        if len(page) < page_size:
            break
        skip += page_size

    logger.info("Exercícios carregados: %d registros", len(all_exercises))
    return all_exercises


def api_upload_media(
    base_url: str,
    token: str,
    file_path: Path,
    folder: str = "exercises",
) -> str:
    url = _build_url(base_url, f"/api/v1/admin/media/upload?folder={folder}")
    headers = {"Authorization": f"Bearer {token}"}
    _rate_limit("upload")

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "image/gif")}
        resp = httpx.post(url, headers=headers, files=files, timeout=120)

    resp.raise_for_status()
    data = resp.json()
    media_url: str = data.get("url") or data.get("file_url") or data.get("path") or ""
    if not media_url:
        logger.warning("Resposta do upload não possui campo url/file_url/path: %s", data)
    logger.info("Mídia enviada: %s -> %s", file_path.name, media_url)
    return media_url


def api_create_exercise(
    base_url: str,
    token: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    url = _build_url(base_url, "/api/v1/admin/catalog/exercises/")
    headers = {"Authorization": f"Bearer {token}"}
    _rate_limit("create_exercise")

    resp = httpx.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data: Dict[str, Any] = resp.json()
    logger.info("Exercício criado: %s (id=%s)", payload.get("name", ""), data.get("id", ""))
    return data


def api_create_instruction(
    base_url: str,
    token: str,
    exercise_id: str,
    description: str,
    step_order: int,
) -> Dict[str, Any]:
    url = _build_url(base_url, f"/api/v1/admin/catalog/exercises/{exercise_id}/instructions/")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"description": description, "step_order": step_order}
    _rate_limit("create_instruction")
    resp = httpx.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    data: Dict[str, Any] = resp.json()
    return data


def api_create_exercise_alternative(
    base_url: str,
    token: str,
    exercise_id: str,
    alternative_exercise_id: str,
    reason: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    url = _build_url(
        base_url,
        f"/api/v1/admin/catalog/exercises/{exercise_id}/alternatives/",
    )
    headers = {"Authorization": f"Bearer {token}"}
    payload: Dict[str, Any] = {
        "alternative_exercise_id": alternative_exercise_id,
    }
    if reason:
        payload["reason"] = reason
    if note:
        payload["note"] = note
    _rate_limit("create_alternative")
    resp = httpx.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    data: Dict[str, Any] = resp.json()
    logger.info(
        "Alternativa criada: exercise=%s alternative=%s (id=%s)",
        exercise_id, alternative_exercise_id, data.get("id", ""),
    )
    return data
