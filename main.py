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
    api_create_exercise_alternative,
    move_to_processed,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("gymtracker")


EQUIPMENT_CATEGORIES: Dict[str, str] = {
    "halteres": "pesos livres",
    "halter": "pesos livres",
    "barra": "pesos livres",
    "anilhas": "pesos livres",
    "banco": "estruturas",
    "maquina": "maquinas",
    "máquina": "maquinas",
    "cabo": "cabos",
    "polia": "cabos",
    "elastico": "acessorios",
    "elástico": "acessorios",
    "smith": "maquinas",
    "bola": "acessorios",
    "step": "acessorios",
    "kettlebell": "pesos livres",
    "peso corporal": "peso corporal",
}

EQUIPMENT_DESCRIPTIONS: Dict[str, str] = {
    "halteres": "Pesos livres seguros com as mãos, usados para uma ampla variedade de exercícios de fortalecimento muscular",
    "halter": "Pesos livres seguros com as mãos, usados para uma ampla variedade de exercícios de fortalecimento muscular",
    "barra": "Barra reta utilizada para exercícios como agachamento, supino e levantamento terra",
    "anilhas": "Discos de peso que são adicionados à barra para aumentar a resistência",
    "banco": "Banco ajustável ou reto utilizado como apoio para exercícios sentados ou deitados",
    "maquina": "Equipamento com cabos, polias e assento que guia o movimento do exercício",
    "máquina": "Equipamento com cabos, polias e assento que guia o movimento do exercício",
    "cabo": "Sistema de cabos e polias que proporciona resistência constante durante o movimento",
    "polia": "Sistema de polias que permite movimentos multidirecionais com resistência",
    "elastico": "Faixa elástica de resistência variável, usada para exercícios de fortalecimento e reabilitação",
    "elástico": "Faixa elástica de resistência variável, usada para exercícios de fortalecimento e reabilitação",
    "smith": "Máquina com barra guiada verticalmente, utilizada para agachamento e supino com segurança",
    "bola": "Bola suíça ou bola de estabilidade utilizada para exercícios de equilíbrio e core",
    "step": "Plataforma elevada utilizada para exercícios aeróbicos e de step",
    "kettlebell": "Peso com alça em forma de bola, utilizado para exercícios de balanço e força funcional",
    "peso corporal": "O próprio peso do corpo como resistência, sem necessidade de equipamentos externos",
}

MOVEMENT_GROUP_DESCRIPTIONS: Dict[str, str] = {
    "composto": "Movimentos que envolvem múltiplas articulações e grupos musculares simultaneamente, proporcionando maior ganho de força e eficiência",
    "isolamento": "Movimentos que focam em uma única articulação e grupo muscular específico, ideal para definição muscular e correção de assimetrias",
    "funcional": "Movimentos que simulam padrões motores do dia a dia, integrando múltiplos grupos musculares e melhorando a coordenação",
    "calistenia": "Movimentos que utilizam o peso corporal como resistência principal, desenvolvendo força, flexibilidade e controle corporal",
}


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
    **extra_fields: Any,
) -> str:
    existing = _find_by_name(name, cache)
    if existing:
        logger.info("  -> Já existe: %s (id=%s)", name, existing["id"])
        return str(existing["id"])
    logger.info("  -> Criando: %s", name)
    created = create_func(base_url, token, name, **extra_fields)
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
    equipment_ids: List[str],
) -> Dict[str, Any]:
    return {
        "name": ai_result.get("nome_exercicio", ""),
        "description": ai_result.get("grupo_muscular", ""),
        "execution_tips": ai_result.get("dicas_seguranca", ""),
        "difficulty": ai_result.get("dificuldade", "intermediario"),
        "target_muscle_primary": ai_result.get("musculo_primario", ""),
        "gif_url": gif_url,
        "muscle_group_id": muscle_group_id,
        "movement_group_id": movement_group_id,
        "equipment_ids": equipment_ids,
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
            equipment_ids: List[str] = []
            for equip_name in equipamentos:
                equip_key = _normalize(equip_name)
                equip_id = _ensure_entity(
                    equip_name,
                    equipment_cache,
                    api_create_equipment,
                    base_url,
                    token,
                    description=EQUIPMENT_DESCRIPTIONS.get(
                        equip_key,
                        f"Equipamento utilizado em exercícios: {equip_name}",
                    ),
                    category=EQUIPMENT_CATEGORIES.get(equip_key, "geral"),
                )
                equipment_ids.append(equip_id)

            muscle_name = ai_result.get("musculo_primario") or ai_result.get("grupo_muscular", "")
            muscle_description = ai_result.get("grupo_muscular", f"Grupo muscular {muscle_name}")
            muscle_id = _ensure_entity(
                muscle_name,
                muscle_groups_cache,
                api_create_muscle_group,
                base_url,
                token,
                description=muscle_description,
            )

            movement_name = ai_result.get("tipo_movimento", "composto")
            movement_description = MOVEMENT_GROUP_DESCRIPTIONS.get(
                _normalize(movement_name),
                f"Tipo de movimento: {movement_name}",
            )
            movement_id = _ensure_entity(
                movement_name,
                movement_groups_cache,
                api_create_movement_group,
                base_url,
                token,
                description=movement_description,
            )

            logger.info("  -> Enviando mídia...")
            gif_url = api_upload_media(base_url, token, gif_path)

            payload = build_exercise_payload(
                ai_result, gif_url, muscle_id, movement_id, equipment_ids,
            )

            logger.info("  -> Criando exercício...")
            created = api_create_exercise(base_url, token, payload)
            exercises_cache.append(created)
            exercise_db_id = created.get("id", "")

            alternative_names = ai_result.get("exercicios_alternativos") or []
            for alt_name in alternative_names:
                alt_exercise = _find_by_name(alt_name, exercises_cache)
                if alt_exercise:
                    api_create_exercise_alternative(
                        base_url,
                        token,
                        exercise_db_id,
                        str(alt_exercise["id"]),
                        reason=f"Alternativa similar a {exercise_name}",
                    )

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
