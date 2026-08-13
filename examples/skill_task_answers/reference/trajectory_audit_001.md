# Trajectory Audit

Run `tradearena hash-run <trajectory.json>` and `tradearena replay
<trajectory.json> --case <case> --step <step> --json` to report the trajectory
hash and replay the inspected step.

Compare raw and approved decisions. Any difference is a risk edit diff, such as
clipping, blocked intent, or approval changes.

Check both the risk report and execution report. Flag rejected orders, partial
fill or partial filled orders, delayed execution, and latency.

Claim boundary: this supports an engineering claim about traceability and maybe
a benchmark claim under the stated scenario, not a scientific claim about model
profitability.
