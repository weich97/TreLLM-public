from __future__ import annotations

from dataclasses import dataclass, field, replace

from tradearena.agents import MaxPositionRiskManager
from tradearena.core.domain import Decision, MarketSnapshot, PortfolioState, RiskCheck, RiskPhase, RiskReport, Side


@dataclass
class SectorConcentrationGuard(MaxPositionRiskManager):
    """Curated example risk plugin that caps aggregate target weight by sector."""

    sector_map: dict[str, str] = field(default_factory=dict)
    max_sector_weight: float = 0.50
    max_abs_weight: float = 1.0
    min_confidence: float = 0.0
    name: str = "sector-concentration-guard"

    def approve(
        self,
        snapshot: MarketSnapshot,
        decisions: list[Decision],
        portfolio: PortfolioState,
        memory: object,
    ) -> list[Decision]:
        approved = super().approve(snapshot, decisions, portfolio, memory)
        scaled, clipped_count, check = self._apply_sector_cap(approved)
        if check is None:
            return scaled

        base_report = self.last_report
        checks = tuple(base_report.checks) if base_report is not None else ()
        violations = tuple(base_report.violations) if base_report is not None else ()
        self.last_report = RiskReport(
            timestamp=snapshot.timestamp,
            checks=(*checks, check),
            approved_count=len(scaled),
            blocked_count=base_report.blocked_count if base_report is not None else 0,
            clipped_count=(base_report.clipped_count if base_report is not None else 0) + clipped_count,
            phase=RiskPhase.PRE_TRADE,
            budget=self.budget(),
            violations=violations,
        )
        return scaled

    def _apply_sector_cap(self, decisions: list[Decision]) -> tuple[list[Decision], int, RiskCheck | None]:
        sector_abs_weights: dict[str, float] = {}
        for decision in decisions:
            sector = self._sector(decision.symbol)
            sector_abs_weights[sector] = sector_abs_weights.get(sector, 0.0) + abs(decision.target_weight)

        sector_scales = {
            sector: min(1.0, self.max_sector_weight / weight)
            for sector, weight in sector_abs_weights.items()
            if weight > self.max_sector_weight > 0
        }
        if not sector_scales:
            return decisions, 0, None

        scaled: list[Decision] = []
        clipped_count = 0
        for decision in decisions:
            sector = self._sector(decision.symbol)
            scale = sector_scales.get(sector, 1.0)
            target = decision.target_weight * scale
            metadata = {**decision.metadata, "sector": sector}
            if scale < 1.0:
                clipped_count += 1
                metadata["sector_concentration_scaled_by"] = scale
                metadata["sector_concentration_limit"] = self.max_sector_weight
            scaled.append(
                replace(
                    decision,
                    target_weight=target,
                    side=decision.side if abs(target) > 1e-12 else Side.HOLD,
                    metadata=metadata,
                )
            )
        check = RiskCheck(
            name="sector_concentration",
            passed=True,
            severity="warning",
            message=f"scaled {clipped_count} decisions to keep sector target weights <= {self.max_sector_weight:.3f}",
            metadata={"sector_scales": sector_scales, "max_sector_weight": self.max_sector_weight},
        )
        return scaled, clipped_count, check

    def _sector(self, symbol: str) -> str:
        return self.sector_map.get(symbol, "unclassified")


__all__ = ["SectorConcentrationGuard"]
