# Evidence-first module decision rubric

## Signals to inspect, not metrics to game

1. **Coordination leakage:** Caller must know sequencing, retries, rollback, or policy across several helpers.
2. **Concept scattering:** One business rule is implemented or described in multiple modules; a simple change forces disconnected edits.
3. **Thin interfaces:** Many exported operations expose internal steps but hide few decisions; deleting a wrapper may actually simplify understanding.
4. **Fragile seam:** Multiple callers independently implement the same validation/failure path.
5. **Hollow tests:** Tests prove mocked collaboration happened, but don't assert the system's behavioral guarantee.
6. **Change pressure:** Recent changes repeatedly land in the same group of files; use git evidence only if available.

Multiple files or many function calls are **not alone** evidence of bad architecture. More test files are not inherently bad. Public libraries, plugins, and independently deployed systems may need wider interfaces.

## Check the counterargument

For each candidate ask:

- Is the present split intentional because modules have separate lifecycles or team ownership?
- Is the existing interface already stable and easy to use despite large implementation complexity?
- Would deepening this module cause one module to accumulate unrelated responsibilities?
- Would moving code obscure transaction, authorization, or failure boundaries?
- Does an ADR, performance requirement, or framework constraint justify it?
- Can a behavioral test improvement solve the problem without architecture changes?

## Recommendation rules

- **Change:** show specific repeated friction, a stable responsibility, a smaller public contract, protected invariants, and a migration path.
- **Investigate:** show concrete suspicious evidence but missing callers/tests/constraints. Propose the smallest fact-finding task.
- **Keep:** existing separation has a meaningful reason, change cost outweighs demonstrated benefit, or the evidence gate fails.

State expected improvement in *observable terms* — e.g., "callers no longer coordinate update+reward" or "retry invariant has integration coverage" — not an invented architecture score.

## Candidate format

```text
Candidate: <domain name>
Evidence: <path:line and exact collaboration/policy exposed>
Current cost: <specific navigation/change/test difficulty>
Counterargument: <why the split might still be right>
Possible contract: <few entrypoints and what they promise>
Guarantee at risk: <invariant and its current test status>
Migration: <one safe first slice>
Recommendation: Change | Investigate | Keep
```
