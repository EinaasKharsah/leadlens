"""AI assessor: scores a written answer, checks its own output, and measures consistency.

Three ideas behind this module:
1. Every score must point to evidence: a quote copied from the candidate's answer.
2. The AI output is not trusted blindly. Quotes are checked against the answer text,
   and a score without real evidence is flagged.
3. The same answer is scored several times. If the scores disagree, the competency
   is flagged for a human, because one run is weak evidence.
"""

from __future__ import annotations

import json
import os
import re
import statistics
import time
from dataclasses import dataclass, field

import requests

from scenarios import COMPETENCIES

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
DEFAULT_MODEL = "openai/gpt-oss-120b"
# Tried in order if a model has been retired (Groq returns 404 for unknown models).
FALLBACK_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "llama-3.1-8b-instant"]

# A competency needs a human look when repeated runs disagree by this much or more.
SPREAD_THRESHOLD = 1


@dataclass
class CompetencyResult:
    key: str
    name: str
    scores: list[int]                      # one score per run
    evidence: list[str]                    # quotes from the first run
    rationale: str
    verified_evidence: list[str] = field(default_factory=list)
    unverified_evidence: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        return round(statistics.median(self.scores), 1)

    @property
    def spread(self) -> int:
        return max(self.scores) - min(self.scores)

    @property
    def flags(self) -> list[str]:
        out = []
        if self.spread >= SPREAD_THRESHOLD and len(self.scores) > 1:
            out.append(f"Unstable: runs gave {', '.join(map(str, self.scores))}")
        if not self.verified_evidence:
            out.append("No verified evidence in the answer")
        if self.unverified_evidence:
            out.append(f"{len(self.unverified_evidence)} quote(s) not found in the answer")
        return out

    @property
    def needs_human(self) -> bool:
        return bool(self.flags)


def build_prompt(scenario_text: str, answer: str) -> str:
    rubric = []
    for key, c in COMPETENCIES.items():
        anchors = "; ".join(f"{lvl} = {txt}" for lvl, txt in c["anchors"].items())
        rubric.append(f'- "{key}" ({c["name"]}): {anchors}')
    rubric_text = "\n".join(rubric)
    return f"""You are an experienced assessment-center assessor. Score the candidate's written answer
to a leadership scenario. Use ONLY the rubric below. Scores are whole numbers from 1 to 5
(2 and 4 lie between the anchors).

RUBRIC
{rubric_text}

RULES
- For each competency, give 0-2 short evidence quotes copied EXACTLY from the answer.
- If the answer shows no evidence for a competency, give an empty list and a score of 1 or 2.
- Do not reward length. Judge what the person would actually do.
- Keep each rationale to one sentence.

SCENARIO
{scenario_text}

ANSWER
{answer}

Return ONLY valid JSON in this exact shape:
{{"communication": {{"score": 3, "evidence": ["..."], "rationale": "..."}},
 "people": {{...}}, "decision": {{...}}, "ownership": {{...}}}}"""


class ModelNotFound(Exception):
    pass


