# Skill: GTM brief

Turn a feature intake into a GTM brief the launch team can act on without a meeting.

## Decide the launch tier first
- **major**: changes what Halden is for, touches pricing, or gives sales a new reason to call every account.
  Earns a release moment, a customer story and a sales kickoff.
- **standard**: a feature customers asked for that improves an existing workflow. Earns release notes, one
  email to the affected segment, enablement for CSMs, and a help article.
- **quiet**: fixes, small conveniences, admin settings. Earns release notes and a help article. Nothing else.
Most intakes are standard. Say why you chose the tier in one sentence.

## Positioning statement
One sentence a dispatcher could repeat: who it's for, what it does, why that matters on a Tuesday.
No adjectives that could apply to any product.

## Segments
Exactly three audience segments. For each: who they are inside the customer (role and situation), the one
message for them in their words, and the proof that message needs (a number, a demo moment or a customer
quote the team must go get).

## Channel plan
Four to six channels, each with the play and the timing relative to launch (for example "two weeks before",
"launch day", "30 days after"). Only channels Halden actually has: in-app announcement, release notes, customer
email, CSM talk track, sales battlecard, help center, webinar, partner newsletter, trade association, direct
mail to dispatch offices.

## Risks
Two to four risks in plain words, each with what would show it's happening. Include the pricing risk when
the pricing impact is add-on or tier gate.

## Sales proof
Three to five things sales will ask for before they'll talk about it, in priority order.

## Output schema (JSON only)
{
  "launch_tier": "major | standard | quiet",
  "tier_reason": "one sentence",
  "positioning": "one sentence",
  "segments": [
    {"name": "short label", "who": "role and situation", "message": "their words", "proof_needed": "what to go get"}
  ],
  "channels": [
    {"channel": "name", "play": "what we do there", "timing": "relative to launch"}
  ],
  "risks": [
    {"risk": "plain words", "signal": "what would show it's happening"}
  ],
  "sales_proof": ["in priority order"]
}
