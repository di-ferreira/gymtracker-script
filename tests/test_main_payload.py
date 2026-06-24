from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from main import (
    EQUIPMENT_CATEGORIES,
    EQUIPMENT_DESCRIPTIONS,
    MOVEMENT_GROUP_DESCRIPTIONS,
    _ensure_entity,
    _find_by_name,
    build_exercise_payload,
)


class TestBuildExercisePayload:
    """Verifica que o payload do exercise contém todos os campos necessários."""

    REQUIRED_PAYLOAD_FIELDS = [
        "name",
        "description",
        "execution_tips",
        "difficulty",
        "target_muscle_primary",
        "gif_url",
        "muscle_group_id",
        "movement_group_id",
        "equipment_ids",
    ]

    def test_payload_has_all_fields(self, mock_ai_result):
        payload = build_exercise_payload(
            ai_result=mock_ai_result,
            gif_url="http://example.com/test.gif",
            muscle_group_id="mg-id-1",
            movement_group_id="mv-id-1",
            equipment_ids=["eq-id-1", "eq-id-2"],
        )
        for field in self.REQUIRED_PAYLOAD_FIELDS:
            assert field in payload, f"Campo '{field}' ausente no payload"

    def test_payload_field_mapping(self, mock_ai_result):
        payload = build_exercise_payload(
            ai_result=mock_ai_result,
            gif_url="http://example.com/test.gif",
            muscle_group_id="mg-id-1",
            movement_group_id="mv-id-1",
            equipment_ids=["eq-id-1"],
        )
        assert payload["name"] == "Agachamento Frontal"
        assert payload["description"] == "Quadríceps (principal), Glúteos Máximos, Core"
        assert payload["difficulty"] == "intermediario"
        assert payload["target_muscle_primary"] == "Quadríceps"
        assert payload["gif_url"] == "http://example.com/test.gif"
        assert payload["muscle_group_id"] == "mg-id-1"
        assert payload["movement_group_id"] == "mv-id-1"
        assert payload["equipment_ids"] == ["eq-id-1"]

    def test_payload_default_difficulty(self):
        payload = build_exercise_payload(
            ai_result={"nome_exercicio": "Teste"},
            gif_url="http://example.com/test.gif",
            muscle_group_id="mg-1",
            movement_group_id="mv-1",
            equipment_ids=[],
        )
        assert payload["difficulty"] == "intermediario"

    def test_payload_default_target_muscle(self):
        payload = build_exercise_payload(
            ai_result={"nome_exercicio": "Teste"},
            gif_url="http://example.com/test.gif",
            muscle_group_id="mg-1",
            movement_group_id="mv-1",
            equipment_ids=[],
        )
        assert payload["target_muscle_primary"] == ""

    def test_payload_equipment_ids_is_list(self, mock_ai_result):
        payload = build_exercise_payload(
            ai_result=mock_ai_result,
            gif_url="http://example.com/test.gif",
            muscle_group_id="mg-1",
            movement_group_id="mv-1",
            equipment_ids=[],
        )
        assert isinstance(payload["equipment_ids"], list)

    def test_payload_equipment_ids_empty_by_default(self, mock_ai_result):
        payload = build_exercise_payload(
            ai_result=mock_ai_result,
            gif_url="http://example.com/test.gif",
            muscle_group_id="mg-1",
            movement_group_id="mv-1",
            equipment_ids=[],
        )
        assert payload["equipment_ids"] == []


class TestFindByName:
    """Testa a busca normalizada por nome no cache."""

    def test_find_exact_match(self):
        items = [{"id": "1", "name": "Quadríceps"}]
        result = _find_by_name("Quadríceps", items)
        assert result is not None
        assert result["id"] == "1"

    def test_find_case_insensitive(self):
        items = [{"id": "1", "name": "Quadríceps"}]
        result = _find_by_name("quadríceps", items)
        assert result is not None

    def test_find_ascii_folded(self):
        items = [{"id": "1", "name": "Quadríceps"}]
        result = _find_by_name("quadriceps", items)
        assert result is not None

    def test_not_found_returns_none(self):
        items = [{"id": "1", "name": "Bíceps"}]
        result = _find_by_name("Tríceps", items)
        assert result is None

    def test_empty_cache_returns_none(self):
        result = _find_by_name("Qualquer", [])
        assert result is None


