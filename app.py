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
import ui

st.set_page_config(page_title="LeadLens – AI-assisted assessment", page_icon="🖍️", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)

# ---------- state ----------
# "answer" belongs to the text box, which Streamlit clears when the box is not on screen,
# so the submitted text is kept separately in "submitted".
defaults = {"step": 1, "results": None, "answer": "", "submitted": "", "scenario_id": SCENARIOS[0]["id"], "final": None}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)


def go(step: int):
    st.session_state.step = step


# ---------- sidebar ----------
with st.sidebar:
    st.markdown("### Settings")
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
    try:
        model_default = st.secrets.get("GROQ_MODEL", DEFAULT_MODEL)
    except Exception:
        model_default = DEFAULT_MODEL
    model = st.text_input("Model", model_default, disabled=not live,
                          help="If this model is retired, the app automatically falls back to another Groq model.")
    st.divider()
    if st.button("Start over"):
        for k, v in defaults.items():
            st.session_state[k] = v
        st.rerun()

scenario = next(s for s in SCENARIOS if s["id"] == st.session_state.scenario_id)

st.markdown(ui.masthead() + ui.stepper(st.session_state.step), unsafe_allow_html=True)

# ---------- step 1: candidate ----------
if st.session_state.step == 1:
    titles = {s["title"]: s["id"] for s in SCENARIOS}
    chosen = st.radio("Choose a scenario", list(titles), horizontal=True,
                      index=list(titles.values()).index(scenario["id"]))
    if titles[chosen] != st.session_state.scenario_id:
        st.session_state.scenario_id = titles[chosen]
        st.session_state.answer = ""
        st.session_state.submitted = ""
        st.rerun()
    st.markdown(ui.scenario_card(scenario["title"], scenario["text"]), unsafe_allow_html=True)
    st.write("")
    if not st.session_state.answer:
        st.session_state.answer = st.session_state.submitted or scenario["sample_answer"]
    answer = st.text_area("Your answer", key="answer", height=220,
                          placeholder="Write what you would do in this situation, and why.")
    words = len(answer.split())
    has_demo = scenario["id"] in DEMO_RUNS
    st.caption(f"{words} words" + ("" if words >= 15 else " · write at least 15 to get a first read"))
    if not live and not has_demo:
        st.warning("Demo mode has example AI output for the first two scenarios only. "
                   "Switch to Live AI in the settings to score this one.")
    if not live and has_demo:
        st.caption("Demo mode uses prepared AI output. The evidence check still runs on the text above, "
                   "so if you edit the answer, the marks change.")
    disabled = words < 15 or (not live and not has_demo) or (live and not api_key)
    if st.button(f"Get the AI's first read ({runs} run{'s' if runs > 1 else ''})", type="primary", disabled=disabled):
        with st.spinner(f"The AI is reading the answer {runs} time{'s' if runs > 1 else ''}…"):
            try:
                st.session_state.submitted = answer
                st.session_state.results = assess(
                    scenario["text"], answer, runs=runs, api_key=api_key, model=model,
                    demo_runs=None if live else DEMO_RUNS[scenario["id"]])
                go(2)
                st.rerun()
            except Exception as e:  # show the problem instead of crashing
                st.error(f"The AI could not score the answer. {e}")

# ---------- step 2: AI assessment ----------
elif st.session_state.step == 2:
    results = st.session_state.results
    flagged = [r for r in results if r.needs_human]
    n = len(results[0].scores)
    if flagged:
        names = ", ".join(r.name for r in flagged)
        st.markdown(f'<div class="ll-summary">The AI read the answer {n} times. '
                    f'It is not reliable enough on <b>{names}</b>, so those go to the assessor first.</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="ll-summary ok">The AI read the answer {n} times and <b>agreed with itself</b> '
                    f'on every competency. The assessor still makes the final call.</div>', unsafe_allow_html=True)
    left, right = st.columns([1, 1.15], gap="large")
    with left:
        st.markdown("#### The answer, marked up")
        st.markdown(ui.marked_answer(st.session_state.submitted, results) + ui.legend(results),
                    unsafe_allow_html=True)
        st.caption("Highlighted text is the evidence the AI quoted. Every quote was checked against the answer.")
        used = getattr(assess, "last_model", None)
        if live and used:
            st.caption(f"Model: {used}")
    with right:
        st.markdown("#### Scores and the AI's notes")
        st.markdown("".join(ui.comp_card(r) for r in sorted(results, key=lambda r: not r.needs_human)),
                    unsafe_allow_html=True)
    a, b = st.columns(2)
    a.button("Back to the answer", on_click=go, args=(1,))
    b.button("Send to assessor review", type="primary", on_click=go, args=(3,))

