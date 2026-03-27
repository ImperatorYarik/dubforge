import pytest
import requests as req
from unittest.mock import MagicMock, patch


class TestOllamaClient:
    def test_success_returns_response_text(self):
        from app.services.ollama_client import OllamaClient
        client = OllamaClient(base_url="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "translated text"}

        with patch("app.services.ollama_client.requests.post", return_value=mock_response):
            result = client.generate(model="llama3.2", prompt="hello", system="translate")

        assert result == "translated text"

    def test_generate_without_system_omits_key(self):
        from app.services.ollama_client import OllamaClient
        client = OllamaClient(base_url="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "ok"}

        with patch("app.services.ollama_client.requests.post", return_value=mock_response) as mock_post:
            client.generate(model="llama3.2", prompt="hello")

        payload = mock_post.call_args[1]["json"]
        assert "system" not in payload

    def test_non_200_raises_runtime_error(self):
        from app.services.ollama_client import OllamaClient
        client = OllamaClient(base_url="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "internal server error"

        with patch("app.services.ollama_client.requests.post", return_value=mock_response):
            with pytest.raises(RuntimeError, match="Ollama returned 500"):
                client.generate(model="llama3.2", prompt="hello")

    def test_connection_error_raises_runtime_error(self):
        from app.services.ollama_client import OllamaClient
        client = OllamaClient(base_url="http://localhost:11434")

        with patch("app.services.ollama_client.requests.post", side_effect=req.ConnectionError("refused")):
            with pytest.raises(RuntimeError, match="Ollama unreachable"):
                client.generate(model="llama3.2", prompt="hello")

    def test_posts_to_generate_endpoint(self):
        from app.services.ollama_client import OllamaClient
        client = OllamaClient(base_url="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "ok"}

        with patch("app.services.ollama_client.requests.post", return_value=mock_response) as mock_post:
            client.generate(model="llama3.2", prompt="hello")

        called_url = mock_post.call_args[0][0]
        assert called_url == "http://localhost:11434/api/generate"

    def test_stream_is_false_in_payload(self):
        from app.services.ollama_client import OllamaClient
        client = OllamaClient(base_url="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "ok"}

        with patch("app.services.ollama_client.requests.post", return_value=mock_response) as mock_post:
            client.generate(model="llama3.2", prompt="hello")

        payload = mock_post.call_args[1]["json"]
        assert payload["stream"] is False
