"""Test Playground."""

from typing import Any, List
from unittest.mock import patch

import pytest
from gpt_index.embeddings.base import BaseEmbedding

from gpt_index.embeddings.openai import OpenAIEmbedding
from gpt_index.indices.list.base import GPTListIndex
from gpt_index.indices.service_context import ServiceContext
from gpt_index.indices.tree.base import GPTTreeIndex
from gpt_index.indices.vector_store.base import GPTVectorStoreIndex
from gpt_index.llm_predictor.base import LLMPredictor
from gpt_index.playground import DEFAULT_INDEX_CLASSES, DEFAULT_MODES, Playground
from gpt_index.readers.schema.base import Document
from tests.mock_utils.mock_decorator import patch_common
from tests.mock_utils.mock_predict import mock_llmpredictor_predict


class MockEmbedding(BaseEmbedding):
    def _get_text_embedding(self, text: str) -> List[float]:
        """Mock get text embedding."""
        # assume dimensions are 5
        if text == "They're taking the Hobbits to Isengard!":
            return [1, 0, 0, 0, 0]
        elif text == "I can't carry it for you.":
            return [0, 1, 0, 0, 0]
        elif text == "But I can carry you!":
            return [0, 0, 1, 0, 0]
        else:
            raise ValueError("Invalid text for `mock_get_text_embedding`.")

    def _get_query_embedding(self, query: str) -> List[float]:
        """Mock get query embedding."""
        del query
        return [0, 0, 1, 0, 0]


def test_get_set_compare(
    mock_service_context: ServiceContext,
) -> None:
    """Test basic comparison of indices."""
    mock_service_context.embed_model = MockEmbedding()
    documents = [Document("They're taking the Hobbits to Isengard!")]

    indices = [
        GPTVectorStoreIndex.from_documents(
            documents=documents, service_context=mock_service_context
        ),
        GPTListIndex.from_documents(documents, service_context=mock_service_context),
        GPTTreeIndex.from_documents(
            documents=documents, service_context=mock_service_context
        ),
    ]

    playground = Playground(indices=indices)  # type: ignore

    assert len(playground.indices) == 3
    assert len(playground.modes) == len(DEFAULT_MODES)

    results = playground.compare("Who is?", to_pandas=False)
    assert len(results) > 0
    assert len(results) <= 3 * len(DEFAULT_MODES)

    playground.indices = [
        GPTVectorStoreIndex.from_documents(
            documents=documents, service_context=mock_service_context
        )
    ]
    playground.modes = ["default", "summarize"]

    assert len(playground.indices) == 1
    assert len(playground.modes) == 2

    with pytest.raises(ValueError):
        playground.modes = []


def test_from_docs(
    mock_service_context: ServiceContext,
) -> None:
    """Test initialization via a list of documents."""
    mock_service_context.embed_model = MockEmbedding()
    documents = [
        Document("I can't carry it for you."),
        Document("But I can carry you!"),
    ]

    playground = Playground.from_docs(
        documents=documents, service_context=mock_service_context
    )

    assert len(playground.indices) == len(DEFAULT_INDEX_CLASSES)
    assert len(playground.modes) == len(DEFAULT_MODES)

    with pytest.raises(ValueError):
        playground = Playground.from_docs(
            documents=documents, modes=[], service_context=mock_service_context
        )


def test_validation() -> None:
    """Test validation of indices and modes."""
    with pytest.raises(ValueError):
        _ = Playground(indices=["GPTSimpleVectorIndex"])  # type: ignore

    with pytest.raises(ValueError):
        _ = Playground(
            indices=[GPTVectorStoreIndex, GPTListIndex, GPTTreeIndex]  # type: ignore
        )

    with pytest.raises(ValueError):
        _ = Playground(indices=[])  # type: ignore

    with pytest.raises(TypeError):
        _ = Playground(modes=["default"])  # type: ignore
