import polars as pl
import polars.selectors as cs
import numpy as np


def basic_features(data: pl.DataFrame | pl.LazyFrame) -> pl.LazyFrame:
    """
    Calculate the basic features
    """

    res = (
        data.lazy()
        .with_columns(pl.col("timestamp").cast(pl.Date()))
        .with_columns(
            # Close & Volume SMA expression
            [
                pl.col(col)
                .rolling_mean(window_size=n)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"{col}_sma_{n}")
                for n in [50, 200]
                for col in ["close", "volume"]
            ]
            # Close EMA Experssion
            + [
                pl.col("close")
                .ewm_mean(alpha=2 / (n + 1))
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"close_ema_{n}")
                for n in [9, 21]
            ]
            # Returns
            + [
                ((pl.col("close") / pl.col("close").shift(i)) - 1)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(4)
                .alias(f"return_{i}_days")
                for i in [1, 5, 21, 63, 126]
            ]
            # Log Returns
            + [
                (pl.col("close").log() - pl.col("close").log().shift(i))
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(4)
                .alias(f"log_return_{i}_days")
                for i in [1, 5, 21, 63, 126]
            ]
            # 52 week high
            + [
                pl.col("close")
                .rolling_max(window_size=252)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .alias("high_52W")
            ]
            # 52 week low
            + [
                pl.col("close")
                .rolling_min(window_size=252)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .alias("low_52W")
            ]
            # Prev Close for ATR Calculation
            + [
                pl.col("close")
                .shift(1)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .alias("_close_prev_1")
            ]
            # Candle Red or Green
            + [
                pl.when(pl.col("close") > pl.col("open"))
                .then(True)
                .otherwise(False)
                .alias("is_green_candle")
            ]
            # Range of Candle
            + [(pl.col("high") - pl.col("low")).round(2).alias("range")]
            # Body of Canlde
            + [(pl.col("open") - pl.col("close")).abs().round(2).alias("body")]
            # Upper Wick
            + [
                (pl.col("high") - pl.max_horizontal("open", "close"))
                .round(2)
                .alias("upper_wick")
            ]
            # Lower Wick
            + [
                (pl.min_horizontal("open", "close") - pl.col("low"))
                .round(2)
                .alias("lower_wick")
            ]
            # Get Day of the week
            + [pl.col("timestamp").dt.weekday().alias("weekday")]
        )
        .with_columns(
            # Percentage off 52 week high
            [
                ((pl.col("close") / pl.col("high_52W")) - 1)
                .round(4)
                .alias("pct_from_high_52W")
            ]
            # True Range Calculation for ATR
            + [
                pl.max_horizontal(
                    pl.col("high") - pl.col("low"),
                    (pl.col("high") - pl.col("_close_prev_1")).abs(),
                    (pl.col("low") - pl.col("_close_prev_1")).abs(),
                ).alias("_true_range")
            ]
            # Relative Volume Pct
            + [
                ((pl.col("volume") / pl.col(f"volume_sma_{n}")) - 1)
                .round(4)
                .alias(f"rvol_{n}")
                for n in [50, 200]
            ]
            # Calculate Standard Deviation based on Close, EMA9 and EMA21
            + [
                pl.concat_list("close_ema_9", "close_ema_21", "close")
                .list.std(ddof=0)
                .round(4)
                .alias("std_9_21")
            ]
            # Calculate Standard Deviation based on Close, EMA9, EMA21 and SMA50
            + [
                pl.concat_list("close_ema_9", "close_ema_21", "close", "close_sma_50")
                .list.std(ddof=0)
                .round(4)
                .alias("std_9_21_50")
            ]
        )
        .with_columns(
            # Calculate ATR using True Range
            [
                pl.col("_true_range")
                .ewm_mean(alpha=2 / (n + 1))
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"atr_{n}")
                for n in [20]
            ]
        )
        .with_columns(
            # Normalize by ATR20
            [
                (pl.col(col) / pl.col("atr_20")).round(4).alias(col)
                for col in [
                    "open",
                    "high",
                    "low",
                    "close",
                    "close_sma_50",
                    "close_sma_200",
                    "close_ema_9",
                    "close_ema_21",
                    "high_52W",
                    "low_52W",
                    "std_9_21",
                    "std_9_21_50",
                    "range",
                    "body",
                    "upper_wick",
                    "lower_wick",
                ]
            ]
        )
        .drop(cs.starts_with("_"), cs.starts_with("volume"))
    )

    return res


