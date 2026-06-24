import json
from typing import Any, Dict, List

import pytest

from skills.prompt_builder import (
    FEW_SHOT_EXAMPLES,
    REQUIRED_FIELDS,
    SYSTEM_PROMPT,
    VALID_DIFFICULTY_LEVELS,
    VALID_MOVEMENT_TYPES,
    VALID_MUSCLE_GROUPS,
    PromptBuilder,
)


class TestSystemPromptSchema:
    """Verifica que o SYSTEM_PROMPT instrui a IA sobre todos os campos necessários."""

    ALL_FIELDS = [
        "nome_exercicio",
        "grupo_muscular",
        "musculo_primario",
        "modo_execucao",
        "dicas_seguranca",
        "equipamentos",
        "tipo_movimento",
        "dificuldade",
        "exercicios_alternativos",
        "tags",
    ]

    def test_system_prompt_has_all_fields(self):
        for field in self.ALL_FIELDS:
            assert field in SYSTEM_PROMPT, (
                f"Campo '{field}' não encontrado no SYSTEM_PROMPT"
            )

    def test_required_fields_are_subset_of_all_fields(self):
        for field in REQUIRED_FIELDS:
            assert field in self.ALL_FIELDS, (
                f"REQUIRED_FIELDS contém '{field}' que não está em ALL_FIELDS"
            )

    def test_valid_difficulty_levels_match_prompt(self):
        for level in VALID_DIFFICULTY_LEVELS:
            assert level in SYSTEM_PROMPT, (
                f"Nível de dificuldade '{level}' não encontrado no SYSTEM_PROMPT"
            )

    def test_valid_movement_types_match_prompt(self):
        for mt in VALID_MOVEMENT_TYPES:
            assert mt in SYSTEM_PROMPT, (
                f"Tipo de movimento '{mt}' não encontrado no SYSTEM_PROMPT"
            )

    def test_valid_muscle_groups_complete(self):
        for mg in VALID_MUSCLE_GROUPS:
            assert mg in SYSTEM_PROMPT.lower(), (
                f"Grupo muscular '{mg}' não encontrado no SYSTEM_PROMPT"
            )


class TestFewShotExamples:
    """Verifica que todos os exemplos few-shot têm os campos novos."""

    def test_all_examples_have_dificuldade(self):
        for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
            assert "dificuldade" in ex, (
                f"Exemplo {i} não possui campo 'dificuldade'"
            )
            assert ex["dificuldade"] in VALID_DIFFICULTY_LEVELS, (
                f"Exemplo {i} dificuldade '{ex['dificuldade']}' inválida"
            )

    def test_all_examples_have_exercicios_alternativos(self):
        for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
            assert "exercicios_alternativos" in ex, (
                f"Exemplo {i} não possui campo 'exercicios_alternativos'"
            )
            assert isinstance(ex["exercicios_alternativos"], list), (
                f"Exemplo {i} exercicios_alternativos não é lista"
            )
            assert len(ex["exercicios_alternativos"]) > 0, (
                f"Exemplo {i} exercicios_alternativos está vazia"
            )

    def test_all_examples_have_all_required(self):
        for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
            for field in REQUIRED_FIELDS:
                assert field in ex, (
                    f"Exemplo {i} não possui campo obrigatório '{field}'"
                )


class TestValidateResponse:
    """Testa a validação da resposta da IA."""

    def test_valid_response_passes(self, mock_ai_result):
        valid, errors = PromptBuilder.validate_response(mock_ai_result)
        assert valid is True
        assert errors == []

    def test_missing_required_field(self, mock_ai_result):
        for field in REQUIRED_FIELDS:
            data = dict(mock_ai_result)
            del data[field]
            valid, errors = PromptBuilder.validate_response(data)
            assert valid is False
            assert any(field in e for e in errors), (
                f"Campo '{field}' ausente não gerou erro. Erros: {errors}"
            )

    def test_empty_required_string(self, mock_ai_result):
        data = dict(mock_ai_result)
        data["nome_exercicio"] = ""
        valid, errors = PromptBuilder.validate_response(data)
        assert valid is False

    def test_empty_required_list(self, mock_ai_result):
        data = dict(mock_ai_result)
        data["equipamentos"] = []
        valid, errors = PromptBuilder.validate_response(data)
        assert valid is False
        assert any("equipamentos" in e for e in errors)

    def test_invalid_muscle_group(self, mock_ai_result):
        data = dict(mock_ai_result)
        data["musculo_primario"] = "Perna"
        valid, errors = PromptBuilder.validate_response(data)
        assert valid is False
        assert any("musculo_primario" in e for e in errors)

    def test_invalid_movement_type(self, mock_ai_result):
        data = dict(mock_ai_result)
        data["tipo_movimento"] = "aerobico"
        valid, errors = PromptBuilder.validate_response(data)
        assert valid is False
        assert any("tipo_movimento" in e for e in errors)

    def test_optional_dificuldade_not_validated(self, mock_ai_result):
        data = dict(mock_ai_result)
        data["dificuldade"] = ""
        valid, errors = PromptBuilder.validate_response(data)
        assert valid is True

    def test_optional_exercicios_alternativos_not_validated(self, mock_ai_result):
        data = dict(mock_ai_result)
        data["exercicios_alternativos"] = []
        valid, errors = PromptBuilder.validate_response(data)
        assert valid is True

    def test_none_values_fail(self, mock_ai_result):
        data = dict(mock_ai_result)
        data["modo_execucao"] = None
        valid, errors = PromptBuilder.validate_response(data)
        assert valid is False


