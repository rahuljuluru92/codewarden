from pathlib import Path

import pytest

from codewarden.indexing.chunker import chunk_parsed_file
from codewarden.indexing.store import CodeIndex
from codewarden.parsing.parser import parse_file

FIXTURES = Path(__file__).resolve().parent / "fixtures"

FIXTURE_FILES = [
    "user_controller.py",
    "user_controller.ts",
    "order_service.py",
    "math_utils.py",
]


@pytest.fixture()
def index(tmp_path) -> CodeIndex:
    idx = CodeIndex(persist_path=str(tmp_path / "chroma_db"))
    for name in FIXTURE_FILES:
        parsed = parse_file(FIXTURES / name)
        idx.index_parsed_file(parsed)
    return idx


def test_indexing_produces_expected_chunk_count():
    parsed = parse_file(FIXTURES / "order_service.py")
    chunks = chunk_parsed_file(parsed)
    # 2 functions + 1 class chunk
    assert len(chunks) == 3
    kinds = {c.metadata["kind"] for c in chunks}
    assert kinds == {"function", "class"}


def test_query_returns_relevant_business_logic_chunk(index: CodeIndex):
    results = index.query("calculate order total with a percentage discount", n_results=3)
    assert len(results) > 0
    top_names = [r.metadata["name"] for r in results]
    assert "calculate_total" in top_names
    # the top hit should not be the unrelated math utility
    assert results[0].metadata["name"] != "is_prime"


def test_query_returns_relevant_controller_chunk(index: CodeIndex):
    results = index.query("HTTP handler that fetches a user by id", n_results=3)
    top_names = [r.metadata["name"] for r in results]
    assert "get_user" in top_names or "getUser" in top_names


def test_query_with_metadata_filter_restricts_to_language(index: CodeIndex):
    results = index.query("class with methods", n_results=10, where={"language": "typescript"})
    assert len(results) > 0
    assert all(r.metadata["language"] == "typescript" for r in results)


def test_index_count_matches_total_chunks(index: CodeIndex):
    total_expected = sum(len(chunk_parsed_file(parse_file(FIXTURES / f))) for f in FIXTURE_FILES)
    assert index.count() == total_expected


def test_unrelated_query_ranks_math_utils_higher(index: CodeIndex):
    results = index.query("check if a number is prime using trial division", n_results=3)
    top_names = [r.metadata["name"] for r in results]
    assert "is_prime" in top_names
