from pathlib import Path

from tradearena.agents import MacroNewsAnalyst
from tradearena.core.domain import PortfolioState
from tradearena.data import CsvMarketDataProvider


def test_csv_market_provider_reads_common_weekly_snapshots(tmp_path: Path):
    for symbol in ("GSPC", "BTC-USD"):
        path = tmp_path / f"{symbol}_Daily_2021_2026.csv"
        path.write_text(
            "\n".join(
                [
                    "Date,Open,High,Low,Close,Volume",
                    "2021-05-03,100,101,99,100.5,1000",
                    "2021-05-04,100.5,102,100,101,1100",
                    "2021-05-05,101,103,100,102,1200",
                    "2021-05-06,102,103,101,102.5,1300",
                    "2021-05-07,102.5,104,102,103,1400",
                    "2021-05-10,103,105,102,104,1500",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    provider = CsvMarketDataProvider(tmp_path, ("GSPC", "BTC-USD"), frequency="weekly")
    snapshots = provider.stream()

    assert len(snapshots) == 2
    assert set(snapshots[0].bars) == {"GSPC", "BTC-USD"}
    assert snapshots[0].bars["GSPC"].close == 100.5
    assert snapshots[1].bars["BTC-USD"].close == 104


def test_csv_market_provider_reads_hourly_snapshots(tmp_path: Path):
    for symbol in ("AAPL", "MSFT"):
        path = tmp_path / f"{symbol}_Hourly_1h.csv"
        path.write_text(
            "\n".join(
                [
                    "Date,Open,High,Low,Close,Volume",
                    "2026-05-01T13:30:00,100,101,99,100.5,1000",
                    "2026-05-01T14:30:00,100.5,102,100,101,1100",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    provider = CsvMarketDataProvider(tmp_path, ("AAPL", "MSFT"), frequency="hourly")
    snapshots = provider.stream()

    assert len(snapshots) == 2
    assert snapshots[0].timestamp.hour == 13
    assert snapshots[1].bars["AAPL"].close == 101


def test_csv_market_provider_window_offset_selects_rolling_slice(tmp_path: Path):
    for symbol in ("GSPC", "BTC-USD"):
        rows = ["Date,Open,High,Low,Close,Volume"]
        for day in range(1, 8):
            rows.append(f"2026-01-0{day},100,101,99,{100 + day},1000")
        (tmp_path / f"{symbol}_Daily_2021_2026.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    latest = CsvMarketDataProvider(tmp_path, ("GSPC", "BTC-USD"), max_periods=3).stream()
    shifted = CsvMarketDataProvider(tmp_path, ("GSPC", "BTC-USD"), max_periods=3, window_offset=2).stream()

    assert [snapshot.bars["GSPC"].close for snapshot in latest] == [105, 106, 107]
    assert [snapshot.bars["GSPC"].close for snapshot in shifted] == [103, 104, 105]


def test_csv_market_provider_loads_optional_research_sidecars(tmp_path: Path):
    (tmp_path / "SYN_Daily_2021_2026.csv").write_text(
        "\n".join(
            [
                "Date,Open,High,Low,Close,Volume",
                "2026-01-02,100,102,99,101,1000",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "news.csv").write_text(
        "Date,Symbol,Source,Title,Body,Sentiment\n"
        "2026-01-02,SYN,test-wire,positive order flow,body,0.4\n",
        encoding="utf-8",
    )
    (tmp_path / "macro.csv").write_text(
        "Date,Name,Value,Unit\n"
        "2026-01-02,synthetic_growth,0.5,index\n",
        encoding="utf-8",
    )
    (tmp_path / "filings.csv").write_text(
        "Date,Symbol,Source,Form,Title,Body,Sentiment,Accession\n"
        "2026-01-02,SYN,test-sec,8-K,contract update,body,0.3,0001\n",
        encoding="utf-8",
    )
    (tmp_path / "alternative_data.csv").write_text(
        "Date,Symbol,Name,Value,Unit,Source\n"
        "2026-01-02,SYN,web_traffic_zscore,0.2,z,test-alt\n",
        encoding="utf-8",
    )

    provider = CsvMarketDataProvider(tmp_path, ("SYN",), include_price_proxy_news=False, include_proxy_macro=False)
    snapshot = provider.stream()[0]

    assert len(snapshot.news) == 1
    assert len(snapshot.macro) == 1
    assert len(snapshot.filings) == 1
    assert snapshot.alt_data["SYN"]["web_traffic_zscore"]["value"] == 0.2

    signal = MacroNewsAnalyst().analyze(snapshot, PortfolioState(cash=100000.0), memory=None)[0]

    assert signal.score > 0.0
    assert "filings=" in signal.rationale
    assert signal.metadata["feature"] == "macro_news_filings_alt_blend"
