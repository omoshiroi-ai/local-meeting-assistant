"""LLM — streaming Qwen2.5 wrapper via mlx-lm.

Designed to be called from a Textual worker thread.
Yields tokens one at a time so the UI can stream them as they arrive.

Usage::

    llm = LLM()
    llm.load()
    for token in llm.stream(messages):
        app.call_from_thread(panel.stream_token, token)
"""

import logging
from collections.abc import Iterator

from src.config import LLM_MAX_NEW_TOKENS, LLM_MODEL

logger = logging.getLogger(__name__)


class LLM:
    """Wraps mlx-lm generate with lazy loading and token streaming."""

    def __init__(self, model_name: str = LLM_MODEL) -> None:
        self._model_name = model_name
        self._model = None
        self._tokenizer = None

    def load(self) -> None:
        """Load model weights into MLX. Safe to call multiple times."""
        if self._model is not None:
            return

        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import LocalEntryNotFoundError
        from mlx_lm import load

        logger.info("Loading LLM: %s", self._model_name)

        try:
            local_path = snapshot_download(
                repo_id=self._model_name,
                local_files_only=True,
            )
        except (LocalEntryNotFoundError, Exception) as exc:
            raise RuntimeError(
                f"LLM '{self._model_name}' not found in local cache.\n"
                f"Download it first:\n"
                f"  uv run python scripts/setup_models.py\n"
                f"Original error: {exc}"
            ) from exc

        self._model, self._tokenizer = load(local_path)
        logger.info("LLM ready.")

    def stream(
        self,
        messages: list[dict],
        max_tokens: int = LLM_MAX_NEW_TOKENS,
    ) -> Iterator[str]:
        """Yield tokens one at a time. Blocks until generation is complete."""
        if self._model is None:
            self.load()

        from mlx_lm import stream_generate

        prompt = self._tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False,
        )

        logger.debug("LLM generating (max_tokens=%d)", max_tokens)
        for response in stream_generate(
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
        ):
            yield response.text

    def generate(
        self,
        messages: list[dict],
        max_tokens: int = LLM_MAX_NEW_TOKENS,
    ) -> str:
        """Non-streaming completion (collects token iterator)."""
        return "".join(self.stream(messages, max_tokens=max_tokens))

    @property
    def is_loaded(self) -> bool:
        return self._model is not None
