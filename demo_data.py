"""Example AI outputs for demo mode (no API key needed).

These are hand-written examples in the same format the model returns. They are
built to show the checks working: one competency where the runs disagree, and one
quote that does not appear in the candidate's answer.
"""

DEMO_RUNS = {
    "missed_deadline": [
        {
            "communication": {"score": 5, "evidence": [
                "I would tell my manager honestly what happened, the options and my recommendation",
                "I would call the client myself before the deadline"],
                "rationale": "Informs manager and client directly, with options and a recommendation."},
            "people": {"score": 4, "evidence": [
                "without blaming anyone",
                "I would not ask the two exhausted colleagues to do more overtime"],
                "rationale": "Protects tired colleagues and avoids blame, but gives little personal support."},
            "decision": {"score": 4, "evidence": [
                "reduce the scope for this delivery, ask for a short extension, or move one person from another task"],
                "rationale": "Weighs three options and picks one, though risks are only briefly covered."},
            "ownership": {"score": 4, "evidence": [
                "I would hold a short team retrospective",
                "I take full responsibility for the delay"],
                "rationale": "Owns the client call and adds a retrospective to prevent repeats."},
        },
        {
            "communication": {"score": 5, "evidence": ["I would call the client myself"],
                "rationale": "Clear, honest messages to manager and client."},
            "people": {"score": 3, "evidence": ["without blaming anyone"],
                "rationale": "Acknowledges the team's situation, little concrete support."},
            "decision": {"score": 4, "evidence": ["my recommendation, which is to deliver the most important part on time"],
                "rationale": "Clear, justified decision among options."},
            "ownership": {"score": 4, "evidence": ["hold a short team retrospective"],
                "rationale": "Takes responsibility and plans follow-up."},
        },
        {
            "communication": {"score": 5, "evidence": ["tell my manager honestly"],
                "rationale": "Honest, tailored communication."},
            "people": {"score": 5, "evidence": ["I would not ask the two exhausted colleagues to do more overtime"],
                "rationale": "Strong care for team wellbeing."},
            "decision": {"score": 4, "evidence": ["look at the options"],
                "rationale": "Considers options and decides."},
            "ownership": {"score": 4, "evidence": ["call the client myself"],
                "rationale": "Owns the outcome."},
        },
    ],
    "conflict": [
        {
            "communication": {"score": 2, "evidence": ["talk to both of them separately first"],
                "rationale": "Plans conversations, but says nothing about informing the wider team."},
            "people": {"score": 3, "evidence": ["to hear their view"],
                "rationale": "Listens to both sides, but ignores the effect on the rest of the team."},
            "decision": {"score": 2, "evidence": ["I make the decision so we can move on"],
                "rationale": "Decides quickly without weighing the technical options."},
            "ownership": {"score": 3, "evidence": ["I make the decision"],
                "rationale": "Takes charge, but no follow-up on the personal conflict."},
        },
        {
            "communication": {"score": 2, "evidence": [], "rationale": "Little communication beyond two meetings."},
            "people": {"score": 2, "evidence": [], "rationale": "Does not address the personal tension."},
            "decision": {"score": 2, "evidence": ["I make the decision"], "rationale": "No trade-offs considered."},
            "ownership": {"score": 3, "evidence": ["I make the decision"], "rationale": "Takes charge."},
        },
        {
            "communication": {"score": 2, "evidence": [], "rationale": "Limited communication."},
            "people": {"score": 3, "evidence": ["hear their view"], "rationale": "Some listening."},
            "decision": {"score": 3, "evidence": ["I make the decision"], "rationale": "Makes a decision."},
            "ownership": {"score": 3, "evidence": ["Then we meet together"], "rationale": "Owns the next step."},
        },
    ],
}
