"""Leadership scenarios and the competency model used for scoring.

Each competency has behavioural anchors for levels 1, 3 and 5, so that the
AI and the human assessor score against the same written standard.
"""

COMPETENCIES = {
    "communication": {
        "name": "Clear communication",
        "anchors": {
            1: "Message is vague or one-sided; key people are not informed.",
            3: "Explains the situation and next steps, but misses some audiences or the 'why'.",
            5: "Tailors a clear, honest message to each audience and explains the reasons.",
        },
    },
    "people": {
        "name": "People focus",
        "anchors": {
            1: "Ignores how the team feels or blames individuals.",
            3: "Acknowledges people's concerns, but offers little concrete support.",
            5: "Listens, recognises emotions and gives concrete support while keeping standards.",
        },
    },
    "decision": {
        "name": "Decision quality",
        "anchors": {
            1: "Acts without weighing options or facts.",
            3: "Considers some options, but trade-offs or risks stay unclear.",
            5: "Gathers key facts, weighs options and risks, and makes a clear, justified decision.",
        },
    },
    "ownership": {
        "name": "Ownership",
        "anchors": {
            1: "Waits for others or shifts responsibility.",
            3: "Takes responsibility for parts of the problem, follow-up is unclear.",
            5: "Takes full responsibility, sets clear next steps and follows up.",
        },
    },
}

SCENARIOS = [
    {
        "id": "missed_deadline",
        "title": "The missed deadline",
        "text": (
            "You lead a team of six. Two days before an important client delivery, a senior team "
            "member tells you that a key part will not be ready. The client is already nervous, "
            "and two other team members are close to burnout after weeks of overtime. "
            "Your manager expects an update this afternoon.\n\n"
            "What do you do in the next 24 hours, and why?"
        ),
        "sample_answer": (
            "First I would sit down with the senior team member to understand exactly what is missing "
            "and why, without blaming anyone. Then I would look at the options: reduce the scope for this "
            "delivery, ask for a short extension, or move one person from another task. I would not ask the "
            "two exhausted colleagues to do more overtime. This afternoon I would tell my manager honestly "
            "what happened, the options and my recommendation, which is to deliver the most important part "
            "on time and agree a new date for the rest. I would call the client myself before the deadline, "
            "explain the plan and confirm what they will receive. Afterwards I would hold a short team "
            "retrospective so we notice risks earlier next time."
        ),
    },
    {
        "id": "conflict",
        "title": "Conflict between two colleagues",
        "text": (
            "Two experienced colleagues in your team openly disagree about how to build a new feature. "
            "The discussion has become personal in meetings, and other team members have started to "
            "avoid them. The feature is due in three weeks.\n\n"
            "How do you handle this situation?"
        ),
        "sample_answer": (
            "I would talk to both of them separately first to hear their view. Then we meet together and "
            "I make the decision so we can move on."
        ),
    },
    {
        "id": "ai_rollout",
        "title": "Rolling out an AI tool",
        "text": (
            "Your company wants every consultant to use a new AI tool for writing reports. Some people in "
            "your team are excited, others are worried it will make their work less valuable or produce "
            "mistakes that clients will notice.\n\n"
            "How do you introduce the tool in your team over the next month?"
        ),
        "sample_answer": "",
    },
]
