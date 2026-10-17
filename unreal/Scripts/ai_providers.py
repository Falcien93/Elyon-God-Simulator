"""Character AI providers. Interface and stubs only: nothing here calls the network."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod

from ai_settings import GROK, LOCAL, redact, remember_secret

log = logging.getLogger("elyon.ai")

LOCAL_STUB = "The bundled voice is quiet in this build."
PREMIUM_STUB = "The premium voice is quiet in this build."


def _present(key):
    if not isinstance(key, str):
        return ""
    text = key.strip()
    if text:
        remember_secret(text)
    return text


def _result(provider, channel, code, text, ok):
    payload = {
        "ok": ok,
        "provider": provider.id,
        "tier": provider.tier,
        "stub": True,
        "paidCall": False,
        "channel": channel,
        "code": code,
        "text": text,
    }
    encoded = json.dumps(payload)
    if redact(encoded) != encoded:
        raise RuntimeError("refusing to return a key")
    log.info(
        "character %s provider=%s stub=1 paid_call=0 code=%s key_present=%s",
        channel,
        provider.id,
        code,
        provider.key_present,
    )
    return payload


class CharacterProvider(ABC):
    """How an in-game character answers. Subclasses stay on this machine."""

    id = ""
    label = ""
    tier = ""
    detail = ""
    requires_player_key = False
    bundled_voice = False

    def __init__(self):
        self.key_present = False

    def describe(self):
        return {
            "id": self.id,
            "label": self.label,
            "tier": self.tier,
            "detail": self.detail,
            "requiresPlayerKey": self.requires_player_key,
            "bundledVoice": self.bundled_voice,
            "paidCall": False,
        }

    def _note(self, key):
        text = _present(key)
        self.key_present = bool(text)
        return text

    @abstractmethod
    def reply(self, speaker, line, key=None):
        """Return a stub reply. `line` is not echoed, so a pasted key cannot leak."""

    @abstractmethod
    def speak(self, text, key=None):
        """Return a stub voice line. No audio is synthesized."""


class LocalBundledProvider(CharacterProvider):
    """Default. The free local LLM and its voice ship in the install. This build does not run them."""

    id = LOCAL
    label = "Bundled local voice"
    tier = "bundled"
    detail = "Free LLM and voice on this computer. No key."
    requires_player_key = False
    bundled_voice = True

    def reply(self, speaker, line, key=None):
        self._note(key)
        return _result(self, "reply", "stub", LOCAL_STUB, True)

    def speak(self, text, key=None):
        self._note(key)
        return _result(self, "voice", "stub", LOCAL_STUB, True)


class GrokPremiumProvider(CharacterProvider):
    """Optional premium tier. A key is kept locally. This build does not call out with it."""

    id = GROK
    label = "Grok"
    tier = "premium"
    detail = "Optional premium tier. Your key stays on this computer. This build does not call out."
    requires_player_key = True
    bundled_voice = True

    def reply(self, speaker, line, key=None):
        if not self._note(key):
            return _result(self, "reply", "key_required", "", False)
        return _result(self, "reply", "stub", PREMIUM_STUB, True)

    def speak(self, text, key=None):
        if not self._note(key):
            return _result(self, "voice", "key_required", "", False)
        return _result(self, "voice", "stub", PREMIUM_STUB, True)


_FACTORIES = {
    LOCAL: LocalBundledProvider,
    GROK: GrokPremiumProvider,
}


def get_provider(provider_id):
    factory = _FACTORIES.get(provider_id)
    if factory is None:
        raise ValueError("unknown provider")
    return factory()


def catalog():
    return [get_provider(provider_id).describe() for provider_id in (LOCAL, GROK)]


def respond(store, speaker, line):
    """Ask the selected provider for a reply. The local tier never reads the key file."""
    return _dispatch(store, "reply", speaker, line)


def speak_line(store, text):
    """Ask the selected provider to speak. The local tier never reads the key file."""
    return _dispatch(store, "voice", "", text)


def _dispatch(store, channel, speaker, line):
    settings = store.load()
    provider = get_provider(settings.provider)
    key = None
    if provider.requires_player_key:
        key = store.read_key()
    if channel == "voice":
        return provider.speak(line, key=key)
    return provider.reply(speaker, line, key=key)
