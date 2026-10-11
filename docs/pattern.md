# Design notes

## Decisions

**One page, no framework.** The audience is a hiring manager or an operator with three minutes. A single HTML file with vanilla JavaScript loads instantly, has nothing to build, and is readable top to bottom. The trade is that the editable brief is a set of `contenteditable` spans that write back into a JSON object by path, which is enough for a demo and would be a form library in a product.

**Skills as markdown files.** The three files in `skills/` are the product, and the prompt strings in code are one line that joins them. The voice file sets the rules for everything the model writes; the step files define the job and the JSON schema. The system prompt is just the two files concatenated, and the page shows them, so there's nothing hidden.

**JSON out, rendered in.** The model returns JSON for both steps. The page streams the raw text into a small monospace box so the visitor sees it working, then parses and renders the document when the stream ends. Streaming partial JSON into a rendered document would be prettier and much more code.

**Offline mode is a real mode.** With no key the server replays the recorded example that matches the intake (by example id, then by feature name). That means the demo, the tests and the screenshot all work on a laptop with no account, and the live path is the only thing that needs a key.

**Caps in memory.** The daily and per-address counters live in the process. A restart resets them, which on a free host that sleeps between visits means the cap is softer than it looks. For a demo that's acceptable; for anything real the counter goes in a store.

**Invented owners.** Approved bets get a made-up owner name by role so the queue reads like a real one. The names are in `index.html` and mean nothing.

**Tests check the rules.** The offline tests assert the shape of the examples and the house rules (tier names, three segments, four to six channels, a hypothesis that starts with "If", no hype vocabulary, no em dashes). The live test asserts the same shape on a real call. There is no golden-output comparison on live calls because the model's wording changes run to run and that's fine.

## What I'd change for production

- Persist the queue and the briefs per workspace instead of the browser.
- Add a review step between brief and bets where a second reader marks what's wrong, and feed that back as a skill revision rather than a one-off edit.
- Record every run (intake, brief, bets, edits) so the skill files can be improved from what people actually changed.
- Measure the three numbers in the README: intake-to-approved-brief time, bet win rate, share of wins that became permanent.

## Open choices

- **Model.** Defaults to a mid-size model for speed and cost on a public demo. A larger model writes a better brief and costs more per run.
- **Live recording of examples.** The three examples were written to the schema by hand so the demo works without a key. Running `pytest --live` checks the live shape; re-recording the examples from live runs is a one-line script away if the wording should come from the model.
- **Edit history.** Edits to the brief are not tracked. A diff view (what the model wrote versus what the PM changed) would be the single most useful addition for improving the skills.
- **Queue export.** No export yet. A CSV or a copy-to-clipboard of the queue is cheap and probably worth it.
- **Hosting.** Render is the simpler path (one Blueprint, no CLI). Fly scales to zero and wakes faster. Both configs are in the repo.
