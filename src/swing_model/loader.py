import polars as pl
import polars.selectors as cs
import glob
from datetime import datetime
import logging

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
