import logging
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv

from skills import (
    create_ai_client,
    api_login,
    api_get_equipment,
    api_create_equipment,
    api_get_muscle_groups,
    api_create_muscle_group,
    api_get_movement_groups,
    api_create_movement_group,
    api_get_exercises,
    api_upload_media,
    api_create_exercise,
    api_create_instruction,
    move_to_processed,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("gymtracker")


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").strip().lower()


def _find_by_name(name: str, items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    name_key = _normalize(name)
    for item in items:
        if _normalize(item.get("name", "")) == name_key:
            return item
    return None


def _ensure_entity(
    name: str,
    cache: List[Dict[str, Any]],
    create_func: Callable[..., Dict[str, Any]],
    base_url: str,
    token: str,
) -> str:
    existing = _find_by_name(name, cache)
    if existing:
        logger.info("  -> Já existe: %s (id=%s)", name, existing["id"])
        return str(existing["id"])
    logger.info("  -> Criando: %s", name)
    created = create_func(base_url, token, name)
    created_id = str(created["id"])
    cache.append(created)
    return created_id


def _parse_instructions_to_steps(text: str) -> List[str]:
    if not text:
        return []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    numbered_pattern = re.compile(r"^\d+[\.\)]\s*")
    steps = []
    for line in lines:
        clean = numbered_pattern.sub("", line).strip()
        if clean:
            steps.append(clean)
    return steps


def build_exercise_payload(
    ai_result: Dict[str, Any],
    gif_url: str,
    muscle_group_id: str,
    movement_group_id: str,
) -> Dict[str, Any]:
    return {
        "name": ai_result.get("nome_exercicio", ""),
        "description": ai_result.get("grupo_muscular", ""),
        "execution_tips": ai_result.get("dicas_seguranca", ""),
        "gif_url": gif_url,
        "muscle_group_id": muscle_group_id,
        "movement_group_id": movement_group_id,
    }


def main() -> None:
    load_dotenv()

    gif_root = Path(os.getenv("GIF_ROOT_PATH", "./1.300 GIFs de Musculação"))
    processed_dirname = os.getenv("PROCESSED_DIR", "processados")
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    email = os.getenv("API_EMAIL", "")
    password = os.getenv("API_PASSWORD", "")

    if not gif_root.is_dir():
        logger.error("Pasta raiz de GIFs não encontrada: %s", gif_root)
        sys.exit(1)

    ai_client = create_ai_client()

    logger.info("Autenticando na API...")
    token = api_login(base_url, email, password)

    logger.info("Carregando catálogo de referência da API...")
    equipment_cache = api_get_equipment(base_url, token)
    muscle_groups_cache = api_get_muscle_groups(base_url, token)
    movement_groups_cache = api_get_movement_groups(base_url, token)
    exercises_cache = api_get_exercises(base_url, token)

    logger.info(
        "Cache: %d equipamentos, %d grupos musculares, %d movimentos, %d exercícios",
        len(equipment_cache),
        len(muscle_groups_cache),
        len(movement_groups_cache),
        len(exercises_cache),
    )

    gif_paths = sorted(gif_root.rglob("*.gif"))
    if not gif_paths:
        logger.warning("Nenhum arquivo .gif encontrado em %s", gif_root)
        return

    logger.info("Encontrados %d arquivos .gif para processar", len(gif_paths))

    total = len(gif_paths)
    success_count = 0
    fail_count = 0
    skipped_count = 0

    for idx, gif_path in enumerate(gif_paths, start=1):
        file_name = gif_path.stem
        logger.info("[%d/%d] Processando: %s", idx, total, gif_path.name)

        try:
            logger.info("  -> Enviando para IA...")
            ai_result = ai_client.analyze_exercise(gif_path, file_name)
            exercise_name = ai_result.get("nome_exercicio", "")
            logger.info("  -> IA retornou: %s", exercise_name)

            if _find_by_name(exercise_name, exercises_cache):
                logger.warning("  -> Exercício '%s' já existe no catálogo. Pulando.", exercise_name)
                move_to_processed(gif_path, processed_dirname)
                skipped_count += 1
                continue

            equipamentos = ai_result.get("equipamentos") or []
            for equip_name in equipamentos:
                _ensure_entity(
                    equip_name,
                    equipment_cache,
                    api_create_equipment,
                    base_url,
                    token,
                )

            muscle_name = ai_result.get("musculo_primario") or ai_result.get("grupo_muscular", "")
            muscle_id = _ensure_entity(
                muscle_name,
                muscle_groups_cache,
                api_create_muscle_group,
                base_url,
                token,
            )

            movement_name = ai_result.get("tipo_movimento", "composto")
            movement_id = _ensure_entity(
                movement_name,
                movement_groups_cache,
                api_create_movement_group,
                base_url,
                token,
            )

            logger.info("  -> Enviando mídia...")
            gif_url = api_upload_media(base_url, token, gif_path)

            payload = build_exercise_payload(
                ai_result, gif_url, muscle_id, movement_id
            )

            logger.info("  -> Criando exercício...")
            created = api_create_exercise(base_url, token, payload)
            exercises_cache.append(created)
            exercise_db_id = created.get("id", "")

            execution_text = ai_result.get("modo_execucao", "")
            steps = _parse_instructions_to_steps(execution_text)
            for step_idx, step_desc in enumerate(steps, start=1):
                api_create_instruction(base_url, token, exercise_db_id, step_desc, step_idx)

            move_to_processed(gif_path, processed_dirname)
            success_count += 1
            logger.info("  [OK] %s processado com sucesso", gif_path.name)

        except Exception as e:
            fail_count += 1
            logger.error(
                "  [FALHA] %s: %s",
                gif_path.name,
                str(e),
                exc_info=True,
            )

    logger.info("=" * 50)
    logger.info("RELATÓRIO FINAL")
    logger.info("  Total de arquivos: %d", total)
    logger.info("  Sucessos: %d", success_count)
    logger.info("  Pulados (já existiam): %d", skipped_count)
    logger.info("  Falhas: %d", fail_count)
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