def moving_average_features(data: pl.DataFrame | pl.LazyFrame) -> pl.LazyFrame:
    """
    Calculate Different Features Based on Moving Average
    """

    res = data.lazy().with_columns(
        # Calculate the smooth dispersion score based on the normalzied standard deviation
        [
            pl.col(col)
            .rolling_mean(window_size=n)
            .over(partition_by="symbol", order_by="timestamp", descending=False)
            .round(4)
            .alias(f"{col}_dispersion_{n}")
            for n in [5, 10, 15, 20]
            for col in ["std_9_21", "std_9_21_50"]
        ]
        # Calculate Slop of the Moving Averages
        + [
            ((pl.col(col) - pl.col(col).shift(i)) / i)
            .over(partition_by="symbol", order_by="timestamp", descending=False)
            .round(4)
            .alias(f"{col}_slope_{i}")
            for col in ["close_ema_9", "close_ema_21", "close_sma_50"]
            for i in [3, 5, 10]
        ]
        # Distance of Close and Low to Moving Averages
        + [
            (((pl.col(m_col) / pl.col(c_col)) - 1).round(4)).alias(
                f"{m_col}_dist_from_{c_col}"
            )
            for m_col in ["close", "low"]
            for c_col in ["close_ema_9", "close_ema_21", "close_sma_50"]
        ]
        # Distance Between SMA 50 and SMA 200
        + [
            ((pl.col(col) / pl.col("close_sma_200")) - 1)
            .round(4)
            .alias(f"{col}_dist_from_close_sma_200")
            for col in ["close", "close_sma_50"]
        ]
        # SMA50 GTE SMA200
        + [
            pl.when(pl.col("close_sma_50") >= pl.col("close_sma_200"))
            .then(True)
            .otherwise(False)
            .alias("is_sma_50_gte_sma_200")
        ]
    )

    return res


def rolling_slope(s: pl.Series) -> float:
    arr = s.to_numpy()

    if len(arr) < 2 or np.isnan(arr).any():
        return np.nan

    x = np.arange(len(arr), dtype=np.float64)

    x_mean = x.mean()
    y_mean = arr.mean()

    cov = ((x - x_mean) * (arr - y_mean)).sum()
    var = ((x - x_mean) ** 2).sum()

    return cov / var if var > 0 else np.nan


def rolling_r2(s: pl.Series) -> float:
    arr = s.to_numpy()

    if len(arr) < 2 or np.isnan(arr).any():
        return np.nan

    x = np.arange(len(arr), dtype=np.float64)

    x_mean = x.mean()
    y_mean = arr.mean()

    cov = ((x - x_mean) * (arr - y_mean)).sum()

    var_x = ((x - x_mean) ** 2).sum()
    var_y = ((arr - y_mean) ** 2).sum()

    if var_x <= 0 or var_y <= 0:
        return np.nan

    return (cov**2) / (var_x * var_y)


