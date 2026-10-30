"""Non-secret first-use defaults injected from a Git-ignored local file.

Runtime resolution order (first existing candidate wins; no other implicit source
is ever consulted):

1. ``SUMMIT_FIRST_USE_DEFAULTS``: an explicit JSON file path from the environment;
2. the packaged app bundle resource ``<App>/Contents/Resources/first-use-defaults.json``.

The repository-local development file ``.local/first-use/defaults.json`` is *not* a
runtime source. Reading it implicitly would make the same code behave differently
on a machine that happens to have the file than on CI or a colleague's machine.
The development preview runner (``scripts/run_dev.py``) points
``SUMMIT_FIRST_USE_DEFAULTS`` at that file when it exists; packaging copies it into
the bundle through :func:`read_first_use_defaults_file`.

Only these four non-secret keys are accepted; the names are fixed:

========================  ========================
key                       provider settings field
========================  ========================
``feishu_app_id``         ``feishu.app_id``
``feishu_redirect_uri``   ``feishu.redirect_uri``
``embedding_base_url``    ``embedding.base_url``
``rerank_base_url``       ``rerank.base_url``
========================  ========================

Secret-shaped key names (``/secret|key|token|password|credential/i``) and unknown
keys fail closed: loading raises :class:`FirstUseDefaultsError` instead of
silently ignoring the entry. Values are checked with the ordinary provider
settings validators (Alibaba Cloud HTTPS host allowlist, loopback callback,
supported base-URL paths); a rejected value is reported the same way as any other
settings validation failure, and neither log output nor error text ever contains
the injected value: only the source path and field names are reported.

An explicit ``SUMMIT_FIRST_USE_DEFAULTS`` path that cannot be read is an error and
does not fall through to the next candidate. Injected values are defaults only: a
non-empty value already stored in the profile wins, and the settings UI can still
override them.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from .settings import ProviderSettings

_LOGGER = logging.getLogger(__name__)

DEFAULTS_ENV_VAR = "SUMMIT_FIRST_USE_DEFAULTS"
BUNDLE_RESOURCE_NAME = "first-use-defaults.json"
REPO_DEFAULTS_RELATIVE_PATH = Path(".local") / "first-use" / "defaults.json"

# key -> (settings section, field name); the mapping is the fixed public contract.
DEFAULTS_FIELD_MAP: Mapping[str, tuple[str, str]] = {
    "feishu_app_id": ("feishu", "app_id"),
    "feishu_redirect_uri": ("feishu", "redirect_uri"),
    "embedding_base_url": ("embedding", "base_url"),
    "rerank_base_url": ("rerank", "base_url"),
}
ALLOWED_DEFAULT_KEYS = frozenset(DEFAULTS_FIELD_MAP)

_SECRET_KEY_PATTERN = re.compile(r"secret|key|token|password|credential", re.IGNORECASE)


def is_secret_shaped_key(name: str) -> bool:
    """True when a key name looks like a secret and must never be injected."""
    return _SECRET_KEY_PATTERN.search(name) is not None


class FirstUseDefaultsError(RuntimeError):
    """Fail-closed rejection of a first-use defaults file."""

    def __init__(
        self,
        code: str,
        *,
        source: Path | None = None,
        fields: tuple[str, ...] = (),
    ) -> None:
        self.code = code
        self.source = source
        self.fields = fields
        parts = [code]
        if source is not None:
            parts.append(f"source={source}")
        if fields:
            parts.append("fields=" + ",".join(fields))
        super().__init__(" ".join(parts))


@dataclass(frozen=True)
class FirstUseDefaults:
    """Validated non-secret defaults plus the file they came from."""

    values: Mapping[str, str] = field(default_factory=dict)
    source: Path | None = None

    @classmethod
    def empty(cls) -> FirstUseDefaults:
        return cls()

    def apply(self, raw: object) -> object:
        """Fill absent or empty string fields of a raw settings mapping.

        A section that is present but not a mapping is left exactly as it is so
        the ordinary validation still rejects the corrupted profile. Injecting an
        empty mapping over it would mask that failure and turn a corrupt profile
        into a silently accepted one.
        """
        if not isinstance(raw, dict):
            return raw
        merged: dict[str, object] = {
            key: dict(value) if isinstance(value, dict) else value for key, value in raw.items()
        }
        for key, value in self.values.items():
            section, field_name = DEFAULTS_FIELD_MAP[key]
            if section in merged:
                section_value = merged[section]
                if not isinstance(section_value, dict):
                    # Corrupted section: never repaired by injection, and never
                    # silently repaired into something valid.
                    continue
            else:
                section_value = {}
                merged[section] = section_value
            if field_name in section_value:
                current = section_value[field_name]
                if isinstance(current, str):
                    if current.strip():
                        # An explicit non-empty value always wins.
                        continue
                else:
                    # Present but not a string: a corrupted field. Injection must
                    # never repair it, otherwise a profile that fails closed
                    # without injection would be silently accepted with it.
                    continue
            section_value[field_name] = value
        return merged


def stored_document(document: object, *, defaults: FirstUseDefaults | None = None) -> object:
    """Return the on-disk settings document for an effective settings dump.

    The stored profile records only explicit user overrides. For the four
    injectable fields, a value equal to the current injected default, or an empty
    string, is removed from the document instead of being written. The key then
    falls back to the pydantic model default on the next read, which lets
    :meth:`FirstUseDefaults.apply` inject whatever default the current build or
    environment provides. Writing ``""`` would be rejected by the existing
    base-URL and callback validators, so the key is dropped rather than blanked.
    """
    if not isinstance(document, dict):
        return document
    result: dict[str, object] = {
        key: dict(value) if isinstance(value, dict) else value for key, value in document.items()
    }
    injected = defaults.values if defaults is not None else {}
    for key, (section, field_name) in DEFAULTS_FIELD_MAP.items():
        section_value = result.get(section)
        if not isinstance(section_value, dict):
            continue
        current = section_value.get(field_name)
        if current is None or current == "" or current == injected.get(key):
            section_value.pop(field_name, None)
    return result


def read_first_use_defaults_file(path: Path) -> FirstUseDefaults:
    """Read and validate one defaults file. Raises :class:`FirstUseDefaultsError`."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        raise FirstUseDefaultsError("first_use_defaults_unavailable", source=path) from None
    try:
        payload = json.loads(text)
    except ValueError:
        raise FirstUseDefaultsError("first_use_defaults_invalid", source=path) from None
    if not isinstance(payload, dict):
        raise FirstUseDefaultsError("first_use_defaults_invalid", source=path)
    secret_keys = sorted(str(key) for key in payload if is_secret_shaped_key(str(key)))
    if secret_keys:
        raise FirstUseDefaultsError(
            "first_use_defaults_secret_key", source=path, fields=tuple(secret_keys)
        )
    unknown_keys = sorted(str(key) for key in payload if key not in ALLOWED_DEFAULT_KEYS)
    if unknown_keys:
        raise FirstUseDefaultsError(
            "first_use_defaults_unknown_key", source=path, fields=tuple(unknown_keys)
        )
    values: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(value, str):
            raise FirstUseDefaultsError(
                "first_use_defaults_invalid", source=path, fields=(str(key),)
            )
        stripped = value.strip()
        if not stripped:
            continue
        values[str(key)] = stripped
    _validate_default_values(values, source=path)
    if values:
        _LOGGER.info(
            "first-use defaults loaded source=%s fields=%s", path, ",".join(sorted(values))
        )
    return FirstUseDefaults(values=values, source=path)


