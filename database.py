from pathlib import Path

import duckdb
import pandas as pd


DATABASE_PATH = Path("environmental_data.duckdb")


def initialize_database(
    merged_data: pd.DataFrame,
    annual_change_data: pd.DataFrame,
) -> None:
    """
    Create a DuckDB database and store the cleaned project datasets.
    """

    connection = duckdb.connect(str(DATABASE_PATH))

    try:
        connection.register(
            "merged_dataframe",
            merged_data,
        )

        connection.register(
            "annual_change_dataframe",
            annual_change_data,
        )

        connection.execute(
            """
            CREATE OR REPLACE TABLE environmental_data AS
            SELECT *
            FROM merged_dataframe
            """
        )

        connection.execute(
            """
            CREATE OR REPLACE TABLE annual_changes AS
            SELECT *
            FROM annual_change_dataframe
            """
        )

    finally:
        connection.close()


def query_annual_change_summary(
    country_codes: list[str],
) -> pd.DataFrame:
    """
    Use SQL to summarize annual forest changes by country.
    """

    if not country_codes:
        return pd.DataFrame()

    placeholders = ", ".join(
        ["?"] * len(country_codes)
    )

    query = f"""
        SELECT
            country AS Country,

            ROUND(
                AVG(forest_change_pp),
                3
            ) AS "Average annual forest change (pp)",

            ROUND(
                MIN(forest_change_pp),
                3
            ) AS "Largest annual decline (pp)",

            ROUND(
                MAX(forest_change_pp),
                3
            ) AS "Largest annual increase (pp)",

            COUNT(*) AS "Years analyzed"

        FROM annual_changes

        WHERE country_code IN ({placeholders})

        GROUP BY
            country

        ORDER BY
            "Average annual forest change (pp)" ASC
    """

    connection = duckdb.connect(
        str(DATABASE_PATH),
        read_only=True,
    )

    try:
        return connection.execute(
            query,
            country_codes,
        ).fetchdf()

    finally:
        connection.close()