def gen_features(data: pl.DataFrame | pl.LazyFrame) -> pl.LazyFrame:
    """
    Gen Features
    """

    res = (
        data.lazy()
        .with_columns(pl.col("timestamp").cast(pl.Date()))
        .with_columns(
            # Prev Price Columns
            [
                pl.col(col)
                .shift(1)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .alias(f"prev_{col}")
                for col in ["open", "high", "low", "close"]
            ]
            # Close SMA expression
            + [
                pl.col(col)
                .rolling_mean(window_size=n)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"{col}_sma_{n}")
                for n in [50, 200]
                for col in ["close"]
            ]
            # Close EMA Experssion
            + [
                pl.col("close")
                .ewm_mean(alpha=2 / (n + 1))
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"close_ema_{n}")
                for n in [9, 21]
            ]
            # 52 week high
            + [
                pl.col("close")
                .rolling_max(window_size=252)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .alias("high_52W")
            ]
            # 52 week low
            + [
                pl.col("close")
                .rolling_min(window_size=252)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .alias("low_52W")
            ]
            # Candle Red or Green
            + [
                pl.when(pl.col("close") > pl.col("open"))
                .then(True)
                .otherwise(False)
                .alias("is_green_candle")
            ]
            # Range of Candle
            + [(pl.col("high") - pl.col("low")).round(2).alias("range")]
            # Body of Canlde
            + [(pl.col("open") - pl.col("close")).abs().round(2).alias("body")]
            # Upper Wick
            + [
                (pl.col("high") - pl.max_horizontal("open", "close"))
                .round(2)
                .alias("upper_wick")
            ]
            # Lower Wick
            + [
                (pl.min_horizontal("open", "close") - pl.col("low"))
                .round(2)
                .alias("lower_wick")
            ]
            # Day Range
            + [(pl.col("high") / pl.col("low")).round(4).alias("day_range")]
            # Close Position in Range
            + [
                ((pl.col("close") - pl.col("low")) / (pl.col("high") - pl.col("low")))
                .round(4)
                .alias("close_position_in_range")
            ]
            # ROC over Short Time Period
            + [
                (pl.col("close") / pl.col("close").shift(n) - 1)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(4)
                .alias(f"roc_{n}")
                for n in [3, 5, 10]
            ]
        )
        .with_columns(
            # Log Returns Calculated for Changes
            [
                (pl.col(col) / pl.col(f"prev_{col}"))
                .log()
                .round(4)
                .alias(f"log_return_{col}")
                for col in ["open", "high", "low", "close"]
            ]
            # Percentage off 52 week high
            + [
                ((pl.col("close") / pl.col("high_52W")) - 1)
                .clip(upper_bound=1)
                .round(4)
                .alias("dst_from_high_52W")
            ]
            # True Range Calculation for ATR
            + [
                pl.max_horizontal(
                    pl.col("high") - pl.col("low"),
                    (pl.col("high") - pl.col("prev_close")).abs(),
                    (pl.col("low") - pl.col("prev_close")).abs(),
                ).alias("true_range")
            ]
            # Calculate Standard Deviation based on Close, EMA9 and EMA21
            + [
                pl.concat_list("close_ema_9", "close_ema_21", "close")
                .list.std(ddof=0)
                .round(4)
                .alias("std_9_21")
            ]
            # Calculate Standard Deviation based on Close, EMA9, EMA21 and SMA50
            + [
                pl.concat_list("close_ema_9", "close_ema_21", "close", "close_sma_50")
                .list.std(ddof=0)
                .round(4)
                .alias("std_9_21_50")
            ]
            # Body, Upper Wick and Lower Wick Pct to Range
            + [
                (pl.col(col) / pl.col("range"))
                .round(4)
                .clip(upper_bound=1, lower_bound=0)
                .alias(f"{col}_to_range_pct")
                for col in ["body", "upper_wick", "lower_wick"]
            ]
            # Distance Between SMA 50 and SMA 200
            + [
                ((pl.col(col) / pl.col("close_sma_200")) - 1)
                .round(4)
                .alias(f"{col}_dist_from_close_sma_200")
                for col in ["close", "close_sma_50"]
            ]
            # SMA50 GTE SMA200
            + [
                pl.when(pl.col("close_sma_50") >= pl.col("close_sma_200"))
                .then(True)
                .otherwise(False)
                .alias("is_sma_50_gte_sma_200")
            ]
            # Distance of Close and Low to Moving Averages
            + [
                (((pl.col(m_col) / pl.col(c_col)) - 1).round(4)).alias(
                    f"{m_col}_dist_from_{c_col}"
                )
                for m_col in ["close", "low"]
                for c_col in ["close_ema_9", "close_ema_21", "close_sma_50"]
            ]
            # Calculate ADR 20
            + [
                pl.col("day_range")
                .rolling_mean(window_size=n)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(4)
                .alias(f"adr_{n}")
                for n in [20]
            ]
            # MA Alignment fot Bullish
            + [
                pl.when(
                    (pl.col("close_ema_9") >= pl.col("close_sma_50"))
                    | (pl.col("close_ema_21") >= pl.col("close_sma_50"))
                )
                .then(True)
                .otherwise(False)
                .alias("ma_aligned_bullish")
            ]
        )
        .with_columns(
            # Calculate ATR using True Range
            [
                pl.col("true_range")
                .ewm_mean(alpha=2 / (n + 1))
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(4)
                .alias(f"atr_{n}")
                for n in [14, 20, 50]
            ]
            # Calculate the smooth dispersion score based on the normalzied standard deviation
            + [
                pl.col(col)
                .rolling_mean(window_size=n)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(4)
                .alias(f"{col}_dispersion_{n}")
                for n in [5, 10, 15, 20]
                for col in ["std_9_21", "std_9_21_50"]
            ]
        )
        .with_columns(
            # ATR ratio 14 by 50
            [(pl.col("atr_14") / pl.col("atr_50")).round(4).alias("atr_ratio_14_50")]
            # ATR 20 Pct
            + [(pl.col("atr_20") / pl.col("close")).round(4).alias("atr_pct_20")]
            # ADR 20 Pct
            + [(pl.col("adr_20") / pl.col("close")).round(4).alias("adr_pct_20")]
        )
        # .with_columns(
        #     [
        #         pl.col(col)
        #         .log()
        #         .rolling_map(rolling_slope, window_size=n)
        #         .over(
        #             partition_by="symbol",
        #             order_by="timestamp",
        #             descending=False,
        #         )
        #         .round(4)
        #         .alias(f"{col}_regression_slope_{n}")
        #         for n in [3, 5, 10]
        #         for col in ["close", "close_ema_21", "close_sma_50"]
        #     ]
        #     + [
        #         pl.col(col)
        #         .rolling_map(rolling_r2, window_size=n)
        #         .over(
        #             partition_by="symbol",
        #             order_by="timestamp",
        #             descending=False,
        #         )
        #         .round(4)
        #         .alias(f"{col}_regression_r2_{n}")
        #         for n in [3, 5, 10]
        #         for col in ["close", "close_ema_21", "close_sma_50"]
        #     ]
        # )
        .select(
            [
                "symbol",
                "timestamp",
                "is_green_candle",
                "close_position_in_range",
                "roc_3",
                "roc_5",
                "roc_10",
                "log_return_open",
                "log_return_high",
                "log_return_low",
                "log_return_close",
                "dst_from_high_52W",
                "std_9_21",
                "std_9_21_50",
                "body_to_range_pct",
                "upper_wick_to_range_pct",
                "lower_wick_to_range_pct",
                "close_dist_from_close_sma_200",
                "close_sma_50_dist_from_close_sma_200",
                "is_sma_50_gte_sma_200",
                "close_dist_from_close_ema_9",
                "close_dist_from_close_ema_21",
                "close_dist_from_close_sma_50",
                "low_dist_from_close_ema_9",
                "low_dist_from_close_ema_21",
                "low_dist_from_close_sma_50",
                "ma_aligned_bullish",
                "std_9_21_dispersion_5",
                "std_9_21_50_dispersion_5",
                "std_9_21_dispersion_10",
                "std_9_21_50_dispersion_10",
                "std_9_21_dispersion_15",
                "std_9_21_50_dispersion_15",
                "std_9_21_dispersion_20",
                "std_9_21_50_dispersion_20",
                "atr_ratio_14_50",
                "atr_pct_20",
                "adr_pct_20",
                # "close_regression_slope_3",
                # "close_ema_21_regression_slope_3",
                # "close_sma_50_regression_slope_3",
                # "close_regression_slope_5",
                # "close_ema_21_regression_slope_5",
                # "close_sma_50_regression_slope_5",
                # "close_regression_slope_10",
                # "close_ema_21_regression_slope_10",
                # "close_sma_50_regression_slope_10",
                # "close_regression_r2_3",
                # "close_ema_21_regression_r2_3",
                # "close_sma_50_regression_r2_3",
                # "close_regression_r2_5",
                # "close_ema_21_regression_r2_5",
                # "close_sma_50_regression_r2_5",
                # "close_regression_r2_10",
                # "close_ema_21_regression_r2_10",
                # "close_sma_50_regression_r2_10",
            ]
        )
    )

    return res


