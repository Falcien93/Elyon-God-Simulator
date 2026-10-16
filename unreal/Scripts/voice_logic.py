"""Voice-as-God intent matching. Pure Python: no Unreal, no model, no download."""

import json
import os
import re
from pathlib import Path

import garden_logic

DATA_PATH = Path(__file__).resolve().parents[1] / "Data" / "intents.json"

EFFECTS = ("light", "water", "grow", "calm", "destroy")
STOPWORDS = {
    "a",
    "an",
    "and",
    "be",
    "for",
    "hey",
    "let",
    "me",
    "now",
    "of",
    "please",
    "the",
    "there",
    "to",
}

WHISPER_DIR = Path("Content/Voice/whisper")
LLAMA_DIR = Path("Content/Voice/llama")


def load_table(path=None):
    raw = json.loads(Path(path or DATA_PATH).read_text(encoding="utf-8"))
    intents = raw.get("intents") or []
    ids = [item["id"] for item in intents]
    if len(ids) != len(set(ids)):
        raise ValueError("intent ids must be unique")
    for item in intents:
        if item.get("effect") not in EFFECTS:
            raise ValueError(f"unknown effect on {item.get('id')}")
        if not item.get("phrases"):
            raise ValueError(f"{item.get('id')} needs phrases")
    raw["by_id"] = {item["id"]: item for item in intents}
    return raw


def _tokens(text):
    cleaned = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
    tokens = [token for token in cleaned.split() if token and token not in STOPWORDS]
    return tokens


def _strip_hotword(tokens, hotword):
    if tokens and hotword and tokens[0] == hotword.lower():
        return tokens[1:]
    return tokens


def _contains_seq(haystack, needle):
    if not needle or len(needle) > len(haystack):
        return False
    span = len(needle)
    for index in range(len(haystack) - span + 1):
        if haystack[index : index + span] == needle:
            return True
    return False


def _score(utterance, phrase):
    phrase_tokens = _tokens(phrase)
    if not utterance or not phrase_tokens:
        return 0.0
    if utterance == phrase_tokens or _contains_seq(utterance, phrase_tokens):
        return 1.0
    if len(phrase_tokens) == 1 and phrase_tokens[0] in utterance:
        return 0.95
    shared = set(phrase_tokens) & set(utterance)
    if not shared:
        return 0.0
    return (2.0 * len(shared)) / (len(phrase_tokens) + len(utterance))


def match_phrase(text, table):
    """Return the best intent at or above the threshold, or None."""
    tokens = _strip_hotword(_tokens(text), table.get("hotword", ""))
    if not tokens:
        return None
    threshold = float(table.get("threshold", 0.8))
    best = None
    for intent in table["intents"]:
        phrase_score = 0.0
        phrase = ""
        for candidate in intent["phrases"]:
            scored = _score(tokens, candidate)
            if scored > phrase_score or (scored == phrase_score and len(candidate) > len(phrase)):
                phrase_score = scored
                phrase = candidate
        if phrase_score < threshold:
            continue
        last_at = max(tokens.index(token) for token in _tokens(phrase) if token in tokens)
        rank = (phrase_score, len(_tokens(phrase)), last_at)
        if best is None or rank > best[0]:
            best = (rank, intent, phrase, phrase_score)
    if best is None:
        return None
    _rank, intent, phrase, phrase_score = best
    return {
        "id": intent["id"],
        "effect": intent["effect"],
        "phrase": phrase,
        "score": round(phrase_score, 3),
        "via": "phrase",
        "model_called": False,
    }


def llm_prompt(text, table):
    ids = ", ".join(intent["id"] for intent in table["intents"])
    return (
        "You map one spoken command from God onto a single intent. "
        f"Allowed intents: {ids}, NONE. "
        'Reply with JSON only: {"intent":"LIGHT","confidence":0.0}. '
        f"Command: {text}"
    )


def parse_llm_json(text, table):
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    intent_id = str(payload.get("intent", "")).upper()
    if intent_id in ("", "NONE"):
        return None
    if intent_id not in table["by_id"]:
        return None
    confidence = payload.get("confidence", 1)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        return None
    if confidence < 0.5:
        return None
    intent = table["by_id"][intent_id]
    return {
        "id": intent_id,
        "effect": intent["effect"],
        "phrase": "",
        "score": round(confidence, 3),
        "via": "llm",
        "model_called": True,
    }


def resolve_utterance(text, table, llm=None):
    """Phrase match first. Call llm only when that misses."""
    heard = " ".join((text or "").split())
    matched = match_phrase(heard, table)
    if matched:
        matched["heard"] = heard
        matched["line"] = table["by_id"][matched["id"]]["line"]
        matched["subtitle"] = heard or matched["line"]
        return matched
    if llm is not None:
        parsed = parse_llm_json(llm(llm_prompt(heard, table)), table)
        if parsed:
            parsed["heard"] = heard
            parsed["line"] = table["by_id"][parsed["id"]]["line"]
            parsed["subtitle"] = heard or parsed["line"]
            return parsed
    return {
        "id": None,
        "effect": None,
        "heard": heard,
        "line": "",
        "subtitle": heard or "…",
        "via": "none",
        "model_called": False,
    }


def direct_intent(intent_id, table):
    intent = table["by_id"][intent_id]
    return {
        "id": intent["id"],
        "effect": intent["effect"],
        "heard": intent["line"],
        "line": intent["line"],
        "subtitle": intent["line"],
        "phrase": intent["phrases"][0],
        "score": 1.0,
        "via": "keyboard",
        "model_called": False,
    }