def load_first_use_defaults(
    *,
    environ: Mapping[str, str] | None = None,
    bundle_path: Path | None = None,
) -> FirstUseDefaults:
    """Resolve the first usable defaults source; empty when none exists.

    Only the explicit environment path and the packaged bundle resource are
    consulted, so the same build behaves identically on every machine.
    """
    environment = os.environ if environ is None else environ
    explicit = environment.get(DEFAULTS_ENV_VAR, "").strip()
    candidates: list[Path] = []
    if explicit:
        explicit_path = Path(explicit).expanduser()
        candidates.append(explicit_path)
        if not explicit_path.is_file():
            # An explicitly requested file is never silently skipped.
            raise FirstUseDefaultsError("first_use_defaults_unavailable", source=explicit_path)
    resources = bundle_path if bundle_path is not None else _bundle_resources_dir()
    if resources is not None:
        candidates.append(resources / BUNDLE_RESOURCE_NAME)
    for candidate in candidates:
        if candidate.is_file():
            return read_first_use_defaults_file(candidate)
    _LOGGER.debug("first-use defaults not configured; using built-in defaults")
    return FirstUseDefaults.empty()


def _validate_default_values(values: Mapping[str, str], *, source: Path) -> None:
    if not values:
        return
    payload: dict[str, dict[str, object]] = {}
    for key, value in values.items():
        section, field_name = DEFAULTS_FIELD_MAP[key]
        payload.setdefault(section, {})[field_name] = value
        if section == "embedding":
            payload[section].update(
                provider="dashscope",
                model="qwen3.7-text-embedding",
                dimensions=1024,
            )
        elif section == "rerank":
            payload[section].update(
                provider="dashscope",
                model="qwen3.7-text-rerank",
                dimensions=1024,
            )
    try:
        ProviderSettings.model_validate(payload)
    except ValidationError as exc:
        # Report field locations only: the offending value must not leak.
        locations = tuple(
            sorted(".".join(str(part) for part in error.get("loc", ())) for error in exc.errors())
        )
        raise FirstUseDefaultsError(
            "first_use_defaults_value_invalid", source=source, fields=locations
        ) from None


def _bundle_resources_dir() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    try:
        executable = Path(sys.executable).resolve()
    except OSError:  # pragma: no cover - defensive, resolve() rarely fails
        return None
    for parent in executable.parents:
        if parent.name == "Resources" and parent.parent.name == "Contents":
            return parent
    return None
