# Phase Gate Details

## Phase 1: EXPLORE — Gate Conditions
- spec-analyst agent MUST have returned findings (directory summary, include graph, coverage stats)
- User MUST have confirmed direction ("What do you want to build/change?")
- If user asks to skip: REFUSE. Explain that unexamined specs cause the most verification failures.

**Entry criteria:** Deep-mode workflow initiated (via /nct-scaffold, methodology skill trigger, or free-form request)
**Exit criteria:** User confirms direction after reviewing findings

## Phase 2: PLAN — Gate Conditions
- Requirement list MUST exist (for NCT/NACT: from traceability-agent; for NSCT: from user topology description)
- Layer mapping MUST be presented and approved by user
- File plan MUST list every file to create/modify with exact paths

**Entry criteria:** Phase 1 gate passed
**Exit criteria:** User approves layer mapping and file plan

## Phase 3: WRITE — Gate Conditions
- Each layer MUST be reviewed by user before proceeding to next
- All Ivy syntax MUST follow ivy-writing-guide conventions
- Bracket-tag annotations MUST be added for any new assertions

**Entry criteria:** Phase 2 gate passed
**Exit criteria:** All layers written and individually approved

## Phase 4: VERIFY — Gate Conditions
- ivy_verify MUST pass on ALL new/modified files
- ivy_diagnostics(mode="structural") MUST report no errors
- model-reviewer agent MUST report no CRITICAL issues
- Max 3 fix attempts. After 3 failures: STOP and escalate to user

**Entry criteria:** Phase 3 gate passed
**Exit criteria:** All checks pass OR user provides direction after escalation

## Phase 5: FINALIZE — Gate Conditions
- ivy_compile MUST succeed (if compilation is requested)
- traceability-agent MUST have produced coverage report
- User MUST review coverage gaps

**Entry criteria:** Phase 4 gate passed
**Exit criteria:** User acknowledges final report

## Bypass Prevention
- NEVER accept "let's skip exploration" — even for single-file changes
- NEVER accept "I already know the spec" — state changes between sessions
- NEVER compile without Phase 4 verification — broken binaries waste more time
- If user EXPLICITLY requests fast mode, route to a FAST-mode command instead of bypassing gates
