# Navigate — Routing Catalog

Cold-path content extracted from `navigate/SKILL.md` so the hub skill stays lean. The runtime source of truth for routing keywords and regex patterns is `routing-rules.json`, consumed by `hooks/scripts/route-user-prompt.py` on every `UserPromptSubmit`. This file is the human-and-machine-readable summary surfaced to the agent during navigation.

## Routing Table

Human-readable summary:

| Goal | Dispatch Target |
|------|----------------|
| Build or scaffold a protocol model | `build` workflow |
| Verify or debug a specification | `verify` workflow |
| Review quality or coverage | `review` workflow |
| Diagnose broken tools | `triage` workflow |
| Learn methodology | `methodology` skill |
| Extract RFC requirements | `traceability-agent` agent |

Machine-readable call graph:

<dispatch target="build" via="skill" trigger="build or scaffold a protocol model"/>
<dispatch target="verify" via="skill" trigger="verify or debug a specification"/>
<dispatch target="review" via="skill" trigger="review quality or coverage"/>
<dispatch target="triage" via="skill" trigger="diagnose broken tools"/>
<dispatch target="methodology" via="skill" trigger="learn methodology"/>
<dispatch target="traceability-agent" via="agent" trigger="extract RFC requirements"/>

<branch condition="user's goal does not clearly map to any target above" name="clarify">
  Ask one clarifying question before dispatching.
</branch>
