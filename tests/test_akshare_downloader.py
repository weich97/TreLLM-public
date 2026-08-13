from scripts.download_akshare_ashare_daily import normalize_akshare_rows, normalize_ashare_symbol


def test_normalize_ashare_symbol_infers_exchange_suffixes():
    assert normalize_ashare_symbol("600519")["tradearena_symbol"] == "600519.SS"
    assert normalize_ashare_symbol("300750")["tradearena_symbol"] == "300750.SZ"
    assert normalize_ashare_symbol("sh600000")["tradearena_symbol"] == "600000.SS"
    assert normalize_ashare_symbol("000001.SZ")["akshare_symbol"] == "000001"


def test_normalize_akshare_rows_maps_chinese_columns_to_standard_ohlcv():
    rows = normalize_akshare_rows(
        [
            {"日期": "2024-01-03", "开盘": "10.0", "最高": "11.0", "最低": "9.8", "收盘": "10.5", "成交量": "123"},
            {"日期": "2024-01-02", "开盘": "9.5", "最高": "10.2", "最低": "9.4", "收盘": "10.0", "成交量": "100"},
        ],
        "600519.SS",
        volume_multiplier=100.0,
    )

    assert [row["Date"] for row in rows] == ["2024-01-02", "2024-01-03"]
    assert rows[0]["Open"] == 9.5
    assert rows[0]["High"] == 10.2
    assert rows[0]["Low"] == 9.4
    assert rows[0]["Close"] == 10.0
    assert rows[0]["Volume"] == 10000.0
