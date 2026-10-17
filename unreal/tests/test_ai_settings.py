import io
import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_garden

from ai_providers import (
    LOCAL_STUB,
    PREMIUM_STUB,
    catalog,
    respond,
    speak_line,
)
from ai_settings import (
    GROK,
    LOCAL,
    SETTINGS_NAME,
    AiSettings,
    AiSettingsStore,
    redact,
)
from pause_settings import MASK, PauseSettings, mount_pause_menu

# A fake player key. Tests assert this exact string never lands in records or logs.
SECRET = "xai-test-DoNotLog-9f3c1a7b"
SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"


class AiSettingsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.store = AiSettingsStore(self.root)
        self.logs = io.StringIO()
        self.handler = logging.StreamHandler(self.logs)
        self.handler.setFormatter(logging.Formatter("%(message)s"))
        self.root_logger = logging.getLogger()
        self.root_logger.addHandler(self.handler)
        self.previous_level = self.root_logger.level
        self.root_logger.setLevel(logging.DEBUG)
        self.addCleanup(self._detach_log)

    def _detach_log(self):
        self.root_logger.removeHandler(self.handler)
        self.root_logger.setLevel(self.previous_level)

    def _record(self):
        return self.store.settings_path.read_text(encoding="utf-8")

    def _assert_secret_hidden(self, *blobs):
        combined = "\n".join(blobs) + "\n" + self.logs.getvalue()
        self.assertNotIn(SECRET, combined)
        self.assertNotIn(SECRET, redact(combined))

    def test_default_is_the_bundled_local_provider(self):
        settings = self.store.load()
        self.assertEqual(settings.provider, LOCAL)
        self.assertFalse(self.store.key_present())
        public = settings.to_public(False)
        self.assertEqual(set(public), {"version", "provider", "keyPresent"})
        self.assertNotIn("key", public)
        ids = [item["id"] for item in catalog()]
        self.assertEqual(ids, [LOCAL, GROK])
        local = catalog()[0]
        premium = catalog()[1]
        self.assertEqual(local["tier"], "bundled")
        self.assertFalse(local["requiresPlayerKey"])
        self.assertTrue(local["bundledVoice"])
        self.assertFalse(local["paidCall"])
        self.assertEqual(premium["tier"], "premium")
        self.assertTrue(premium["requiresPlayerKey"])
        self.assertFalse(premium["paidCall"])

    def test_key_is_stored_beside_the_record_and_not_inside_it(self):
        self.store.save(AiSettings(provider=GROK), key="  " + SECRET + "  ")
        record = json.loads(self._record())
        self.assertEqual(record["provider"], GROK)
        self.assertTrue(record["keyPresent"])
        self.assertEqual(set(record), {"version", "provider", "keyPresent"})
        self.assertNotIn(SECRET, self._record())
        self.assertEqual(self.store.key_path.read_text(encoding="utf-8").strip(), SECRET)
        self.assertEqual(self.store.key_path.stat().st_mode & 0o777, 0o600)
        names = {path.name for path in self.root.iterdir()}
        self.assertEqual(names, {SETTINGS_NAME, "elyon-ai-key.txt"})
        loaded = self.store.load()
        self.assertEqual(loaded.provider, GROK)
        self.assertNotIn("key", repr(loaded))
        self._assert_secret_hidden(self._record(), repr(self.store), repr(loaded))

    def test_pause_menu_saves_masks_and_cancel_drops_the_draft(self):
        menu = PauseSettings(self.store)
        self.assertEqual(menu.handle_input("Escape"), "open")
        self.assertTrue(menu.public_state()["open"])
        menu.choose(GROK)
        shown = menu.set_key(SECRET)
        self.assertEqual(shown["keyField"], MASK)
        self.assertTrue(shown["keyPending"])
        self.assertNotIn(SECRET, repr(menu))
        self.assertNotIn(SECRET, repr(vars(menu)))
        self.assertNotIn(SECRET, json.dumps(menu.public_state()))
        menu.cancel()
        self.assertFalse(self.store.key_present())
        self.assertFalse(self.store.settings_path.exists())
        menu.open()
        menu.choose("Grok")
        menu.set_key(SECRET)
        self.assertEqual(menu.handle_input("enter"), "saved")
        self.assertEqual(self.store.load().provider, GROK)
        self.assertTrue(self.store.key_present())
        self.assertEqual(menu.public_state()["keyField"], MASK)
        menu.open()
        menu.set_key("")
        menu.save()
        self.assertFalse(self.store.key_present())
        self.assertFalse(self.store.key_path.exists())
        self._assert_secret_hidden(repr(menu), json.dumps(menu.public_state()))

    def test_mount_uses_the_editor_mock_and_hides_the_key(self):
        menu = PauseSettings(self.store)
        menu.choose(GROK)
        menu.set_key(SECRET)
        ue = test_garden.FakeUnreal()
        actor = mount_pause_menu(menu, ue=ue)
        self.assertEqual(actor.get_actor_label(), "Elyon.PauseSettings")
        state = actor.props["elyon_pause"]
        self.assertEqual(state["provider"], GROK)
        self.assertEqual(state["tier"], "premium")
        self.assertEqual(state["keyField"], MASK)
        self.assertEqual([item["id"] for item in state["choices"]], [LOCAL, GROK])
        mount_pause_menu(menu, ue=ue)
        labels = [item.get_actor_label() for item in ue.sub.actors]
        self.assertEqual(labels.count("Elyon.PauseSettings"), 1)
        dumped = json.dumps(actor.props)
        self.assertNotIn(SECRET, dumped)
        self._assert_secret_hidden(dumped, repr(actor.props))

    def test_local_tier_does_not_read_the_key_file(self):
        self.store.save(AiSettings(provider=GROK), key=SECRET)
        self.store.save(AiSettings(provider=LOCAL))
        self.store.key_reads = 0
        result = respond(self.store, "Adam", SECRET)
        spoken = speak_line(self.store, SECRET)
        self.assertEqual(self.store.key_reads, 0)
        self.assertTrue(self.store.key_present())
        self.assertEqual(result["provider"], LOCAL)
        self.assertEqual(result["text"], LOCAL_STUB)
        self.assertEqual(spoken["channel"], "voice")
        self.assertEqual(spoken["text"], LOCAL_STUB)
        self.assertTrue(result["stub"])
        self.assertFalse(result["paidCall"])
        self.assertFalse(spoken["paidCall"])
        self._assert_secret_hidden(json.dumps(result), json.dumps(spoken))

    def test_grok_stub_accepts_a_local_key_and_does_not_call_out(self):
        self.store.save(AiSettings(provider=GROK), key=SECRET)
        self.store.key_reads = 0

        def explode(*_args, **_kwargs):
            raise AssertionError("network")

        with patch("socket.socket", explode), patch("urllib.request.urlopen", explode):
            result = respond(self.store, "Eve", SECRET)
            spoken = speak_line(self.store, "a line")
        self.assertEqual(self.store.key_reads, 2)
        self.assertTrue(result["ok"])
        self.assertEqual(result["code"], "stub")
        self.assertEqual(result["text"], PREMIUM_STUB)
        self.assertEqual(spoken["code"], "stub")
        self.assertTrue(result["stub"])
        self.assertFalse(result["paidCall"])
        self.assertFalse(spoken["paidCall"])
        self.assertEqual(spoken["provider"], GROK)
        missing = AiSettingsStore(self.root / "empty")
        missing.save(AiSettings(provider=GROK))
        blocked = respond(missing, "Eve", "hello")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "key_required")
        self.assertEqual(blocked["text"], "")
        self.assertFalse(blocked["paidCall"])
        self._assert_secret_hidden(json.dumps(result), json.dumps(spoken), json.dumps(blocked))

    def test_logs_and_exceptions_redact_the_key(self):
        self.store.save(AiSettings(provider=GROK), key=SECRET)
        logging.getLogger("elyon.ai").info("token %s", SECRET)
        logging.getLogger("other").info("payload %s", {"apiKey": SECRET})
        try:
            raise RuntimeError(SECRET)
        except RuntimeError:
            logging.getLogger("elyon.ai").exception("provider failed")
        self.assertIn("[redacted]", self.logs.getvalue())
        self.assertIn("redacted", self.logs.getvalue())
        self._assert_secret_hidden()

    def test_corrupt_record_resets_and_a_stray_key_is_lifted(self):
        self.store.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.store.settings_path.write_text('{"provider": "grok", "apiKey": "' + SECRET + '"', encoding="utf-8")
        broken = self.store.load()
        self.assertEqual(broken.provider, LOCAL)
        self.assertFalse(self.store.key_present())
        self.assertNotIn(SECRET, self._record())
        self.store.settings_path.write_text(
            json.dumps({"version": 1, "provider": "Grok", "apiKey": SECRET, "token": "short"}),
            encoding="utf-8",
        )
        lifted = self.store.load()
        self.assertEqual(lifted.provider, GROK)
        self.assertTrue(self.store.key_present())
        record = json.loads(self._record())
        self.assertEqual(set(record), {"version", "provider", "keyPresent"})
        self.assertTrue(record["keyPresent"])
        self.assertNotIn(SECRET, self._record())
        self.assertEqual(self.store.read_key(), SECRET)
        self.store.settings_path.write_text(json.dumps({"provider": "openai"}), encoding="utf-8")
        self.assertEqual(self.store.load().provider, LOCAL)
        menu = PauseSettings(self.store)
        with self.assertRaises(ValueError):
            menu.choose(SECRET)
        with self.assertRaises(ValueError):
            self.store.save(AiSettings(provider=GROK), key="short")
        self._assert_secret_hidden(self._record())

    def test_provider_modules_do_not_name_a_network_client(self):
        banned = ("urllib", "requests", "http.client", "api.x.ai", "https://", "socket")
        for name in ("ai_settings.py", "ai_providers.py", "pause_settings.py"):
            source = (SCRIPTS / name).read_text(encoding="utf-8")
            for token in banned:
                self.assertNotIn(token, source, name)


if __name__ == "__main__":
    unittest.main()
