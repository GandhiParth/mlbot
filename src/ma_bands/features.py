import numpy as np
import polars as pl
import polars.selectors as cs

# ---------- core: indicators + state machine ----------


def add_indicators(
    data: pl.DataFrame | pl.LazyFrame,
    ma_window_size: int,
    use_ema: bool,
    atr_window_size: int,
    atr_multi: float = 0.5,
) -> pl.DataFrame:
    return (
        data.lazy()
        .with_columns(
            pl.col("timestamp").cast(pl.Date()),
            pl.col("close")
            .shift(1)
            .over(partition_by="symbol", order_by="timestamp", descending=False)
            .alias("_close_prev_1"),
        )
        .with_columns(
            [
                pl.max_horizontal(
                    pl.col("high") - pl.col("low"),
                    (pl.col("high") - pl.col("_close_prev_1")).abs(),
                    (pl.col("low") - pl.col("_close_prev_1")).abs(),
                ).alias("_true_range")
            ]
            # Close SMA Expression
            + [
                pl.col("close")
                .rolling_mean(window_size=ma_window_size)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"close_sma_{ma_window_size}")
            ]
            # Close EMA Experssion
            + [
                pl.col("close")
                .ewm_mean(alpha=2 / (ma_window_size + 1))
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"close_ema_{ma_window_size}")
            ]
        )
        .with_columns(
            # Calculate ATR using True Range
            [
                pl.col("_true_range")
                .ewm_mean(alpha=2 / (atr_window_size + 1))
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"atr_{atr_window_size}")
            ]
        )
        .with_columns(
            [
                (pl.col(col) + (atr_multi * pl.col(f"atr_{atr_window_size}"))).alias(
                    "upper_band"
                )
                for col in [
                    (
                        f"close_ema_{ma_window_size}"
                        if use_ema
                        else f"close_sma_{ma_window_size}"
                    )
                ]
            ]
            + [
                (pl.col(col) - (atr_multi * pl.col(f"atr_{atr_window_size}"))).alias(
                    "lower_band"
                )
                for col in [
                    (
                        f"close_ema_{ma_window_size}"
                        if use_ema
                        else f"close_sma_{ma_window_size}"
                    )
                ]
            ]
        )
        .with_columns(
            # +1 = above upper band, -1 = below lower band, 0 = inside band
            pl.when(pl.col("close") > pl.col("upper_band"))
            .then(1)
            .when(pl.col("close") < pl.col("lower_band"))
            .then(-1)
            .otherwise(0)
            .alias("pos")
        )
        .drop(cs.starts_with("_"), "open", "high", "low", "volume")
        .drop(
            [
                (
                    f"close_ema_{ma_window_size}"
                    if not use_ema
                    else f"close_sma_{ma_window_size}"
                )
            ]
        )
        .filter(pl.col("upper_band").is_not_null())
    )


def detect_events(data: pl.DataFrame | pl.LazyFrame) -> pl.LazyFrame:
    # An event = bar where price exits the band region (or jumps directly across it).
    # entry_side = the band side the price came from before this exit
    # bounce iff exit_side == entry_side

    # last_outside is forward filled and includes the current row when the curret row is non-zero
    # so an event where pos != 0, last_outside == pos, the current_pos has already overwritten it
    # last_outside: on an event row = wherfe we are going to
    # prev_outside: on an event row = where we came from

    # at event bar price has just updated last_outside, to compare where I am now against where I was,
    # we need the version of last_outside from before this update that is prev_outside

    res = (
        data.lazy()
        .with_columns(
            # where the price was on the previous bar
            pl.col("pos")
            .shift(1)
            .over(partition_by="symbol", order_by="timestamp", descending=False)
            .alias("prev_pos"),
            # What side the price was on the last time it was outside
            pl.when(pl.col("pos") != 0)
            .then(pl.col("pos"))
            .otherwise(None)
            .forward_fill()
            .over(partition_by="symbol", order_by="timestamp", descending=False)
            .alias("last_outside"),
        )
        .with_columns(
            # previous row's last outide
            pl.col("last_outside")
            .shift(1)
            .over(partition_by="symbol", order_by="timestamp", descending=False)
            .alias("prev_outside")
        )
        .with_columns(
            (
                (pl.col("pos") != 0)  # we are currently outside the band
                & (
                    pl.col("prev_pos") != pl.col("pos")
                )  # something just changed, of == we were already outside nothing to change
                & pl.col(
                    "prev_outside"
                ).is_not_null()  # we have history we know which side we came from
            ).alias("is_event"),
        )
        .filter(pl.col("is_event"))
        .with_columns(
            pl.col("prev_outside").alias(
                "regime"
            ),  # +1 support test, -1 resistance test #which side we were on before
            (pl.col("prev_outside") == pl.col("pos")).alias(
                "is_bounce"
            ),  # did we leave on the same side,
        )
    )

    return res