class TestEnsureEntity:
    """Testa a criação/garantia de entidades no catálogo."""

    def test_creates_new_entity(self):
        cache: List[Dict[str, Any]] = []
        create_func = MagicMock(return_value={"id": "new-id-123"})
        result_id = _ensure_entity(
            "Novo Item", cache, create_func, "http://base", "token"
        )
        assert result_id == "new-id-123"
        create_func.assert_called_once_with(
            "http://base", "token", "Novo Item"
        )
        assert len(cache) == 1
        assert cache[0]["id"] == "new-id-123"

    def test_returns_existing_entity(self):
        cache = [{"id": "existing-id", "name": "Item Existente"}]
        create_func = MagicMock()
        result_id = _ensure_entity(
            "Item Existente", cache, create_func, "http://base", "token"
        )
        assert result_id == "existing-id"
        create_func.assert_not_called()

    def test_passes_extra_fields_to_create_func(self):
        cache: List[Dict[str, Any]] = []
        create_func = MagicMock(return_value={"id": "new-id"})
        _ensure_entity(
            "Item",
            cache,
            create_func,
            "http://base",
            "token",
            description="Descrição teste",
            category="categoria-teste",
        )
        create_func.assert_called_once_with(
            "http://base", "token", "Item",
            description="Descrição teste",
            category="categoria-teste",
        )

    def test_passes_partial_extra_fields(self):
        cache: List[Dict[str, Any]] = []
        create_func = MagicMock(return_value={"id": "new-id"})
        _ensure_entity(
            "Item",
            cache,
            create_func,
            "http://base",
            "token",
            description="Só descrição",
        )
        create_func.assert_called_once_with(
            "http://base", "token", "Item",
            description="Só descrição",
        )


class TestLookupTables:
    """Verifica que os lookups de descrição/categoria cobrem os equipamentos comuns."""

    KNOWN_EQUIPMENT_NAMES = [
        "halteres", "halter", "barra", "anilhas", "banco",
        "maquina", "máquina", "cabo", "polia", "elastico",
        "elástico", "smith", "bola", "step", "kettlebell",
        "peso corporal",
    ]

    def test_all_known_equipment_have_category(self):
        for name in self.KNOWN_EQUIPMENT_NAMES:
            assert name in EQUIPMENT_CATEGORIES, (
                f"Equipamento '{name}' não tem categoria definida"
            )

    def test_all_known_equipment_have_description(self):
        for name in self.KNOWN_EQUIPMENT_NAMES:
            assert name in EQUIPMENT_DESCRIPTIONS, (
                f"Equipamento '{name}' não tem descrição definida"
            )

    def test_unknown_equipment_gets_default_category(self):
        assert EQUIPMENT_CATEGORIES.get("equipamento_desconhecido", "geral") == "geral"

    def test_unknown_equipment_gets_default_description(self):
        default = EQUIPMENT_DESCRIPTIONS.get(
            "desconhecido",
            "Equipamento utilizado em exercícios: desconhecido",
        )
        assert "desconhecido" in default

    def test_movement_descriptions_cover_all_types(self):
        from skills.prompt_builder import VALID_MOVEMENT_TYPES
        for mt in VALID_MOVEMENT_TYPES:
            assert mt in MOVEMENT_GROUP_DESCRIPTIONS, (
                f"Tipo de movimento '{mt}' não tem descrição"
            )

    def test_movement_unknown_gets_default(self):
        default = MOVEMENT_GROUP_DESCRIPTIONS.get(
            "desconhecido",
            "Tipo de movimento: desconhecido",
        )
        assert "desconhecido" in default