class TestRepairPartialResponse:
    """Testa o reparo de respostas parciais da IA."""

    def test_repair_fills_dificuldade_default(self):
        result = PromptBuilder.repair_partial_response({"nome_exercicio": "Teste"})
        assert result["dificuldade"] == "intermediario"

    def test_repair_preserves_existing_dificuldade(self):
        result = PromptBuilder.repair_partial_response(
            {"nome_exercicio": "Teste", "dificuldade": "avancado"}
        )
        assert result["dificuldade"] == "avancado"

    def test_repair_fills_exercicios_alternativos_default(self):
        result = PromptBuilder.repair_partial_response({"nome_exercicio": "Teste"})
        assert result["exercicios_alternativos"] == []

    def test_repair_preserves_existing_exercicios_alternativos(self):
        result = PromptBuilder.repair_partial_response(
            {
                "nome_exercicio": "Teste",
                "exercicios_alternativos": ["Alt1", "Alt2"],
            }
        )
        assert result["exercicios_alternativos"] == ["Alt1", "Alt2"]

    def test_repair_fills_all_required_defaults(self):
        result = PromptBuilder.repair_partial_response({})
        assert result["nome_exercicio"] == "Exercício Não Identificado"
        assert result["musculo_primario"] == "Outros"
        assert "Execute o movimento" in result["modo_execucao"]
        assert "Consulte um profissional" in result["dicas_seguranca"]
        assert result["equipamentos"] == ["peso corporal"]
        assert result["tipo_movimento"] == "composto"
        assert result["dificuldade"] == "intermediario"
        assert result["exercicios_alternativos"] == []
        assert len(result["tags"]) > 0

    def test_repair_uses_file_name_for_nome_exercicio(self):
        result = PromptBuilder.repair_partial_response(
            {}, file_name="meu_exercicio_teste"
        )
        assert "Meu Exercicio Teste" in result["nome_exercicio"]

    def test_repair_extracts_muscle_from_grupo_muscular(self):
        result = PromptBuilder.repair_partial_response(
            {"grupo_muscular": "Quadríceps (principal), Glúteos (secundário)"}
        )
        assert result["musculo_primario"] == "Quadríceps"

    def test_repair_heuristic_equipments_from_tags(self):
        result = PromptBuilder.repair_partial_response(
            {"nome_exercicio": "Teste", "tags": ["halteres", "biceps"]}
        )
        assert "halteres" in result["equipamentos"]

    def test_repair_heuristic_equipments_from_name(self):
        result = PromptBuilder.repair_partial_response(
            {"nome_exercicio": "Rosca na Barra W"}
        )
        assert "barra" in result["equipamentos"]

    def test_repair_does_not_overwrite_existing(self):
        data = {
            "nome_exercicio": "Meu Exercicio",
            "musculo_primario": "Costas",
            "modo_execucao": "1. Faça algo.",
            "dicas_seguranca": "Cuidado.",
            "equipamentos": ["cabo"],
            "tipo_movimento": "isolamento",
            "dificuldade": "expert",
            "exercicios_alternativos": ["Outro Exercicio"],
            "tags": ["costas"],
        }
        result = PromptBuilder.repair_partial_response(data)
        assert result == data


class TestFallbackFromFilename:
    """Testa o fallback quando a IA não retorna JSON válido."""

    def test_fallback_has_all_fields(self):
        result = PromptBuilder.fallback_from_filename("meu_gif_teste")
        assert result["nome_exercicio"] == "Meu Gif Teste"
        assert "musculo_primario" in result
        assert "modo_execucao" in result
        assert "dicas_seguranca" in result
        assert "equipamentos" in result
        assert "tipo_movimento" in result
        assert "dificuldade" in result
        assert "exercicios_alternativos" in result
        assert "tags" in result

    def test_fallback_cleans_special_chars(self):
        result = PromptBuilder.fallback_from_filename("supino_(1)")
        assert result["nome_exercicio"] == "Supino 1"


class TestBuildSystemPrompt:
    """Testa a montagem do system prompt."""

    def test_build_without_few_shot(self):
        result = PromptBuilder.build_system_prompt(include_few_shot=False)
        assert result == SYSTEM_PROMPT

    def test_build_with_few_shot_includes_examples(self):
        result = PromptBuilder.build_system_prompt(include_few_shot=True)
        for ex in FEW_SHOT_EXAMPLES:
            assert ex["nome_exercicio"] in result

    def test_build_with_few_shot_has_json(self):
        result = PromptBuilder.build_system_prompt(include_few_shot=True)
        for ex in FEW_SHOT_EXAMPLES:
            for key in ("dificuldade", "exercicios_alternativos"):
                assert f'"{key}"' in result


class TestBuildUserMessage:
    def test_build_user_message(self):
        result = PromptBuilder.build_user_message("meu_exercicio.gif")
        assert "meu_exercicio.gif" in result
        assert "JSON" in result


class TestFormatFewShotBlock:
    def test_format_returns_json(self):
        block = PromptBuilder.format_few_shot_block(count=1)
        assert "Agachamento Livre" in block
        assert "dificuldade" in block
        assert "exercicios_alternativos" in block
