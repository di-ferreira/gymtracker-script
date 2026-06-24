from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import httpx
import pytest

from skills.api_connector import api_get_exercises


class TestApiGetExercisesPagination:
    """Testa que api_get_exercises faz paginação completa."""

    BASE_URL = "http://teste.com"
    TOKEN = "fake-token"

    def _mock_response(self, json_data: Any, status: int = 200) -> MagicMock:
        resp = MagicMock(spec=httpx.Response)
        resp.json.return_value = json_data
        resp.status_code = status
        resp.raise_for_status.return_value = None
        return resp

    def test_single_page_less_than_limit(self):
        """Menos resultados que o page_size → única chamada, sem loop."""
        page = [{"id": "1", "name": "Exercício A"}] * 50

        with patch("skills.api_connector.httpx.get") as mock_get:
            mock_get.return_value = self._mock_response(page)
            result = api_get_exercises(self.BASE_URL, self.TOKEN, page_size=100)

        assert len(result) == 50
        mock_get.assert_called_once()

    def test_exact_page_size(self):
        """Exatamente page_size → última página cheia, depois página vazia."""
        page = [{"id": str(i), "name": f"Ex {i}"} for i in range(100)]

        with patch("skills.api_connector.httpx.get") as mock_get:
            mock_get.side_effect = [
                self._mock_response(page),
                self._mock_response([]),
            ]
            result = api_get_exercises(self.BASE_URL, self.TOKEN, page_size=100)

        assert len(result) == 100
        assert mock_get.call_count == 2

    def test_multiple_pages(self):
        """Mais resultados que page_size → segunda página menor."""
        page_1 = [{"id": str(i), "name": f"Ex {i}"} for i in range(100)]
        page_2 = [{"id": str(i + 100), "name": f"Ex {i + 100}"} for i in range(50)]

        with patch("skills.api_connector.httpx.get") as mock_get:
            mock_get.side_effect = [
                self._mock_response(page_1),
                self._mock_response(page_2),
            ]
            result = api_get_exercises(self.BASE_URL, self.TOKEN, page_size=100)

        assert len(result) == 150
        assert mock_get.call_count == 2

    def test_three_pages_last_partial(self):
        """Três páginas: 100 + 100 + 75 (75 < 100 → fim)."""
        page_1 = [{"id": str(i), "name": f"Ex {i}"} for i in range(100)]
        page_2 = [{"id": str(i + 100), "name": f"Ex {i + 100}"} for i in range(100)]
        page_3 = [{"id": str(i + 200), "name": f"Ex {i + 200}"} for i in range(75)]

        with patch("skills.api_connector.httpx.get") as mock_get:
            mock_get.side_effect = [
                self._mock_response(page_1),
                self._mock_response(page_2),
                self._mock_response(page_3),
            ]
            result = api_get_exercises(self.BASE_URL, self.TOKEN, page_size=100)

        assert len(result) == 275
        assert mock_get.call_count == 3
        assert result[0]["id"] == "0"
        assert result[199]["id"] == "199"
        assert result[274]["id"] == "274"

    def test_three_full_pages_plus_empty(self):
        """100 + 100 + 100 + 0 → 300 itens, 4 chamadas."""
        pages = [
            [{"id": str(i), "name": f"Ex {i}"} for i in range(100)],
            [{"id": str(i + 100), "name": f"Ex {i + 100}"} for i in range(100)],
            [{"id": str(i + 200), "name": f"Ex {i + 200}"} for i in range(100)],
            [],
        ]

        with patch("skills.api_connector.httpx.get") as mock_get:
            mock_get.side_effect = [self._mock_response(p) for p in pages]
            result = api_get_exercises(self.BASE_URL, self.TOKEN, page_size=100)

        assert len(result) == 300
        assert mock_get.call_count == 4

    def test_empty_database(self):
        """Banco vazio → única chamada, retorna lista vazia."""
        with patch("skills.api_connector.httpx.get") as mock_get:
            mock_get.return_value = self._mock_response([])
            result = api_get_exercises(self.BASE_URL, self.TOKEN)

        assert result == []
        mock_get.assert_called_once()

    def test_pagination_uses_correct_url(self):
        """Verifica que as URLs chamadas têm skip/limit corretos."""
        page_1 = [{"id": str(i)} for i in range(100)]
        page_2 = [{"id": str(i + 100)} for i in range(30)]

        with patch("skills.api_connector.httpx.get") as mock_get:
            mock_get.side_effect = [
                self._mock_response(page_1),
                self._mock_response(page_2),
            ]
            api_get_exercises(self.BASE_URL, self.TOKEN, page_size=100)

        calls = mock_get.call_args_list
        assert len(calls) == 2
        url_1 = str(calls[0][0][0])
        url_2 = str(calls[1][0][0])
        assert "skip=0&limit=100" in url_1
        assert "skip=100&limit=100" in url_2

    def test_raises_on_http_error(self):
        """Erro HTTP na API propaga exceção."""
        with patch("skills.api_connector.httpx.get") as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "Erro 500", request=MagicMock(), response=MagicMock(status_code=500)
            )
            with pytest.raises(httpx.HTTPStatusError):
                api_get_exercises(self.BASE_URL, self.TOKEN)

    def test_rate_limit_is_respected(self):
        """Verifica que _rate_limit foi chamada corretamente."""
        page = [{"id": "1"}]

        with patch("skills.api_connector.httpx.get") as mock_get, \
             patch("skills.api_connector._rate_limit") as mock_rl:
            mock_get.return_value = self._mock_response(page)
            api_get_exercises(self.BASE_URL, self.TOKEN, page_size=100)

            mock_rl.assert_called_once_with("exercises")
