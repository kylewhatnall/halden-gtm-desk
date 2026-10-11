# Skill: marketing bets

Turn an approved GTM brief into marketing bets. A bet is a small experiment with a target set before it
starts, so the team learns something whether it wins or loses.

## What makes a bet
- **One change.** A bet changes one thing: a message, a channel, an offer, a sequence, a page. If you need
  "and" to describe the change, it's two bets.
- **A hypothesis** in the form "If we [change], then [audience] will [behavior], because [reason from the brief]."
- **A win target set before it starts.** A number and a baseline or assumption. "12% of in-app views click
  through, against 7% on the last three announcements." If there's no baseline, state the assumption.
- **A fixed window** in weeks. Two to six. Nothing open ended.
- **Scores**: expected impact 1 to 5 (5 moves pipeline or retention for the whole segment) and effort 1 to 5
  (5 needs engineering or a budget). Be honest; most bets are impact 2 to 3.
- **An owner role**, invented: PMM, lifecycle marketer, CSM lead, sales enablement, content, partner manager.

## Mix
Four to six bets. At least one cheap and fast (effort 1 or 2, two weeks). At least one aimed at existing
customers and one at pipeline. No bet may repeat a channel play already in the brief word for word; the bet
is the test of that play, so it must name what's being varied.

## Order
Return bets sorted by impact descending, then effort ascending.

## Output schema (JSON only)
{
  "bets": [
    {
      "title": "short imperative",
      "hypothesis": "If we ..., then ..., because ...",
      "change": "the one thing that changes",
      "win_target": "number plus baseline or assumption",
      "window_weeks": 2,
      "impact": 3,
      "effort": 2,
      "owner_role": "PMM"
    }
  ]
}
