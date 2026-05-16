import polars as pl
import polars.selectors as cs
import glob
from datetime import datetime
import logging
from functools import reduce

logger = logging.getLogger(__name__)


def gen_stocks_list(
    files_list: list[str], start_date: datetime, end_date: datetime
) -> pl.LazyFrame:
    """
    Generate Stocks List from BhavCopy
    """

    res = (
        pl.scan_csv(
            files_list, with_column_names=lambda cols: [col.strip() for col in cols]
        )
        .select("SYMBOL", "SERIES", "DATE1")
        .rename({"SYMBOL": "symbol", "SERIES": "series", "DATE1": "date"})
        .with_columns(
            pl.col("date").str.strptime(pl.Date, format="%d-%b-%Y").alias("date"),
            pl.col("series").str.strip_chars().alias("series"),
            pl.col("symbol").str.strip_chars().alias("symbol"),
        )
        .filter(pl.col("series") == "EQ")
        .filter(pl.col("date").is_between(start_date, end_date, closed="both"))
        .group_by("date")
        .agg(pl.col("symbol").len().alias("symbol_count"), pl.col("symbol"))
        .sort("date")
    )

    return res


def gen_scanner_list(data: pl.DataFrame | pl.LazyFrame) -> pl.LazyFrame:
    """ """

    class IndicatorConfig:
        LOOKBACK_RETURN_PCT = {1: "1D", 5: "1W", 21: "1M", 63: "3M", 126: "6M"}

        LOOKBACK_DAYS_TO_MIN_RETURN_PCT = {
            1: 4.99,  # close today ≥ close 1 day ago * 1.05
            5: 7.5,  # close today ≥ close 5 day ago * 1.075
            21: 10,  # close today ≥ close 21 days ago * 1.10
            63: 20,  # close today ≥ close 63 days ago * 1.22
            126: 60,  # close today ≥ close 126 days ago * 1.60
        }

        SMA_DAYS = [50, 200]
        EMA_DAYS = [9, 21]
        VOL_SMA_DAYS = [20, 50]
        CLEAN_SCORE_DAYS = [20, 50]
        ADR_DAYS = [20]

    pct_gain_expr = reduce(
        lambda a, b: a | b,
        [
            pl.col(f"pct_gain_prev_{days}") >= threshold
            for days, threshold in IndicatorConfig.LOOKBACK_DAYS_TO_MIN_RETURN_PCT.items()
        ],
    )

    res = (
        data.lazy()
        .with_columns(pl.col("timestamp").cast(pl.Date))
        .with_columns(
            # Shift Columns
            [
                pl.col(col)
                .shift(i)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .alias(f"{col}_prev_{i}")
                for col in ["close", "timestamp"]
                for i in IndicatorConfig.LOOKBACK_RETURN_PCT.keys()
            ]
            # Day Range
            + [(pl.col("high") / pl.col("low")).round(4).alias("day_range")]
            # Close EMA Experssion
            + [
                pl.col("close")
                .ewm_mean(alpha=2 / (n + 1))
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"close_ema_{n}")
                for n in [9, 21]
            ]
            # Close SMA expression
            + [
                pl.col("close")
                .rolling_mean(window_size=n)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"close_sma_{n}")
                for n in [50, 200]
            ]
        )
        .with_columns(
            # Gains Calculation
            [
                (
                    (pl.col("close") - pl.col(f"close_prev_{i}"))
                    * 100
                    / pl.col(f"close_prev_{i}")
                )
                .round(4)
                .alias(f"pct_gain_prev_{i}")
                for i in IndicatorConfig.LOOKBACK_RETURN_PCT.keys()
            ]
            # ADR calculation
            + [
                (
                    (
                        pl.col("day_range")
                        .rolling_mean(window_size=i)
                        .over(
                            partition_by="symbol",
                            order_by="timestamp",
                            descending=False,
                        )
                        - 1
                    )
                    * 100
                )
                .round(2)
                .alias(f"adr_pct_{i}")
                for i in IndicatorConfig.ADR_DAYS
            ]
        )
        .with_columns(
            pl.when(pl.any_horizontal(pl.col("*").is_null()))
            .then(False)
            .otherwise(True)
            .alias("all_data_flag")
        )
        .with_columns(
            pl.when(
                (pl.col("all_data_flag") == True)
                & (pl.col("adr_pct_20") >= 3.5)
                & (pct_gain_expr)
            )
            .then(True)
            .otherwise(False)
            .alias("eligible")
        )
        .with_columns(
            pl.col("eligible")
            .cast(pl.Int8)
            .rolling_max(window_size=63)
            .over(
                partition_by="symbol",
                order_by="timestamp",
                descending=False,
            )
            .cast(pl.Boolean)
            .alias("eligible_past_63d")
        )
        .with_columns(
            (
                pl.col("eligible_past_63d")
                & (pl.col("adr_pct_20") >= 3.5)
                & (
                    (pl.col("close_ema_9") >= pl.col("close_sma_50"))
                    | (pl.col("close_ema_21") >= pl.col("close_sma_50"))
                )
                & (pl.col("close_sma_50") >= pl.col("close_sma_200"))
            ).alias("scanner_eligible")
        )
        .filter(pl.col("scanner_eligible"))
        .select("timestamp", "symbol")
    )

    return res
