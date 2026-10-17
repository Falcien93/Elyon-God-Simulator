"""Character AI settings. The player key stays in its own file and out of logs."""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path

SETTINGS_VERSION = 1
LOCAL = "local"
GROK = "grok"
PROVIDER_IDS = (LOCAL, GROK)
SETTINGS_NAME = "elyon-ai-settings.json"
KEY_NAME = "elyon-ai-key.txt"
MIN_KEY_LENGTH = 8
MAX_KEY_LENGTH = 512
# Names a pasted key might use inside the settings record. They are lifted out.
KEY_FIELDS = (
    "apiKey",
    "api_key",
    "xaiKey",
    "xai_key",
    "grokKey",
    "grok_key",
    "key",
    "token",
    "secret",
)

log = logging.getLogger("elyon.ai")

_secrets: set[str] = set()
_LOG_PATCHED = False


def project_saved_dir():
    """Local settings folder for this Unreal project. Gitignored."""
    return Path(__file__).resolve().parents[1] / "Saved" / "Settings"


def remember_secret(value):
    """Remember a player key so later log lines cannot print it."""
    if isinstance(value, str) and len(value) >= MIN_KEY_LENGTH:
        _secrets.add(value)


def redact(value):
    if not isinstance(value, str) or not value or not _secrets:
        return value
    redacted = value
    for secret in tuple(_secrets):
        if secret and secret in redacted:
            redacted = redacted.replace(secret, "[redacted]")
    return redacted


def _redact_obj(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, tuple):
        return tuple(_redact_obj(item) for item in value)
    if isinstance(value, list):
        return [_redact_obj(item) for item in value]
    if isinstance(value, dict):
        return {_redact_obj(key): _redact_obj(item) for key, item in value.items()}
    return value


def _exception_text(info):
    try:
        return "".join(traceback.format_exception(*info))
    except Exception:
        return ""


def _clean_exc(exc):
    if not exc or not _secrets:
        return exc
    if exc is True:
        info = sys.exc_info()
    elif isinstance(exc, BaseException):
        info = (type(exc), exc, exc.__traceback__)
    elif isinstance(exc, tuple) and len(exc) == 3:
        info = exc
    else:
        return exc
    if info[1] is None:
        return exc
    if any(secret and secret in _exception_text(info) for secret in tuple(_secrets)):
        clean = RuntimeError("redacted")
        return (RuntimeError, clean, None)
    return exc


def install_log_redaction():
    """Replace logger output that would include a key already seen by this process."""
    global _LOG_PATCHED
    if _LOG_PATCHED:
        return
    original = logging.Logger._log

    def _log(self, level, msg, args, *rest, **kwargs):
        if isinstance(msg, str):
            msg = redact(msg)
        args = _redact_obj(args)
        if rest:
            cleaned = list(rest)
            cleaned[0] = _clean_exc(cleaned[0])
            rest = tuple(cleaned)
        if "exc_info" in kwargs:
            kwargs["exc_info"] = _clean_exc(kwargs["exc_info"])
        return original(self, level, msg, args, *rest, **kwargs)

    logging.Logger._log = _log
    _LOG_PATCHED = True


def normalize_provider(value, *, fallback=False):
    if isinstance(value, str):
        name = value.strip().lower()
        if name in PROVIDER_IDS:
            return name
    if fallback:
        return LOCAL
    raise ValueError("unknown provider")


