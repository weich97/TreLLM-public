# B1 — LLM 决策 horizon 稳健性(可复现直连板)

_完成 2026-06-20。问题:E0→E1 的 τ_b 坍塌是否只是 12 步 Sharpe 估计噪声?_

## 板子与协议
- **可复现 9-agent 直连板** = deepseek-v4-pro(直连)+ glm-5(直连)+ 7 经典基线。
  - 注:12-agent 板在 N=2 用的是 **routed** `poe:glm-5`(`analyze_deepseek_compression.py:57`);本臂刻意用**直连** glm:glm-5,故 12 步基线 = **0.44**,不是 routed 板的 **0.21**(不同板,见下"边界")。
- high_vol,N=2(SYN,ALT),E0_ideal vs E1_default_stress,10 seeds(101–110)。
- horizons {12,30,60,120} 决策步;每 horizon 各模型 2 levels×10 seeds = 20 trajectory。
- deepseek 前 12 步复用主矩阵缓存;glm 直连无 N=2 基线,按 12→30→60→120 顺序跑(前序 horizon 缓存供后续复用),12 步重算入板自洽。
- 数据:`{ds,glm}_h{12,30,60,120}/execution_sensitivity_runs.csv`。

## 结果:E0→E1 Kendall τ_b(9-agent)

| 决策步 | 12 | 30 | 60 | 120 |
|---|---|---|---|---|
| **9-agent 直连板** | **0.44** | 0.83 | **0.39** | 0.89 |
| 确定性 7 经典(参照) | 0.81 | 0.905 (h24) | 0.714 | 0.905 |

## 结论
- **曲线非单调**(0.44→0.83→0.39→0.89),与确定性板的非单调形状一致(60 步均回落)。
- **不是 12 步假象**:60 步的 τ_b=0.39 ≤ 12 步的 0.44 —— 把 horizon 拉到 5× 后重排**不降反增**,无法用"短 horizon Sharpe 估计噪声"打发。
- LLM 让每个 horizon 都比纯经典板更不稳(0.44<0.81 @12;0.39<0.714 @60)→ 重排是 LLM 驱动且跨 horizon。
- 仅在最长 120 步显著回稳(0.89),符合"步数足够多后 Sharpe 估计收敛"的预期;但 **realistic 评测常用的短-中 horizon 区间内重排持续存在**。

## 边界
- 本臂是**可复现直连板**(12 步=0.44),非 routed 12-agent 板(12 步=0.21)。routed 板坍塌更深,是因为 3 个 Poe contender 分数挤在一起;其长 horizon 行为未跑。
- 因此结论严格成立于直连板。routed 板的 horizon 复现留作未来工作。
