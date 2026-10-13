"""Visual layer for LeadLens: the 'assessor's notebook' look.

Each competency has its own highlighter colour. The candidate's answer is shown with
the evidence the AI used marked in that colour, and every competency has a
consistency strip: a 1-5 scale with one dot per AI run.
"""

from __future__ import annotations

import html
import re

INK = "#1D2A3A"
PAPER = "#EEF1F4"
FLAG = "#B3264E"
HIGHLIGHT = {
    "communication": "#F5D547",
    "people": "#7FD6B5",
    "decision": "#8CB8FF",
    "ownership": "#F2A7C3",
}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700;800&family=Kalam:wght@400;700&display=swap');

html, body, [class*="css"], .stMarkdown, .stTextArea textarea, .stTextInput input, button {{
  font-family: 'Public Sans', system-ui, sans-serif !important;
}}
.block-container {{ padding-top: 2.2rem; max-width: 1180px; }}
h1, h2, h3, h4 {{ font-family: 'Public Sans', sans-serif !important; letter-spacing: -0.02em; color: {INK}; }}

/* masthead */
.ll-mast {{ display:flex; align-items:baseline; gap:1rem; flex-wrap:wrap; margin-bottom:.4rem; }}
.ll-mast .name {{ font-size:2.6rem; font-weight:800; letter-spacing:-0.045em; color:{INK}; line-height:1; }}
.ll-mast .name span {{ background: linear-gradient(transparent 58%, {HIGHLIGHT['communication']} 58%, {HIGHLIGHT['communication']} 92%, transparent 92%); padding: 0 .1em; }}
.ll-mast .tag {{ font-size:1.05rem; color:#4A5868; }}

/* stepper: a real sequence, so numbers are earned */
.ll-steps {{ display:flex; gap:0; margin:1.1rem 0 1.8rem; border-bottom:2px solid #CBD3DC; }}
.ll-step {{ flex:1; padding:.55rem .2rem .7rem; color:#7A8796; font-weight:500; font-size:.95rem; position:relative; }}
.ll-step b {{ font-weight:700; margin-right:.35rem; }}
.ll-step.done {{ color:{INK}; }}
.ll-step.active {{ color:{INK}; font-weight:700; }}
.ll-step.active::after {{ content:""; position:absolute; left:0; right:12%; bottom:-2px; height:4px; background:{INK}; border-radius:2px; }}

/* scenario card */
.ll-scenario {{ background:#fff; border-left:5px solid {INK}; padding:1.1rem 1.3rem; border-radius:4px 10px 10px 4px; line-height:1.6; color:{INK}; max-width:78ch; }}
.ll-scenario h3 {{ margin:0 0 .4rem; font-size:1.25rem; }}

/* marked-up answer */
.ll-paper {{ background:#fff; border-radius:10px; padding:1.3rem 1.4rem; line-height:1.95; font-size:1.02rem; color:{INK};
  box-shadow: 0 1px 0 #D5DCE4; }}
.ll-paper mark {{ padding: .05em .15em; border-radius: 3px; color:{INK}; }}
.ll-legend {{ display:flex; flex-wrap:wrap; gap:.4rem .9rem; margin:.6rem 0 0; font-size:.88rem; color:#4A5868; }}
.ll-legend i {{ display:inline-block; width:.85rem; height:.85rem; border-radius:3px; margin-right:.35rem; vertical-align:-1px; }}

/* competency row */
.ll-comp {{ background:#fff; border-radius:10px; padding:1rem 1.2rem 1.1rem; margin-bottom:.9rem; border-left:8px solid var(--hl); }}
.ll-comp.flagged {{ box-shadow: inset 0 0 0 2px {FLAG}; }}
.ll-comp-head {{ display:flex; justify-content:space-between; align-items:center; gap:1rem; flex-wrap:wrap; }}
.ll-comp-name {{ font-weight:700; font-size:1.12rem; color:{INK}; }}
.ll-score {{ font-weight:800; font-size:1.7rem; letter-spacing:-0.03em; color:{INK}; }}
.ll-score small {{ font-size:.95rem; color:#7A8796; font-weight:500; }}
.ll-note {{ font-family:'Kalam', cursive; font-size:1.12rem; color:#2F4A6B; margin:.35rem 0 .5rem; line-height:1.4; }}
.ll-flag {{ display:inline-block; color:{FLAG}; font-weight:600; font-size:.88rem; margin:.25rem .8rem 0 0; }}
.ll-quote-bad {{ color:{FLAG}; font-size:.9rem; margin-top:.3rem; }}
.ll-quote-bad s {{ text-decoration-thickness:2px; }}

/* consistency strip: the one bold element */
.ll-strip {{ position:relative; height:52px; margin:.6rem 0 .1rem; max-width:420px; }}
.ll-strip .axis {{ position:absolute; left:0; right:0; top:28px; height:2px; background:#CBD3DC; }}
.ll-strip .tick {{ position:absolute; top:22px; width:2px; height:14px; background:#CBD3DC; transform:translateX(-1px); }}
.ll-strip .lbl {{ position:absolute; top:38px; font-size:.75rem; color:#7A8796; transform:translateX(-50%); }}
.ll-strip .range {{ position:absolute; top:23px; height:12px; border-radius:6px; background:rgba(179,38,78,.16); }}
.ll-strip .dot {{ position:absolute; top:21px; width:16px; height:16px; border-radius:50%; background:{INK}; border:2px solid #fff;
  transform:translate(-50%, 0); box-shadow:0 0 0 1px {INK}; color:#fff; font-size:.62rem; font-weight:700;
  display:flex; align-items:center; justify-content:center; }}
.ll-strip .dot.many {{ width:22px; height:22px; top:18px; }}
.ll-strip .human {{ position:absolute; top:0; width:0; height:0; transform:translateX(-7px);
  border-left:7px solid transparent; border-right:7px solid transparent; border-top:11px solid {FLAG}; }}
.ll-strip-cap {{ font-size:.82rem; color:#4A5868; }}

/* summary line */
.ll-summary {{ font-size:1.15rem; color:{INK}; margin:.2rem 0 1.2rem; max-width:70ch; }}
.ll-summary b {{ color:{FLAG}; }}
.ll-summary.ok b {{ color:#1F7A55; }}

/* report */
.ll-big {{ font-size:3.4rem; font-weight:800; letter-spacing:-0.05em; color:{INK}; line-height:1; }}
.ll-big small {{ font-size:1.2rem; color:#7A8796; font-weight:500; letter-spacing:0; }}

.stButton button[kind="primary"] {{ background:{INK}; border-color:{INK}; }}
.stButton button[kind="primary"]:hover {{ background:#2C3E55; border-color:#2C3E55; }}
button:focus-visible, textarea:focus-visible, input:focus-visible {{ outline:3px solid {HIGHLIGHT['decision']} !important; outline-offset:2px; }}
@media (max-width: 640px) {{ .ll-mast .name {{ font-size:2rem; }} .ll-step {{ font-size:.8rem; }} .ll-step b {{ display:block; }} }}
</style>
"""

STEP_NAMES = ["Candidate answer", "AI first read", "Assessor review", "Final report"]


def masthead() -> str:
    return ('<div class="ll-mast"><div class="name"><span>LeadLens</span></div>'
            '<div class="tag">The AI reads first. A person decides.</div></div>')


def stepper(current: int) -> str:
    parts = []
    for i, name in enumerate(STEP_NAMES, start=1):
        cls = "active" if i == current else ("done" if i < current else "")
        parts.append(f'<div class="ll-step {cls}"><b>{i}</b>{name}</div>')
    return f'<div class="ll-steps">{"".join(parts)}</div>'


def scenario_card(title: str, text: str) -> str:
    body = "<br>".join(html.escape(p) for p in text.split("\n") if p.strip())
    return f'<div class="ll-scenario"><h3>{html.escape(title)}</h3>{body}</div>'


def _quote_pattern(quote: str) -> re.Pattern | None:
    words = re.findall(r"\w+", quote)
    if not words:
        return None
    return re.compile(r"\W+".join(re.escape(w) for w in words), re.IGNORECASE)


def marked_answer(answer: str, results) -> str:
    """The candidate's answer with each verified quote highlighted in its competency colour."""
    spans = []  # (start, end, key)
    for r in results:
        for q in r.verified_evidence:
            pat = _quote_pattern(q)
            m = pat.search(answer) if pat else None
            if m:
                spans.append((m.start(), m.end(), r.key))
    spans.sort()
    out, pos = [], 0
    for start, end, key in spans:
        if start < pos:          # overlapping evidence: keep the first mark
            continue
        out.append(html.escape(answer[pos:start]))
        out.append(f'<mark style="background:{HIGHLIGHT[key]}">{html.escape(answer[start:end])}</mark>')
        pos = end
    out.append(html.escape(answer[pos:]))
    return f'<div class="ll-paper">{"".join(out)}</div>'


def legend(results) -> str:
    items = "".join(f'<span><i style="background:{HIGHLIGHT[r.key]}"></i>{html.escape(r.name)}</span>'
                    for r in results)
    return f'<div class="ll-legend">{items}</div>'


def _x(score: float) -> float:
    return (score - 1) / 4 * 100


def strip(scores: list[int], human: int | None = None) -> str:
    """A 1-5 scale with one dot per AI run; stacked dots mean the runs agreed."""
    ticks = "".join(f'<div class="tick" style="left:{_x(v)}%"></div><div class="lbl" style="left:{_x(v)}%">{v}</div>'
                    for v in range(1, 6))
    rng = ""
    if max(scores) != min(scores):
        rng = (f'<div class="range" style="left:calc({_x(min(scores))}% - 8px);'
               f'width:calc({_x(max(scores)) - _x(min(scores))}% + 16px)"></div>')
    counts = {}
    for s in scores:
        counts[s] = counts.get(s, 0) + 1
    dots = []
    for s, n in sorted(counts.items()):
        label = f"{n}" if n > 1 else ""
        cls = "dot many" if n > 1 else "dot"
        dots.append(f'<div class="{cls}" style="left:{_x(s)}%" title="{n} run(s) gave {s}">{label}</div>')
    hum = f'<div class="human" style="left:{_x(human)}%" title="Assessor score"></div>' if human else ""
    return f'<div class="ll-strip"><div class="axis"></div>{ticks}{rng}{"".join(dots)}{hum}</div>'


def strip_caption(scores: list[int]) -> str:
    if len(scores) == 1:
        return "One AI run, so consistency is unknown."
    if max(scores) == min(scores):
        return f"All {len(scores)} AI runs agreed."
    return f"The {len(scores)} AI runs disagreed: {', '.join(map(str, scores))}."


def comp_card(r) -> str:
    flagged = " flagged" if r.needs_human else ""
    flags = "".join(f'<span class="ll-flag">{html.escape(f)}</span>' for f in r.flags)
    bad = "".join(f'<div class="ll-quote-bad">Quote not found in the answer: <s>“{html.escape(q)}”</s></div>'
                  for q in r.unverified_evidence)
    note = html.escape(r.rationale) if r.rationale else "No reason given."
    return (f'<div class="ll-comp{flagged}" style="--hl:{HIGHLIGHT[r.key]}">'
            f'<div class="ll-comp-head"><div class="ll-comp-name">{html.escape(r.name)}</div>'
            f'<div class="ll-score">{r.score:g}<small> / 5</small></div></div>'
            f'{strip(r.scores)}<div class="ll-strip-cap">{strip_caption(r.scores)}</div>'
            f'<div class="ll-note">{note}</div>{bad}{flags}</div>')
