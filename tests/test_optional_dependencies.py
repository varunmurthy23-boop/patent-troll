import builtins

import pytest

from patent_troll.providers import (
    MissingProviderDependency,
    load_anthropic_client_class,
    load_openai_client_class,
)


def block_import(monkeypatch, package: str) -> None:
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == package:
            raise ImportError(f"blocked {package} for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)


def test_missing_openai_sdk_has_install_guidance(monkeypatch) -> None:
    block_import(monkeypatch, "openai")

    with pytest.raises(MissingProviderDependency, match=r"patent-troll\[openai\]"):
        load_openai_client_class()


def test_missing_anthropic_sdk_has_install_guidance(monkeypatch) -> None:
    block_import(monkeypatch, "anthropic")

    with pytest.raises(MissingProviderDependency, match=r"patent-troll\[anthropic\]"):
        load_anthropic_client_class()
