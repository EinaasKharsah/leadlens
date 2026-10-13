"""LeadLens: AI-assisted leadership assessment with a human in the loop.

Flow: candidate answers a scenario -> AI scores it several times -> the app checks
the AI's evidence and consistency -> a human assessor reviews and decides -> report.
Run with:  streamlit run app.py
"""

import json
import os
from datetime import datetime

import streamlit as st

from assessor import DEFAULT_MODEL, assess
from demo_data import DEMO_RUNS
from scenarios import COMPETENCIES, SCENARIOS

st.set_page_config(page_title="LeadLens – AI-assisted assessment", page_icon="🔎", layout="wide")

# ---------- state ----------
defaults = {"step": 1, "results": None, "answer": "", "scenario_id": SCENARIOS[0]["id"], "final": None}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)


def go(step: int):
    st.session_state.step = step


# ---------- sidebar ----------
with st.sidebar:
    st.title("🔎 LeadLens")
    st.caption("AI does the first read. A human makes the call.")
    secret_key = None
    try:
        secret_key = st.secrets.get("GROQ_API_KEY")
    except Exception:
        pass
    env_key = secret_key or os.environ.get("GROQ_API_KEY")
    mode = st.radio("Mode", ["Demo (example AI output)", "Live AI (Groq)"],
                    index=1 if env_key else 0)
    live = mode.startswith("Live")
    api_key = env_key
    if live and not env_key:
        api_key = st.text_input("Groq API key", type="password",
                                help="Free key at console.groq.com. It is only used for this session.")
    runs = st.slider("AI runs per answer", 1, 5, 3,
                     help="The same answer is scored several times. Disagreement between runs is a warning sign.")
    model = st.text_input("Model", DEFAULT_MODEL, disabled=not live)
    st.divider()
    steps = ["1 · Candidate answer", "2 · AI assessment", "3 · Assessor review", "4 · Final report"]
    for i, label in enumerate(steps, start=1):
        st.markdown(f"**{label}**" if st.session_state.step == i else label)
    if st.button("Start over"):
        for k, v in defaults.items():
            st.session_state[k] = v
        st.rerun()

scenario = next(s for s in SCENARIOS if s["id"] == st.session_state.scenario_id)

# ---------- step 1: candidate ----------
if st.session_state.step == 1:
    st.header("1 · Candidate answer")
    titles = {s["title"]: s["id"] for s in SCENARIOS}
    chosen = st.selectbox("Scenario", list(titles), index=list(titles.values()).index(scenario["id"]))
    if titles[chosen] != st.session_state.scenario_id:
        st.session_state.scenario_id = titles[chosen]
        st.session_state.answer = ""
        st.rerun()
    st.info(scenario["text"])
    if not st.session_state.answer and scenario["sample_answer"]:
        st.session_state.answer = scenario["sample_answer"]
    answer = st.text_area("Your answer", key="answer", height=220,
                          placeholder="Write what you would do and why…")
    has_demo = scenario["id"] in DEMO_RUNS
    if not live and not has_demo:
        st.warning("Demo mode has example AI output only for the first two scenarios. "
                   "Switch to Live AI to score this one.")
    if not live and has_demo:
        st.caption("Demo mode: scores come from prepared example output. The evidence check still runs "
                   "against the text in the box, so editing the answer changes which quotes are verified.")
    disabled = len(answer.split()) < 15 or (not live and not has_demo) or (live and not api_key)
    if st.button("Get AI assessment →", type="primary", disabled=disabled):
        with st.spinner(f"Scoring the answer {runs} time(s)…"):
            try:
                st.session_state.results = assess(
                    scenario["text"], answer, runs=runs, api_key=api_key, model=model,
                    demo_runs=None if live else DEMO_RUNS[scenario["id"]])
                go(2)
                st.rerun()
            except Exception as e:  # show the problem instead of crashing
                st.error(f"The AI assessment failed: {e}")
    if len(answer.split()) < 15:
        st.caption("Write at least 15 words.")

