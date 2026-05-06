import polars as pl
import polars.selectors as cs


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
