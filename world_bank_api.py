import pandas as pd
import requests


BASE_URL = (
    "https://api.worldbank.org/v2/"
    "country/{countries}/indicator/{indicator}"
)


def get_indicator_data(
    country_codes: list[str],
    indicator: str,
    start_year: int = 1990,
    end_year: int = 2023,
) -> pd.DataFrame:
    """
    Retrieve one World Bank indicator for multiple countries.

    Parameters
    ----------
    country_codes:
        A list of three-letter country codes, such as ["BRA", "CRI"].
    indicator:
        A World Bank indicator code.
    start_year:
        First year to request.
    end_year:
        Last year to request.

    Returns
    -------
    pd.DataFrame
        A table with country, country code, year, and value.
    """

    countries = ";".join(country_codes)

    url = BASE_URL.format(
        countries=countries,
        indicator=indicator,
    )

    params = {
        "format": "json",
        "date": f"{start_year}:{end_year}",
        "per_page": 2000,
    }

    response = requests.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    payload = response.json()

    if (
        not isinstance(payload, list)
        or len(payload) < 2
        or payload[1] is None
    ):
        return pd.DataFrame(
            columns=[
                "country",
                "country_code",
                "year",
                "value",
            ]
        )

    rows = []

    for observation in payload[1]:
        if observation["value"] is None:
            continue

        rows.append(
            {
                "country": observation["country"]["value"],
                "country_code": observation["countryiso3code"],
                "year": int(observation["date"]),
                "value": float(observation["value"]),
            }
        )

    dataframe = pd.DataFrame(rows)

    if dataframe.empty:
        return dataframe

    return (
        dataframe
        .sort_values(["country", "year"])
        .reset_index(drop=True)
    )