import pytest
from unittest.mock import MagicMock, patch


SAMPLE_SEGMENTS = [
    {"start": 0.0, "end": 2.5, "text": "Hola mundo"},
    {"start": 3.0, "end": 5.0, "text": "Como estas"},
]


class TestCollectContext:
    def test_calls_ollama_once(self):
        from app.services.llm_translator import collect_context
        mock_client = MagicMock()
        mock_client.generate.return_value = "Context summary"

        with patch("app.services.llm_translator.OllamaClient", return_value=mock_client):
            result = collect_context(SAMPLE_SEGMENTS, model="llama3.2")

        assert mock_client.generate.call_count == 1
        assert result == "Context summary"

    def test_returns_context_string(self):
        from app.services.llm_translator import collect_context
        mock_client = MagicMock()
        mock_client.generate.return_value = "This is a Spanish greeting video"

        with patch("app.services.llm_translator.OllamaClient", return_value=mock_client):
            result = collect_context(SAMPLE_SEGMENTS, model="llama3.2")

        assert isinstance(result, str)
        assert "Spanish" in result

    def test_prompt_contains_segment_text(self):
        from app.services.llm_translator import collect_context
        mock_client = MagicMock()
        mock_client.generate.return_value = "context"

        with patch("app.services.llm_translator.OllamaClient", return_value=mock_client):
            collect_context(SAMPLE_SEGMENTS, model="llama3.2")

        call_kwargs = mock_client.generate.call_args
        prompt = call_kwargs.kwargs.get("prompt") or call_kwargs.args[1]
        assert "Hola mundo" in prompt

    def test_prompt_contains_all_segments(self):
        from app.services.llm_translator import collect_context
        mock_client = MagicMock()
        mock_client.generate.return_value = "context"

        with patch("app.services.llm_translator.OllamaClient", return_value=mock_client):
            collect_context(SAMPLE_SEGMENTS, model="llama3.2")

        call_kwargs = mock_client.generate.call_args
        prompt = call_kwargs.kwargs.get("prompt") or call_kwargs.args[1]
        assert "Como estas" in prompt

    def test_truncates_long_passage(self):
        from app.services.llm_translator import collect_context
        long_segments = [{"start": 0.0, "end": 1.0, "text": "word " * 500}]
        mock_client = MagicMock()
        mock_client.generate.return_value = "context"

        with patch("app.services.llm_translator.OllamaClient", return_value=mock_client):
            collect_context(long_segments, model="llama3.2")

        call_kwargs = mock_client.generate.call_args
        prompt = call_kwargs.kwargs.get("prompt") or call_kwargs.args[1]
        assert len(prompt) <= 2000

    def test_uses_default_system_prompt_when_none_given(self):
        from app.services.llm_translator import collect_context, DEFAULT_CONTEXT_SYSTEM
        mock_client = MagicMock()
        mock_client.generate.return_value = "context"

        with patch("app.services.llm_translator.OllamaClient", return_value=mock_client):
            collect_context(SAMPLE_SEGMENTS, model="llama3.2")

        call_kwargs = mock_client.generate.call_args
        system = call_kwargs.kwargs.get("system") or call_kwargs.args[2]
        assert system == DEFAULT_CONTEXT_SYSTEM

    def test_accepts_custom_system_prompt(self):
        from app.services.llm_translator import collect_context
        mock_client = MagicMock()
        mock_client.generate.return_value = "context"

        with patch("app.services.llm_translator.OllamaClient", return_value=mock_client):
            collect_context(SAMPLE_SEGMENTS, model="llama3.2", custom_system_prompt="Custom prompt")

        call_kwargs = mock_client.generate.call_args
        system = call_kwargs.kwargs.get("system") or call_kwargs.args[2]
        assert system == "Custom prompt"


class TestTranslateSegment:
    def test_returns_translated_text(self):
        from app.services.llm_translator import translate_segment
        mock_client = MagicMock()
        mock_client.generate.return_value = "Hello world"

        with patch("app.services.llm_translator.OllamaClient", return_value=mock_client):
            result = translate_segment("Hola mundo", context="Spanish greeting", model="llama3.2")

        assert result == "Hello world"

    def test_passes_context_in_system_prompt(self):
        from app.services.llm_translator import translate_segment
        mock_client = MagicMock()
        mock_client.generate.return_value = "Hello"

        with patch("app.services.llm_translator.OllamaClient", return_value=mock_client):
            translate_segment("Hola", context="Spanish informal greeting video", model="llama3.2")

        call_kwargs = mock_client.generate.call_args
        system = call_kwargs.kwargs.get("system") or call_kwargs.args[2]
        assert "Spanish informal greeting video" in system

    def test_passes_text_as_prompt(self):
        from app.services.llm_translator import translate_segment
        mock_client = MagicMock()
        mock_client.generate.return_value = "translated"

        with patch("app.services.llm_translator.OllamaClient", return_value=mock_client):
            translate_segment("Hola mundo", context="ctx", model="llama3.2")

        call_kwargs = mock_client.generate.call_args
        prompt = call_kwargs.kwargs.get("prompt") or call_kwargs.args[1]
        assert prompt == "Hola mundo"

    def test_falls_back_to_original_on_failure(self):
        from app.services.llm_translator import translate_segment
        mock_client = MagicMock()
        mock_client.generate.side_effect = RuntimeError("Connection refused")

        with patch("app.services.llm_translator.OllamaClient", return_value=mock_client):
            result = translate_segment("Hola mundo", context="context", model="llama3.2")

        assert result == "Hola mundo"