def gen_target(data: pl.DataFrame | pl.LazyFrame) -> pl.LazyFrame:
    """ """

    res = (
        data.lazy()
        .with_columns(pl.col("timestamp").cast(pl.Date()))
        .with_columns(
            [
                pl.col("close")
                .shift(-i)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .alias(f"close_next_{i}")
                for i in [1, 2, 3]
            ]
            + [
                pl.col("low")
                .shift(-i)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .alias(f"low_next_{i}")
                for i in [1, 2, 3]
            ]
            + [
                pl.col(col)
                .shift(1)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .alias(f"{col}_prev_1")
                for col in ["close", "low"]
            ]
        )
        .with_columns(
            pl.min_horizontal("low_next_1", "low_next_2", "low_next_3").alias(
                "min_low_next"
            ),
            pl.min_horizontal("close_next_1", "close_next_2", "close_next_3").alias(
                "min_close_next"
            ),
            pl.min_horizontal("low_prev_1", "low").alias("min_low"),
        )
        .with_columns(
            pl.when(
                (pl.col("min_low_next") > pl.col("min_low"))
                & (pl.col("min_close_next") > pl.col("close"))
            )
            .then(True)
            .otherwise(False)
            .alias("target")
        )
        .select("symbol", "timestamp", "target")
    )

    return res