def _post(prompt: str, api_key: str, model: str, temperature: float, json_mode: bool) -> requests.Response:
    body = {"model": model, "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    send = lambda: requests.post(GROQ_URL, json=body, timeout=90,
                                 headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    resp = send()
    attempt = 0
    while resp.status_code == 429 and attempt < MAX_RATE_RETRIES:
        # Free Groq accounts have a tokens-per-minute limit: wait as Groq suggests, then try again.
        time.sleep(_wait_seconds(resp, attempt))
        attempt += 1
        resp = send()
    return resp


MAX_RATE_RETRIES = 6


def _wait_seconds(resp, attempt: int) -> float:
    hint = resp.headers.get("retry-after") if getattr(resp, "headers", None) else None
    if not hint:
        m = re.search(r"try again in ([0-9.]+)s", getattr(resp, "text", "") or "")
        hint = m.group(1) if m else None
    try:
        return min(float(hint) + 0.5, 60.0)
    except (TypeError, ValueError):
        return min(2.0 * (2 ** attempt), 60.0)


def _call_model(prompt: str, api_key: str, model: str, temperature: float) -> dict:
    resp = _post(prompt, api_key, model, temperature, json_mode=True)
    if resp.status_code == 400:
        # Some models do not support JSON mode; the parser can handle plain text around the JSON.
        resp = _post(prompt, api_key, model, temperature, json_mode=False)
    if resp.status_code == 404:
        raise ModelNotFound(model)
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("error", {}).get("message", resp.text)
        except ValueError:
            detail = resp.text
        raise RuntimeError(f"Groq API error {resp.status_code}: {detail}")
    content = resp.json()["choices"][0]["message"]["content"]
    return parse_llm_json(content)


def _available_models(api_key: str) -> list[str]:
    try:
        r = requests.get(GROQ_MODELS_URL, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
        r.raise_for_status()
        ids = [m["id"] for m in r.json().get("data", [])]
    except Exception:
        return []
    skip = ("whisper", "guard", "tts", "playai", "orpheus", "distil")
    return [i for i in ids if not any(x in i.lower() for x in skip)]


def _call_llm(prompt: str, api_key: str, model: str, temperature: float) -> tuple[dict, str]:
    """Call the model; if it has been retired, fall back to another available model.

    Returns the parsed output and the model that was actually used.
    """
    tried = []
    for m in [model] + [f for f in FALLBACK_MODELS if f != model]:
        tried.append(m)
        try:
            return _call_model(prompt, api_key, m, temperature), m
        except ModelNotFound:
            continue
    for m in _available_models(api_key):
        if m in tried:
            continue
        try:
            return _call_model(prompt, api_key, m, temperature), m
        except ModelNotFound:
            continue
    raise RuntimeError("None of the Groq models are available: " + ", ".join(tried))


def parse_llm_json(content: str) -> dict:
    """Parse the model output, tolerating code fences or extra text around the JSON."""
    content = content.strip()
    content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("The model did not return JSON.")
    data = json.loads(content[start : end + 1])
    for key in COMPETENCIES:
        if key not in data:
            raise ValueError(f"Missing competency in model output: {key}")
        score = int(round(float(data[key].get("score", 0))))
        data[key]["score"] = min(5, max(1, score))
        ev = data[key].get("evidence") or []
        data[key]["evidence"] = [str(e) for e in ev if str(e).strip()]
        data[key]["rationale"] = str(data[key].get("rationale", "")).strip()
    return data


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", text.lower())).strip()


def quote_in_answer(quote: str, answer: str) -> bool:
    """True if the quote really appears in the answer (ignoring case, punctuation and spacing)."""
    q = _normalise(quote)
    return bool(q) and q in _normalise(answer)


def assess(scenario_text: str, answer: str, runs: int = 3, api_key: str | None = None,
           model: str = DEFAULT_MODEL, demo_runs: list[dict] | None = None) -> list[CompetencyResult]:
    """Score the answer `runs` times and combine the results.

    If `demo_runs` is given, those pre-recorded outputs are used instead of calling the API.
    """
    if demo_runs is not None:
        outputs = demo_runs[:runs]
    else:
        key = api_key or os.environ.get("GROQ_API_KEY")
        if not key:
            raise RuntimeError("No API key. Add a Groq API key or use demo mode.")
        prompt = build_prompt(scenario_text, answer)
        outputs = []
        for _ in range(runs):
            out, model = _call_llm(prompt, key, model, temperature=0.7)  # keep the model that worked
            outputs.append(out)
        assess.last_model = model

    results = []
    for key, comp in COMPETENCIES.items():
        first = outputs[0][key]
        res = CompetencyResult(
            key=key,
            name=comp["name"],
            scores=[o[key]["score"] for o in outputs],
            evidence=first["evidence"],
            rationale=first["rationale"],
        )
        for q in res.evidence:
            (res.verified_evidence if quote_in_answer(q, answer) else res.unverified_evidence).append(q)
        results.append(res)
    return results
