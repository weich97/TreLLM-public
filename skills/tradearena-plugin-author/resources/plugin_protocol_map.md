# Plugin Protocol Map

| Plugin type | Boundary |
| --- | --- |
| data | stream market snapshots |
| analyst | produce signals |
| strategy | convert signals to decisions |
| risk | approve, monitor, and attribute risk |
| execution | convert approved decisions to orders |
| simulator | convert orders to fills |
| memory | store and retrieve events |
| evaluator | compute metrics from trajectories |

Do not put orchestration logic inside plugins.
