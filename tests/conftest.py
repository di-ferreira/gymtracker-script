from typing import Any, Dict, List

import pytest


@pytest.fixture
def mock_ai_result() -> Dict[str, Any]:
    return {
        "nome_exercicio": "Agachamento Frontal",
        "grupo_muscular": "Quadríceps (principal), Glúteos Máximos, Core",
        "musculo_primario": "Quadríceps",
        "modo_execucao": "1. Posicione a barra frontal. 2. Desça até 90 graus. 3. Suba contraindo o quadríceps.",
        "dicas_seguranca": "Mantenha a coluna neutra. Não deixe os joelhos ultrapassarem a ponta dos pés.",
        "equipamentos": ["barra", "anilhas"],
        "tipo_movimento": "composto",
        "dificuldade": "intermediario",
        "exercicios_alternativos": ["Agachamento Livre", "Leg Press"],
        "tags": ["pernas", "quadriceps", "gluteos", "agachamento"],
    }


@pytest.fixture
def mock_equipment_cache() -> List[Dict[str, Any]]:
    return []


@pytest.fixture
def mock_muscle_groups_cache() -> List[Dict[str, Any]]:
    return []


@pytest.fixture
def mock_movement_groups_cache() -> List[Dict[str, Any]]:
    return []


@pytest.fixture
def mock_exercises_cache() -> List[Dict[str, Any]]:
    return []
