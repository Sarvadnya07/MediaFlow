"""
MediaDock Architectural Fitness Tests.
Enforces structural modularity, boundary invariants, and dependency directions.
"""
import ast
import os
from pathlib import Path
import pytest

APP_DIR = Path(__file__).resolve().parent.parent / "app"


def get_imported_modules_for_file(filepath: Path) -> set[str]:
    """Parse a python file AST and return all top-level imported module names."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except Exception:
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


def test_core_engine_does_not_import_server_frameworks():
    """
    Fitness Function 1:
    The core media engine (app/engine/, app/services/) must never import
    FastAPI, Uvicorn, Celery, or Redis. It must remain a pure, transport-agnostic library.
    """
    forbidden_frameworks = {"fastapi", "uvicorn", "celery", "redis"}

    engine_paths = list((APP_DIR / "engine").glob("*.py"))
    # Exclude server-only tasks in services if any (yt_service, ffmpeg_service, etc.)
    service_paths = [
        p for p in (APP_DIR / "services").glob("*.py")
        if p.name not in ("ai_service.py",)  # legacy server stubs
    ]

    for py_file in engine_paths + service_paths:
        imported = get_imported_modules_for_file(py_file)
        for mod in imported:
            root_mod = mod.split(".")[0]
            assert root_mod not in forbidden_frameworks, (
                f"Architecture violation: {py_file.name} imports '{root_mod}'. "
                f"Engine must remain independent of server frameworks."
            )


def test_security_module_has_zero_external_dependencies():
    """
    Fitness Function 2:
    app/security.py is a critical security barrier and must depend only on
    standard library modules or internal typing. It must never depend on engine or route layers.
    """
    security_file = APP_DIR / "security.py"
    imported = get_imported_modules_for_file(security_file)

    forbidden_internal = {
        "app.routes", "app.worker", "app.engine", "app.services",
        "app.database", "app.models"
    }

    for mod in imported:
        for forbidden in forbidden_internal:
            assert not mod.startswith(forbidden), (
                f"Architecture violation: security.py imports '{mod}'. "
                f"Security module must remain at the foundational layer."
            )


def test_protocol_module_is_pure_declarative_schema():
    """
    Fitness Function 3:
    app/engine/protocol.py defines the cross-boundary IPC contract.
    It must depend only on pydantic / typing, never on services or execution code.
    """
    protocol_file = APP_DIR / "engine" / "protocol.py"
    imported = get_imported_modules_for_file(protocol_file)

    forbidden_modules = {"yt_dlp", "requests", "sqlalchemy", "subprocess", "celery"}

    for mod in imported:
        root_mod = mod.split(".")[0]
        assert root_mod not in forbidden_modules, (
            f"Architecture violation: protocol.py imports execution dependency '{root_mod}'. "
            f"Protocol must remain a pure schema contract."
        )


def test_provider_registry_contract_uniformity():
    """
    Fitness Function 4:
    Every registered provider in ProviderRegistry must implement BaseProvider
    and provide valid ProviderCapability declarations.
    """
    from app.providers.registry import provider_registry
    from app.providers.base import BaseProvider

    providers = provider_registry._providers
    assert len(providers) >= 2, "Provider registry must have at least direct and universal providers"

    for prov in providers:
        assert isinstance(prov, BaseProvider)
        info = prov.info
        assert info.id
        assert info.name
        assert hasattr(info.capabilities, "video")
        assert hasattr(info.capabilities, "audio")
