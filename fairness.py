"""Bias Mirror: does the score change when only the writing style changes?

The same answer is rewritten in different styles (same ideas, different wording) and
scored again. A fair assessor should give the same scores. A change counts as a style
effect only if it is bigger than the normal run-to-run noise of the original answer.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from assessor import FALLBACK_MODELS, ModelNotFound, _post, assess

STYLES = {
    "non_native": ("Non-native English",
                   "as a non-native English speaker would write it: simpler words and a few small grammar "
                   "mistakes"),
    "formal": ("Very formal", "in very formal, polished business English"),
    "bullets": ("Short bullet points", "as short bullet points"),
}

REWRITE_PROMPT = """Rewrite the text below {how}.
Keep EXACTLY the same ideas, actions and reasons. Do not add, remove or improve any content.
Return only the rewritten text.

TEXT
{text}"""


@dataclass
class StyleResult:
    style: str
    label: str
    text: str
    scores: dict      # competency key -> list of scores (one per run)


def rewrite(text: str, style: str, api_key: str, model: str) -> str:
    prompt = REWRITE_PROMPT.format(how=STYLES[style][1], text=text)
    for m in [model] + [f for f in FALLBACK_MODELS if f != model]:
        resp = _post(prompt, api_key, m, 0.3, json_mode=False)
        if resp.status_code == 404:
            continue
        if resp.status_code >= 400:
            raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text[:200]}")
        return resp.json()["choices"][0]["message"]["content"].strip()
    raise ModelNotFound(model)


def run_mirror(scenario_text: str, answer: str, runs: int, api_key: str, model: str) -> list[StyleResult]:
    out = []
    for style, (label, _) in STYLES.items():
        text = rewrite(answer, style, api_key, model)
        res = assess(scenario_text, text, runs=runs, api_key=api_key, model=model)
        out.append(StyleResult(style, label, text, {r.key: r.scores for r in res}))
    return out


def compare(original: dict, versions: list[StyleResult]) -> list[dict]:
    """One row per competency: original median, each style's median, and whether style moved the score.

    `original` maps competency key -> list of run scores for the original answer.
    A style effect is flagged when the median moves by at least 1 point AND by more than the
    original answer's own spread between runs (otherwise it may just be normal noise).
    """
    rows = []
    for key, orig_scores in original.items():
        base = statistics.median(orig_scores)
        noise = max(orig_scores) - min(orig_scores)
        row = {"key": key, "original": base, "noise": noise, "styles": {}}
        for v in versions:
            med = statistics.median(v.scores[key])
            delta = med - base
            row["styles"][v.style] = {"median": med, "delta": delta,
                                      "flag": abs(delta) >= 1 and abs(delta) > noise}
        rows.append(row)
    return rows
