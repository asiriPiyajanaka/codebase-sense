# Comparison with improve-codebase-architecture

Reference: [mattpocock/skills at abeeaf9](https://github.com/mattpocock/skills/tree/abeeaf95660ba9e8b7c753eb38f441ca707a8823/skills/engineering/improve-codebase-architecture),
retrieved 2026-11-21. Source archives and SHA-256 pins are in
[evals/sources.json](../evals/sources.json). Review the source version when
interpreting this comparison; the upstream skill can evolve.

| Area | Reference skill at this commit | Codebase Sense candidate |
| --- | --- | --- |
| Primary task | Find deepening opportunities, present candidates, guide selected design | Maintain workflow understanding across audit, plan, review, verification and approved implementation |
| Architecture reasoning | Organic friction, recent changes, deletion test, deep-module vocabulary | Observed callers, contracts, invariants, counterarguments and change cost |
| Output | Visual HTML candidates and before/after diagrams | Compact Sense Card and evidence; optional JSON |
| Supporting context | codebase-design; later grilling and domain-modeling; glossary and ADRs | Self-contained references; repository instructions, domain docs and ADRs |
| No-change guidance | Exploration is framed around deepening opportunities | Explicit Keep / Investigate / Change distinction |
| Tests | Interface as test surface; coordination and testability inform candidates | Specific behavior, failure/retry outcomes, safe execution and honest coverage limits |
| Writes | Temporary HTML during exploration; glossary updates during guided design | Target source stays read-only until implementation is explicitly requested |

These are instruction-level differences, not measured advantages. Both emphasize
useful interfaces and testability. Codebase Sense should learn from the reference's
organic exploration and deletion reasoning without treating every thin module as
a defect. A deliberately small adapter or validation facade can earn its place.

The exploratory comparison uses identical audit prompts on checkout, ledger,
Click and Flask copies. The reference's required design vocabulary is available.
The harness reads dependency files directly because this Codex runtime has no
tool named `Skill`; it suppresses window opening, nested delegation and live CDN
execution. Those adaptations limit conclusions about the reference's native
interactive/visual experience. No guided design phase is compared.

Review, blocked verification and implementation are evaluated as Codebase Sense
capabilities, not scored as omissions in the reference. See the
[recorded results](../evals/results/2026-11-21/README.md) for actual outcomes and
methodological limitations. No superiority claim is supported by this small study.
