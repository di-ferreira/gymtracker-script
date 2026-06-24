import json

import pytest

from skills.ai_client import BaseAIClient
from skills.prompt_builder import PromptBuilder


class TestParseJsonResponse:
    """Testa o parsing da resposta JSON bruta da IA."""

    def test_parse_plain_json(self):
        raw = '{"nome_exercicio": "Agachamento"}'
        result = BaseAIClient._parse_json_response(raw)
        assert result == {"nome_exercicio": "Agachamento"}

    def test_parse_json_with_markdown_fence(self):
        raw = '```json\n{"nome_exercicio": "Agachamento"}\n```'
        result = BaseAIClient._parse_json_response(raw)
        assert result == {"nome_exercicio": "Agachamento"}

    def test_parse_json_with_markdown_no_lang(self):
        raw = '```\n{"nome_exercicio": "Agachamento"}\n```'
        result = BaseAIClient._parse_json_response(raw)
        assert result == {"nome_exercicio": "Agachamento"}

    def test_parse_json_with_extra_text_before_fails(self):
        raw = 'Aqui está o JSON:\n{"nome_exercicio": "Teste"}'
        with pytest.raises((json.JSONDecodeError, ValueError)):
            BaseAIClient._parse_json_response(raw)

    def test_parse_invalid_json_raises(self):
        raw = "não é um json válido"
        with pytest.raises((json.JSONDecodeError, ValueError)):
            BaseAIClient._parse_json_response(raw)

    def test_parse_empty_string_raises(self):
        with pytest.raises((json.JSONDecodeError, ValueError)):
            BaseAIClient._parse_json_response("")

    def test_parse_complex_full_response(self, mock_ai_result):
        raw = json.dumps(mock_ai_result, ensure_ascii=False)
        result = BaseAIClient._parse_json_response(raw)
        assert result == mock_ai_result


class TestFallbackFromFilename:
    """Testa que o fallback gera todas as informações necessárias."""

    def test_fallback_has_dificuldade(self):
        result = PromptBuilder.fallback_from_filename("test.gif")
        assert result["dificuldade"] == "intermediario"

    def test_fallback_has_exercicios_alternativos(self):
        result = PromptBuilder.fallback_from_filename("test.gif")
        assert result["exercicios_alternativos"] == []

    def test_fallback_has_all_required(self):
        result = PromptBuilder.fallback_from_filename("test.gif")
        for field in [
            "nome_exercicio",
            "musculo_primario",
            "modo_execucao",
            "dicas_seguranca",
            "equipamentos",
            "tipo_movimento",
            "tags",
        ]:
            assert field in result, f"Campo '{field}' ausente no fallback"
            assert result[field], f"Campo '{field}' vazio no fallback"