# ---------- step 3: assessor review ----------
elif st.session_state.step == 3:
    st.markdown('<div class="ll-summary">You decide. Flagged competencies come first. '
                'If you change the AI\'s score, write one line on why. Those reasons are how the rubric '
                'and the AI get better.</div>', unsafe_allow_html=True)
    results = st.session_state.results
    with st.expander("Show the marked-up answer"):
        st.markdown(ui.marked_answer(st.session_state.submitted, results) + ui.legend(results),
                    unsafe_allow_html=True)
    decisions = {}
    for r in sorted(results, key=lambda r: not r.needs_human):
        with st.container(border=True):
            ai = int(round(r.score))
            top, side = st.columns([1.3, 1], gap="large")
            with top:
                st.markdown(f'<div class="ll-comp-name" style="border-left:8px solid {ui.HIGHLIGHT[r.key]};'
                            f'padding-left:.6rem">{r.name}</div>', unsafe_allow_html=True)
                final = st.slider("Your score", 1, 5, ai, key=f"s_{r.key}")
                st.markdown(ui.strip(r.scores, human=final) + '<div class="ll-strip-cap">Dots are the AI runs (a number means several runs gave that score). '
                            'The red marker is your score.</div>', unsafe_allow_html=True)
            with side:
                anchors = COMPETENCIES[r.key]["anchors"]
                st.caption("\n\n".join(f"**{k}** · {v}" for k, v in anchors.items()))
            reason = st.text_input("Why did you change it?" if final != ai else "Note (optional)",
                                   key=f"r_{r.key}",
                                   placeholder="e.g. They protect the team but offer no personal support.")
            if r.needs_human:
                st.markdown("".join(f'<span class="ll-flag">{f}</span>' for f in r.flags), unsafe_allow_html=True)
            decisions[r.key] = {"final": final, "reason": reason.strip()}
    missing = [COMPETENCIES[k]["name"] for k, d in decisions.items()
               if d["final"] != int(round(next(r for r in results if r.key == k).score)) and not d["reason"]]
    if missing:
        st.info("Add a reason for: " + ", ".join(missing))
    a, b = st.columns(2)
    a.button("Back to the AI's first read", on_click=go, args=(2,))
    if b.button("Finalise the assessment", type="primary", disabled=bool(missing)):
        st.session_state.final = decisions
        go(4)
        st.rerun()

# ---------- step 4: report ----------
elif st.session_state.step == 4:
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
    left, right = st.columns([1, 2], gap="large")
    with left:
        st.markdown(f'<div class="ll-big">{total:g}<small> / 5 overall</small></div>', unsafe_allow_html=True)
        st.write("")
        st.markdown(f"**{len(results) - changed} of {len(results)}** AI scores kept, "
                    f"**{changed}** changed by the assessor.")
        st.caption("Every final score was confirmed by a person. The AI gave a first read, evidence and warnings.")
    with right:
        for r in results:
            d = final[r.key]
            reason = f" — {d['reason']}" if d["reason"] else ""
            st.markdown(f'<div class="ll-comp" style="--hl:{ui.HIGHLIGHT[r.key]};margin-bottom:.6rem">'
                        f'<div class="ll-comp-head"><div class="ll-comp-name">{r.name}</div>'
                        f'<div class="ll-score">{d["final"]}<small> / 5</small></div></div>'
                        f'{ui.strip(r.scores, human=d["final"])}'
                        f'<div class="ll-strip-cap">AI runs {", ".join(map(str, r.scores))}, '
                        f'final {d["final"]}{reason}</div></div>', unsafe_allow_html=True)
    with st.expander("Table view"):
        st.dataframe(rows, width="stretch", hide_index=True)

    report = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "scenario": scenario["title"],
        "answer": st.session_state.submitted,
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
    c.button("Back to review", on_click=go, args=(3,))