# ---------- step 2: AI assessment ----------
elif st.session_state.step == 2:
    st.header("2 · AI assessment")
    results = st.session_state.results
    flagged = [r for r in results if r.needs_human]
    c1, c2, c3 = st.columns(3)
    c1.metric("Competencies scored", len(results))
    c2.metric("Need a human check", len(flagged))
    c3.metric("AI runs per answer", len(results[0].scores))
    if flagged:
        st.warning("The AI is not reliable enough on: " + ", ".join(r.name for r in flagged)
                   + ". These go to the assessor first.")
    for r in sorted(results, key=lambda r: not r.needs_human):
        with st.container(border=True):
            left, right = st.columns([1, 3])
            left.markdown(f"### {r.name}")
            left.metric("AI score (median)", f"{r.score} / 5")
            left.caption("Runs: " + " · ".join(map(str, r.scores)))
            right.markdown(f"**Why:** {r.rationale or '–'}")
            for q in r.verified_evidence:
                right.markdown(f"✅ Evidence found in answer: *“{q}”*")
            for q in r.unverified_evidence:
                right.markdown(f"❌ Quote **not** in the answer (possible AI invention): *“{q}”*")
            for f in r.flags:
                right.markdown(f"⚠️ {f}")
    a, b = st.columns(2)
    a.button("← Back", on_click=go, args=(1,))
    b.button("Send to assessor review →", type="primary", on_click=go, args=(3,))

# ---------- step 3: assessor review ----------
elif st.session_state.step == 3:
    st.header("3 · Assessor review")
    st.caption("You decide. Flagged items are shown first. If you change a score, say why. "
               "That reason is what improves the rubric and the AI over time.")
    results = st.session_state.results
    with st.expander("Candidate answer", expanded=False):
        st.write(st.session_state.answer)
    decisions = {}
    for r in sorted(results, key=lambda r: not r.needs_human):
        with st.container(border=True):
            st.markdown(f"**{r.name}** — AI: {r.score} (runs {', '.join(map(str, r.scores))})"
                        + ("  ⚠️ needs check" if r.needs_human else ""))
            anchors = COMPETENCIES[r.key]["anchors"]
            st.caption(" | ".join(f"{k}: {v}" for k, v in anchors.items()))
            final = st.slider("Final score", 1, 5, int(round(r.score)), key=f"s_{r.key}")
            reason = st.text_input("Reason (required if you change the AI score)", key=f"r_{r.key}")
            decisions[r.key] = {"final": final, "reason": reason.strip()}
    missing = [COMPETENCIES[k]["name"] for k, d in decisions.items()
               if d["final"] != int(round(next(r for r in results if r.key == k).score)) and not d["reason"]]
    if missing:
        st.info("Add a reason for: " + ", ".join(missing))
    a, b = st.columns(2)
    a.button("← Back", on_click=go, args=(2,))
    if b.button("Finalise →", type="primary", disabled=bool(missing)):
        st.session_state.final = decisions
        go(4)
        st.rerun()

# ---------- step 4: report ----------
elif st.session_state.step == 4:
    st.header("4 · Final report")
    results, final = st.session_state.results, st.session_state.final
    rows, changed = [], 0
    for r in results:
        d = final[r.key]
        ai = int(round(r.score))
        changed += d["final"] != ai
        rows.append({"Competency": r.name, "AI score": r.score, "AI runs": ", ".join(map(str, r.scores)),
                     "Final (human)": d["final"], "Change": d["final"] - ai,
                     "Reason": d["reason"] or ("–" if d["final"] == ai else ""),
                     "Flags": "; ".join(r.flags) or "–"})
    total = round(sum(final[r.key]["final"] for r in results) / len(results), 2)
    c1, c2, c3 = st.columns(3)
    c1.metric("Overall (human final)", f"{total} / 5")
    c2.metric("AI scores kept", f"{len(results) - changed} of {len(results)}")
    c3.metric("Human overrides", changed)
    st.dataframe(rows, width="stretch", hide_index=True)
    st.caption("Every final score was confirmed by a person. The AI provided a first read, evidence and warnings.")

    report = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "scenario": scenario["title"],
        "answer": st.session_state.answer,
        "mode": "live" if live else "demo",
        "competencies": rows,
        "overall_final": total,
    }
    md = [f"# LeadLens report – {scenario['title']}", "", f"Overall (human final): **{total} / 5**", "",
          "| Competency | AI | Runs | Final | Reason |", "|---|---|---|---|---|"]
    md += [f"| {r['Competency']} | {r['AI score']} | {r['AI runs']} | {r['Final (human)']} | {r['Reason']} |"
           for r in rows]
    a, b, c = st.columns(3)
    a.download_button("Download report (Markdown)", "\n".join(md), "leadlens_report.md")
    b.download_button("Download data (JSON)", json.dumps(report, indent=2), "leadlens_report.json")
    c.button("← Back to review", on_click=go, args=(3,))