def bounce_stats(events: pl.DataFrame) -> dict:
    s = events.filter(pl.col("regime") == 1)
    r = events.filter(pl.col("regime") == -1)
    sb, sp = s.filter(pl.col("is_bounce")).height, s.filter(~pl.col("is_bounce")).height
    rb, rp = r.filter(pl.col("is_bounce")).height, r.filter(~pl.col("is_bounce")).height
    total = sb + sp + rb + rp
    return {
        "support_bounces": sb,
        "support_pens": sp,
        "support_pct": sb / max(sb + sp, 1),
        "resist_bounces": rb,
        "resist_pens": rp,
        "resist_pct": rb / max(rb + rp, 1),
        "combined_pct": (sb + rb) / max(total, 1),
        "total_events": total,
    }


# ---------- sweep across MA periods ----------


def sweep_ma_periods(
    df: pl.DataFrame,
    periods: range | list[int] = range(24, 201),
    atr_period: int = 200,
    atr_mult: float = 0.5,
) -> pl.DataFrame:
    rows = []
    for p in periods:
        events = detect_events(add_indicators(df, p, atr_period, atr_mult))
        rows.append({"ma_period": p, **bounce_stats(events)})
    return pl.DataFrame(rows)


# ---------- Monte Carlo permutation test ----------


def permute_ohlc(df: pl.DataFrame, seed: int) -> pl.DataFrame:
    """Bar permutation: shuffle close-to-close log returns while keeping
    intra-bar (open/high/low) offsets bound to their bar."""
    df = (
        df.sort("timestamp")
        .with_columns(log_close=pl.col("close").log())
        .with_columns(
            log_ret=pl.col("log_close").diff(),
            log_o_off=pl.col("open").log() - pl.col("log_close"),
            log_h_off=pl.col("high").log() - pl.col("log_close"),
            log_l_off=pl.col("low").log() - pl.col("log_close"),
        )
    )
    first, rest = df.head(1), df.slice(1)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(rest.height)
    rest = rest.with_columns(
        log_ret=pl.Series(rest["log_ret"].to_numpy()[perm]),
        log_o_off=pl.Series(rest["log_o_off"].to_numpy()[perm]),
        log_h_off=pl.Series(rest["log_h_off"].to_numpy()[perm]),
        log_l_off=pl.Series(rest["log_l_off"].to_numpy()[perm]),
    )
    base = float(first["log_close"][0])
    return (
        pl.concat([first, rest])
        .with_columns(log_close=pl.col("log_ret").fill_null(0).cum_sum() + base)
        .with_columns(
            close=pl.col("log_close").exp(),
            open=(pl.col("log_close") + pl.col("log_o_off")).exp(),
            high=(pl.col("log_close") + pl.col("log_h_off")).exp(),
            low=(pl.col("log_close") + pl.col("log_l_off")).exp(),
        )
        .select("symbol", "timestamp", "open", "high", "low", "close", "volume")
    )


def monte_carlo_test(
    df: pl.DataFrame,
    periods: range | list[int] = range(24, 201),
    n_perms: int = 1000,
    seed: int = 42,
    metric: str = "combined_pct",  # or "support_pct" / "resist_pct"
) -> dict:
    real = sweep_ma_periods(df, periods)
    real_opt = real[metric].max()

    rng = np.random.default_rng(seed)
    perm_opts = np.empty(n_perms)
    for i in range(n_perms):
        perm_df = permute_ohlc(df, int(rng.integers(0, 2**32)))
        perm_opts[i] = sweep_ma_periods(perm_df, periods)[metric].max()

    return {
        "real_sweep": real,
        "real_optimal": real_opt,
        "perm_optimals": perm_opts,
        "p_value": float((perm_opts >= real_opt).mean()),
    }
