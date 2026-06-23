import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from skills import (
    api_create_exercise,
    api_get_movement_groups,
    api_get_muscle_groups,
    api_login,
    api_upload_media,
    create_ai_client,
    move_to_processed,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("gymtracker")


def _find_group_id(
    text: str,
    groups: List[Dict[str, Any]],
    default_id: Optional[str],
) -> Optional[str]:
    text_lower = text.lower().strip()
    for g in groups:
        name = g.get("name", "").lower().strip()
        if name and (name in text_lower or text_lower in name):
            return str(g["id"])
    return default_id or None


def build_exercise_payload(
    ai_result: Dict[str, Any],
    gif_url: str,
    muscle_group_id: Optional[str],
    movement_group_id: Optional[str],
) -> Dict[str, Any]:
    name = ai_result.get("nome_exercicio", "")
    desc = ai_result.get("grupo_muscular", "")
    tips = ai_result.get("dicas_seguranca", "")
    execution_text = ai_result.get("modo_execucao", "")

    description = f"{desc}\n\n## Modo de Execução\n{execution_text}" if execution_text else desc

    payload = {
        "name": name,
        "description": description,
        "execution_tips": tips,
        "gif_url": gif_url,
    }
    if muscle_group_id:
        payload["muscle_group_id"] = muscle_group_id
    if movement_group_id:
        payload["movement_group_id"] = movement_group_id
    return payload


def main() -> None:
    load_dotenv()

    gif_root = Path(os.getenv("GIF_ROOT_PATH", "./1.300 GIFs de Musculação"))
    processed_dirname = os.getenv("PROCESSED_DIR", "processados")
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    email = os.getenv("API_EMAIL", "")
    password = os.getenv("API_PASSWORD", "")
    default_muscle_id = os.getenv("DEFAULT_MUSCLE_GROUP_ID") or None
    default_movement_id = os.getenv("DEFAULT_MOVEMENT_GROUP_ID") or None

    if not gif_root.is_dir():
        logger.error("Pasta raiz de GIFs não encontrada: %s", gif_root)
        sys.exit(1)

    ai_client = create_ai_client()

    logger.info("Autenticando na API...")
    token = api_login(base_url, email, password)

    logger.info("Carregando grupos de referência...")
    muscle_groups = api_get_muscle_groups(base_url, token)
    movement_groups = api_get_movement_groups(base_url, token)

    gif_paths = sorted(gif_root.rglob("*.gif"))
    if not gif_paths:
        logger.warning("Nenhum arquivo .gif encontrado em %s", gif_root)
        return

    logger.info("Encontrados %d arquivos .gif para processar", len(gif_paths))

    total = len(gif_paths)
    success_count = 0
    fail_count = 0

    for idx, gif_path in enumerate(gif_paths, start=1):
        file_name = gif_path.stem
        logger.info("[%d/%d] Processando: %s", idx, total, gif_path.name)

        try:
            logger.info("  -> Enviando para IA...")
            ai_result = ai_client.analyze_exercise(gif_path, file_name)
            logger.info("  -> IA retornou: %s", ai_result.get("nome_exercicio", "?"))

            muscle_id = _find_group_id(
                ai_result.get("grupo_muscular", ""),
                muscle_groups,
                default_muscle_id,
            )
            movement_id = _find_group_id(
                ai_result.get("nome_exercicio", ""),
                movement_groups,
                default_movement_id,
            )

            if not muscle_id:
                logger.warning(
                    "  -> Grupo muscular não identificado para '%s', usando fallback",
                    ai_result.get("grupo_muscular", ""),
                )
            if not movement_id:
                logger.warning(
                    "  -> Grupo de movimento não identificado para '%s', usando fallback",
                    ai_result.get("nome_exercicio", ""),
                )

            logger.info("  -> Enviando mídia...")
            gif_url = api_upload_media(base_url, token, gif_path)

            payload = build_exercise_payload(
                ai_result, gif_url, muscle_id, movement_id
            )

            logger.info("  -> Criando exercício...")
            api_create_exercise(base_url, token, payload)

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
    logger.info("  Falhas: %d", fail_count)
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
