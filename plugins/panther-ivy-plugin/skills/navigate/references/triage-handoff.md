# Navigate — Triage Preflight Handoff

Cold-path content extracted from `navigate/SKILL.md` so the hub skill stays lean. Loaded automatically by `auto-load-skill-references.py` when navigate is invoked. Documents the preflight outcome handling, the preflight-to-full escalation path, and the relationship to user-driven triage requests.

## Step 4: Run triage preflight (inline)

Confirm stack health before proceeding. Preflight is loaded inline as a skill call with `args="preflight"` — no state writes, no workflow dispatch:

```
Skill(skill="panther-ivy-plugin:triage", args="preflight")
```

Triage's Phase 1 runs in preflight mode (read-only health checks), returns a pass/fail summary to navigate's current turn, and does not alter `active-workflow`. Navigate stays on `phase = "context-scan"` throughout.

<outcome verdict="preflight-pass">
  Proceed to Step 5 (Situation Briefing).
</outcome>

<outcome verdict="preflight-fail">
  Surface the failing checks to the user via `AskUserQuestion`. Offer these options:

  - **Run triage interactively to diagnose and repair** — dispatch `triage` as a full workflow.
    <dispatch target="triage" via="pending_dispatch" reason="preflight failed"/>
    Triage Phase 2–3 runs interactively. On repair completion triage emits
    `pending_dispatch(<caller>, reason="post-triage-repair")` handing control
    back, so navigate re-enters on the next turn via Phase 1 Step 2c and
    picks up where it left off. **This is a blocking escalation** — the user
    will complete a full triage cycle before navigate resumes, so announce
    that explicitly in the `AskUserQuestion` option description.

  - **Continue anyway** — record the failure in a `progress` journal entry
    (`{kind: "preflight_skipped", reason: "<user chose continue"}`) and
    proceed to Step 5. Downstream workflows (`build`, `verify`, `review`)
    may still fail on the underlying issue, but the user has explicitly
    chosen to defer the fix.
</outcome>

Users who type "things are broken" or similar still dispatch triage as a full workflow via Phase 2's routing table — the preflight-to-full escalation path documented above is a separate branch triggered by a failed preflight check, not by the user's direct request.
