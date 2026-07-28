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

    Each country is requested separately, and the results are
    combined into one pandas DataFrame.
    """

    rows = []

    for country_code in country_codes:
        url = BASE_URL.format(
            countries=country_code,
            indicator=indicator,
        )

        params = {
            "format": "json",
            "date": f"{start_year}:{end_year}",
            "per_page": 2000,
            "source": 2,
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
            continue

        for observation in payload[1]:
            if observation["value"] is None:
                continue

            rows.append(
                {
                    "country": observation["country"]["value"],
                    "country_code": observation[
                        "countryiso3code"
                    ],
                    "year": int(observation["date"]),
                    "value": float(observation["value"]),
                }
            )

    dataframe = pd.DataFrame(
        rows,
        columns=[
            "country",
            "country_code",
            "year",
            "value",
        ],
    )

    if dataframe.empty:
        return dataframe

    return (
        dataframe
        .sort_values(["country", "year"])
        .reset_index(drop=True)
    )