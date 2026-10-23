from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_validation_has_no_research_dependency_or_runtime_discovery():
    for path in (ROOT / "strategy-validation/src/crypto_quant_validation").glob("*.py"):
        source = path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(not alias.name.startswith("crypto_quant_research") for alias in node.names), path
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("crypto_quant_research"), path
            if isinstance(node, ast.Call):
                assert not (isinstance(node.func, ast.Name) and node.func.id == "__import__"), path
                assert not (isinstance(node.func, ast.Attribute) and node.func.attr in {"import_module", "entry_points"}), path
        assert "crypto_quant_research" not in source, path
    assert '"crypto-quant-research' not in (ROOT / "strategy-validation/pyproject.toml").read_text()


def test_public_roots_import_lazily_in_either_order_and_validation_alone():
    for code in (
        "import crypto_quant_validation; import sys; assert 'crypto_quant_research' not in sys.modules",
        "import crypto_quant_research; import crypto_quant_validation",
        "import crypto_quant_validation; import crypto_quant_research",
    ):
        subprocess.run([sys.executable, "-B", "-c", code], check=True, env=os.environ.copy())


def test_public_runtime_verifier_keyword_and_composition_wiring():
    import inspect
    from crypto_quant_validation import CandidateProvenanceVerifier, validate_candidate, validate_target_candidate
    assert CandidateProvenanceVerifier is not None
    for entry in (validate_candidate, validate_target_candidate):
        parameter = inspect.signature(entry).parameters["candidate_provenance_verifier"]
        assert parameter.kind == inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is None
    for version in (1, 2, 3, 5, 6):
        path = ROOT / f"tests/integration/test_integration_v{version}.py"
        tree = ast.parse(path.read_text())
        assert any(isinstance(node, ast.ImportFrom) and node.module == "crypto_quant_research" and any(alias.name == "verify_candidate_provenance" for alias in node.names) for node in ast.walk(tree))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and ((isinstance(node.func, ast.Name) and node.func.id in {"validate_candidate", "validate_target_candidate"}) or (isinstance(node.func, ast.Attribute) and node.func.attr in {"validate_candidate", "validate_target_candidate"})):
                assert any(keyword.arg == "candidate_provenance_verifier" and isinstance(keyword.value, ast.Name) and keyword.value.id == "verify_candidate_provenance" for keyword in node.keywords)