def normalize_key(value):
    """Return a key safe to store, or empty when the player cleared the field.

    A rejected key raises ValueError with a fixed message that does not include it.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        raise TypeError("key must be a string")
    text = value.strip()
    if text == "":
        return ""
    if len(text) < MIN_KEY_LENGTH or len(text) > MAX_KEY_LENGTH:
        raise ValueError("key was not stored")
    if any(mark in text for mark in ("\r", "\n", "\x00")):
        raise ValueError("key was not stored")
    remember_secret(text)
    return text


@dataclass(frozen=True)
class AiSettings:
    """Public settings. This object has no field for a player key."""

    provider: str = LOCAL
    version: int = SETTINGS_VERSION

    def __post_init__(self):
        object.__setattr__(self, "provider", normalize_provider(self.provider, fallback=False))
        object.__setattr__(self, "version", SETTINGS_VERSION)

    def to_public(self, key_present):
        return {
            "version": self.version,
            "provider": self.provider,
            "keyPresent": bool(key_present),
        }


class AiSettingsStore:
    """Writes the choice and the key as two files. Only the choice is JSON."""

    def __init__(self, root=None):
        self.root = Path(root) if root is not None else project_saved_dir()
        self.settings_path = self.root / SETTINGS_NAME
        self.key_path = self.root / KEY_NAME
        self.key_reads = 0

    def __repr__(self):
        return "AiSettingsStore(local)"

    def load(self):
        if not self.settings_path.is_file():
            return AiSettings()
        try:
            raw = self.settings_path.read_text(encoding="utf-8")
        except OSError:
            log.info("ai settings file could not be read; using the bundled provider")
            return AiSettings()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            log.info("ai settings file is unreadable; using the bundled provider")
            self._write_public(AiSettings(), self.key_present())
            return AiSettings()
        if not isinstance(payload, dict):
            log.info("ai settings file is unreadable; using the bundled provider")
            self._write_public(AiSettings(), self.key_present())
            return AiSettings()
        self._lift_stray_keys(payload)
        provider = normalize_provider(payload.get("provider", LOCAL), fallback=True)
        return AiSettings(provider=provider)

    def key_present(self):
        return self._peek_key() != ""

    def read_key(self):
        """Read the player key. Call this only for a provider that asks for one."""
        self.key_reads += 1
        return self._peek_key()

    def save(self, settings, key=None):
        """Persist the provider. Pass key="" to clear it, or omit key to leave it."""
        if not isinstance(settings, AiSettings):
            settings = AiSettings(provider=getattr(settings, "provider", LOCAL))
        stored = None
        if key is not None:
            stored = normalize_key(key)
            if stored == "":
                self._delete_key()
            else:
                self._write_text(self.key_path, stored + "\n", 0o600)
        self._write_public(settings, self._key_will_be_present(stored))
        log.info("saved character provider %s key_present=%s", settings.provider, self.key_present())
        return settings

    def _key_will_be_present(self, stored):
        if stored is None:
            return self.key_present()
        return stored != ""

    def _peek_key(self):
        if not self.key_path.is_file():
            return ""
        try:
            text = self.key_path.read_text(encoding="utf-8").strip()
        except OSError:
            log.info("ai key file could not be read")
            return ""
        if text == "":
            return ""
        try:
            return normalize_key(text)
        except ValueError:
            log.info("ai key file was not usable")
            return ""

    def _lift_stray_keys(self, payload):
        found = []
        removed = False
        for name in KEY_FIELDS:
            if name not in payload:
                continue
            removed = True
            value = payload.pop(name)
            if isinstance(value, str) and value.strip():
                text = value.strip()
                found.append(text)
                remember_secret(text)
        if not removed:
            return
        chosen = ""
        for candidate in found:
            try:
                chosen = normalize_key(candidate)
            except ValueError:
                continue
            if chosen:
                break
        if chosen:
            self._write_text(self.key_path, chosen + "\n", 0o600)
        provider = normalize_provider(payload.get("provider", LOCAL), fallback=True)
        self._write_public(AiSettings(provider=provider), bool(chosen))
        log.info("moved a player key out of the settings record")

    def _write_public(self, settings, key_present):
        body = settings.to_public(key_present)
        self._write_text(self.settings_path, json.dumps(body, indent=2, sort_keys=True) + "\n", 0o644)

    def _delete_key(self):
        try:
            self.key_path.unlink()
        except FileNotFoundError:
            return
        except OSError:
            log.info("ai key file could not be cleared")

    def _write_text(self, path, data, mode):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        fd = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            log.info("ai settings could not be written")
            raise
        os.replace(temporary, path)
        try:
            os.chmod(path, mode)
        except OSError:
            log.info("ai settings file mode could not be set")


install_log_redaction()
