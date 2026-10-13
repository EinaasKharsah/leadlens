"""Small tests for the parts that check the AI's output. Run: python -m pytest -q"""

from assessor import assess, parse_llm_json, quote_in_answer
from demo_data import DEMO_RUNS
from scenarios import SCENARIOS


def test_quote_check_ignores_case_and_punctuation():
    answer = "First, I would talk to the team. Then I decide."
    assert quote_in_answer("i would talk to the team", answer)
    assert not quote_in_answer("I would fire someone", answer)


def test_parser_handles_code_fences_and_clamps_scores():
    raw = '```json\n{"communication":{"score":7,"evidence":["a"],"rationale":"x"},' \
          '"people":{"score":0,"evidence":[],"rationale":"y"},' \
          '"decision":{"score":3.4,"evidence":[],"rationale":"z"},' \
          '"ownership":{"score":"4","evidence":[""],"rationale":"w"}}\n```'
    data = parse_llm_json(raw)
    assert data["communication"]["score"] == 5
    assert data["people"]["score"] == 1
    assert data["decision"]["score"] == 3
    assert data["ownership"]["evidence"] == []


def test_demo_flags_invented_quote_and_instability():
    sc = SCENARIOS[0]
    results = {r.key: r for r in assess(sc["text"], sc["sample_answer"], runs=3, demo_runs=DEMO_RUNS[sc["id"]])}
    assert "I take full responsibility for the delay" in results["ownership"].unverified_evidence
    assert results["people"].spread == 2 and results["people"].needs_human
    assert not results["communication"].needs_human


def test_live_path_with_mocked_api(monkeypatch):
    """The live path calls the API once per run and combines the results."""
    import assessor
    calls = []

    class FakeResp:
        status_code = 200

        def __init__(self, score):
            self.score = score
        def raise_for_status(self):
            pass
        def json(self):
            body = {k: {"score": self.score, "evidence": ["talk to the team"], "rationale": "ok"}
                    for k in ["communication", "people", "decision", "ownership"]}
            import json as _j
            return {"choices": [{"message": {"content": _j.dumps(body)}}]}

    def fake_post(url, headers, json, timeout):
        calls.append(json["model"])
        return FakeResp(3 + len(calls) % 2)   # alternates 4, 3, 4

    monkeypatch.setattr(assessor.requests, "post", fake_post)
    res = assessor.assess("scenario", "I would talk to the team first and then decide.", runs=3, api_key="x")
    assert len(calls) == 3
    assert res[0].scores == [4, 3, 4] and res[0].needs_human
    assert res[0].verified_evidence == ["talk to the team"]


def test_retired_model_falls_back(monkeypatch):
    """A 404 for a retired model makes the app try the next model instead of failing."""
    import assessor
    seen = []

    class Resp:
        def __init__(self, code):
            self.status_code = code
        def json(self):
            body = {k: {"score": 3, "evidence": [], "rationale": "ok"}
                    for k in ["communication", "people", "decision", "ownership"]}
            import json as _j
            return {"choices": [{"message": {"content": _j.dumps(body)}}]}

    def fake_post(url, headers, json, timeout):
        seen.append(json["model"])
        return Resp(404 if json["model"] == "old-model" else 200)

    monkeypatch.setattr(assessor.requests, "post", fake_post)
    res = assessor.assess("s", "some answer text here", runs=2, api_key="x", model="old-model")
    assert seen[0] == "old-model" and seen[1] == assessor.FALLBACK_MODELS[0]
    assert assessor.assess.last_model == assessor.FALLBACK_MODELS[0]
    assert len(res) == 4
