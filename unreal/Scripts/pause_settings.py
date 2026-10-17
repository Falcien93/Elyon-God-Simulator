"""Pause-menu layer for choosing who speaks for in-game characters.

The menu edits AiSettingsStore. It does not build the garden, and it does not
speak for God-commands or the desktop Living Voices path.
"""

from __future__ import annotations

import weakref

from ai_providers import catalog, get_provider
from ai_settings import LOCAL, AiSettings, log, normalize_provider

MASK = "••••••••"
ACTOR_LABEL = "Elyon.PauseSettings"

_draft_keys = weakref.WeakKeyDictionary()


class PauseSettings:
    """Esc opens this layer. The draft key is not on the instance dict."""

    def __init__(self, store):
        self.store = store
        self.visible = False
        self.provider = store.load().provider
        _draft_keys[self] = None

    def __repr__(self):
        return f"PauseSettings({self.public_state()!r})"

    def open(self):
        self.provider = self.store.load().provider
        self.visible = True
        _draft_keys[self] = None
        log.info("pause settings open provider=%s", self.provider)
        return self.public_state()

    def choose(self, provider_id):
        if not isinstance(provider_id, str):
            raise ValueError("unknown provider")
        try:
            self.provider = normalize_provider(provider_id, fallback=False)
        except ValueError:
            raise ValueError("unknown provider") from None
        if not self.visible:
            self.visible = True
        log.info("pause choice %s", self.provider)
        return self.public_state()

    def set_key(self, value):
        """Hold a draft key in memory until save or cancel. The value is not logged."""
        if not isinstance(value, str):
            raise TypeError("key must be a string")
        _draft_keys[self] = value.strip()
        if not self.visible:
            self.visible = True
        log.info("pause key field edited")
        return self.public_state()

    def save(self):
        draft = _draft_keys.get(self)
        settings = AiSettings(provider=self.provider or LOCAL)
        if draft is None:
            self.store.save(settings)
        else:
            self.store.save(settings, key=draft)
        _draft_keys[self] = None
        self.provider = self.store.load().provider
        self.visible = False
        log.info("pause settings saved provider=%s", self.provider)
        return self.public_state()

    def cancel(self):
        _draft_keys[self] = None
        self.provider = self.store.load().provider
        self.visible = False
        log.info("pause settings closed")
        return self.public_state()

    def toggle(self):
        if self.visible:
            return self.cancel()
        return self.open()

    def handle_input(self, command):
        """Keyboard for the pause layer. A key is never passed as a command."""
        if not isinstance(command, str):
            return "ignored"
        word = command.strip().lower()
        if word in ("escape", "esc", "pause"):
            self.toggle()
            return "open" if self.visible else "closed"
        if not self.visible:
            return "ignored"
        if word in ("1", "local"):
            self.choose(LOCAL)
            return "provider"
        if word == "2" or word == "grok":
            self.choose("grok")
            return "provider"
        if word in ("enter", "save"):
            self.save()
            return "saved"
        if word in ("cancel", "back"):
            self.cancel()
            return "closed"
        return "ignored"

    def public_state(self):
        draft = _draft_keys.get(self)
        if draft is None:
            key_present = self.store.key_present()
            key_field = MASK if key_present else ""
            pending = False
        elif draft == "":
            key_field = ""
            key_present = False
            pending = True
        else:
            key_field = MASK
            key_present = True
            pending = True
        provider = get_provider(self.provider)
        return {
            "open": self.visible,
            "provider": provider.id,
            "tier": provider.tier,
            "label": provider.label,
            "keyPresent": key_present,
            "keyField": key_field,
            "keyPending": pending,
            "choices": catalog(),
        }


def mount_pause_menu(menu, ue=None):
    """Put the public pause state on an editor actor. The actor never receives the key."""
    if ue is None:
        import unreal

        ue = unreal
    subsystem = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    actor = None
    for existing in subsystem.get_all_level_actors():
        if existing.get_actor_label() == ACTOR_LABEL:
            actor = existing
            break
    if actor is None:
        actor = subsystem.spawn_actor_from_class(ue.TargetPoint, ue.Vector(0.0, 0.0, 200.0), ue.Rotator(0.0, 0.0, 0.0))
        actor.set_actor_label(ACTOR_LABEL)
    actor.set_editor_property("elyon_pause", menu.public_state())
    return actor