def command_for_key(key, table, phrase_index=0):
    binding = (table.get("keyboard") or {}).get(key)
    if binding == "phrase":
        samples = table.get("phraseSamples") or [""]
        return {"type": "phrase", "text": samples[phrase_index % len(samples)]}
    if binding in table["by_id"]:
        return {"type": "intent", "id": binding}
    if key == table.get("pushToTalk"):
        return {"type": "push_to_talk"}
    return {"type": "ignore"}


def dawn_sun_lux():
    """Same dawn sun the garden build writes onto Elyon.Sun."""
    return garden_logic.light_state(True)["sun_intensity"]


def new_world():
    return {
        "light": "dawn",
        "sun": dawn_sun_lux(),
        "skylight": 1.0,
        "water": 0.35,
        "rain": False,
        "foliage_scale": 1.0,
        "growth": [],
        "wind": 0.35,
        "clouds": 0.55,
        "storm": 0.2,
        "strikes": [],
        "subtitle": "",
        "grow_serial": 0,
    }


def grow_points(gaze, count, radius, serial):
    """Deterministic ring around the gaze point. PCG uses the same center and radius."""
    origin_x, origin_y, origin_z = gaze
    points = []
    for index in range(count):
        angle = (index / count) * 6.283185307179586
        # Cheap unit-circle sample without importing math in a loop of trig surprises.
        ox = round(origin_x + radius * _cos(angle), 2)
        oy = round(origin_y + radius * _sin(angle), 2)
        points.append(
            {
                "label": f"Elyon.Growth.{serial + index + 1:02d}",
                "x": ox,
                "y": oy,
                "z": origin_z,
            }
        )
    return points


def _cos(angle):
    import math

    return math.cos(angle)


def _sin(angle):
    import math

    return math.sin(angle)


def apply_intent(world, resolved, gaze=(0.0, -200.0, 40.0)):
    """Fold one resolved command into world stats. Does not touch Unreal."""
    nxt = json.loads(json.dumps(world))
    effect = resolved.get("effect")
    nxt["subtitle"] = resolved.get("subtitle") or ""
    if effect == "light":
        nxt["light"] = "dawn"
        nxt["sun"] = dawn_sun_lux()
        nxt["skylight"] = round(min(2.0, max(nxt["skylight"], 1.0) + 0.35), 2)
    elif effect == "water":
        if nxt["water"] < 1:
            nxt["water"] = 1.0
            nxt["rain"] = False
        else:
            nxt["rain"] = True
    elif effect == "grow":
        count = int(resolved.get("count") or 8)
        radius = float(resolved.get("radius") or 600)
        points = grow_points(gaze, count, radius, nxt["grow_serial"])
        nxt["grow_serial"] += len(points)
        nxt["growth"].extend(points)
        nxt["foliage_scale"] = round(min(2.5, nxt["foliage_scale"] + 0.2), 2)
        nxt["pcg"] = {
            "graph": resolved.get("graph") or "/Game/PCG/GrowAroundGaze",
            "radius": radius,
            "count": count,
            "gaze": list(gaze),
        }
    elif effect == "calm":
        nxt["wind"] = 0.0
        nxt["storm"] = 0.0
        nxt["clouds"] = 0.15
    elif effect == "destroy":
        nxt["strikes"].append(
            {
                "at": [round(float(part), 2) for part in gaze],
                "impulse": int(resolved.get("impulse") or 25000),
                "radius": float(resolved.get("radius") or 900),
                "lightning": True,
            }
        )
    else:
        return nxt
    return nxt


def whisper_model_path(name, root=None):
    base = Path(root) if root else WHISPER_DIR
    return str(base / f"ggml-{name}.bin")


def whisper_command(wav_path, table, binary, model_path):
    """GPU stays on unless the table turns it off. -ng is whisper.cpp's no-GPU flag."""
    stt = table.get("stt") or {}
    command = [binary, "-m", model_path, "-f", wav_path, "-l", stt.get("language", "en"), "-nt"]
    if not stt.get("gpu", True):
        command.append("-ng")
    return command


def choose_whisper_model(table, exists, root=None):
    stt = table.get("stt") or {}
    names = [stt.get("prefer", "small.en"), stt.get("fallbackModel", "base.en")]
    for name in names:
        path = whisper_model_path(name, root)
        if exists(path):
            return path
    return whisper_model_path(names[0], root)


def llama_command(prompt, table, binary, model_path):
    limit = str(int((table.get("llm") or {}).get("maxTokens", 80)))
    return [binary, "-m", model_path, "-p", prompt, "-n", limit, "--temp", "0", "-no-cnv"]


def ffmpeg_record_command(output, seconds=4, spec=None):
    """4 second mono 16 kHz take. spec is format:input, overridable with ELYON_FFMPEG_INPUT."""
    chosen = spec if spec is not None else os.environ.get("ELYON_FFMPEG_INPUT", "")
    if not chosen:
        chosen = "dshow:audio=Microphone" if os.name == "nt" else "pulse:default"
    audio_format, source = chosen.split(":", 1)
    return [
        "ffmpeg",
        "-y",
        "-f",
        audio_format,
        "-i",
        source,
        "-t",
        str(int(seconds)),
        "-ac",
        "1",
        "-ar",
        "16000",
        output,
    ]
