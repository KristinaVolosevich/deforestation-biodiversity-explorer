import pandas as pd
import plotly.express as px
import streamlit as st

from world_bank_api import get_indicator_data


st.set_page_config(
    page_title="What Is a Forest Worth?",
    page_icon="🌳",
    layout="wide",
)


COUNTRIES = {
    "Brazil": "BRA",
    "Colombia": "COL",
    "Costa Rica": "CRI",
    "Democratic Republic of the Congo": "COD",
    "Indonesia": "IDN",
}


def merge_environmental_data(
    forest_data: pd.DataFrame,
    population_data: pd.DataFrame,
    gdp_data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combine forest, population, and GDP data by country and year.
    """

    forest = forest_data.rename(
        columns={"value": "forest_percent"}
    )

    population = population_data.rename(
        columns={"value": "population"}
    )

    gdp = gdp_data.rename(
        columns={"value": "gdp_per_capita"}
    )

    merged_data = forest.merge(
        population[
            [
                "country_code",
                "year",
                "population",
            ]
        ],
        on=["country_code", "year"],
        how="inner",
    )

    merged_data = merged_data.merge(
        gdp[
            [
                "country_code",
                "year",
                "gdp_per_capita",
            ]
        ],
        on=["country_code", "year"],
        how="inner",
    )

    return (
        merged_data
        .sort_values(["country", "year"])
        .reset_index(drop=True)
    )


@st.cache_data(ttl=86400)
def load_forest_data() -> pd.DataFrame:
    """
    Retrieve forest area as a percentage of land area.
    """

    return get_indicator_data(
        country_codes=list(COUNTRIES.values()),
        indicator="AG.LND.FRST.ZS",
        start_year=1990,
        end_year=2023,
    )


@st.cache_data(ttl=86400)
def load_population_data() -> pd.DataFrame:
    """
    Retrieve total population data.
    """

    return get_indicator_data(
        country_codes=list(COUNTRIES.values()),
        indicator="SP.POP.TOTL",
        start_year=1990,
        end_year=2023,
    )


@st.cache_data(ttl=86400)
def load_gdp_data() -> pd.DataFrame:
    """
    Retrieve GDP per capita data.
    """

    return get_indicator_data(
        country_codes=list(COUNTRIES.values()),
        indicator="NY.GDP.PCAP.CD",
        start_year=1990,
        end_year=2023,
    )


st.title("🌳 What Is a Forest Worth?")

st.subheader(
    "An Interactive Deforestation, Biodiversity, "
    "and Conservation Policy Explorer"
)

st.write(
    """
    This application examines how tropical countries balance
    economic development with forest conservation and
    biodiversity protection.
    """
)

st.sidebar.header("Explorer Settings")

selected_countries = st.sidebar.multiselect(
    "Select countries",
    options=list(COUNTRIES.keys()),
    default=list(COUNTRIES.keys()),
)

if not selected_countries:
    st.warning(
        "Select at least one country using the sidebar."
    )
    st.stop()

selected_country_codes = [
    COUNTRIES[country_name]
    for country_name in selected_countries
]

try:
    forest_data = load_forest_data()
    population_data = load_population_data()
    gdp_data = load_gdp_data()

    merged_data = merge_environmental_data(
        forest_data=forest_data,
        population_data=population_data,
        gdp_data=gdp_data,
    )

except Exception as error:
    st.error(
        "The application could not retrieve data from "
        "the World Bank API."
    )
    st.exception(error)
    st.stop()

if (
    forest_data.empty
    or population_data.empty
    or gdp_data.empty
    or merged_data.empty
):
    st.warning(
        "The World Bank API did not return all required data."
    )
    st.stop()

filtered_forest = forest_data[
    forest_data["country_code"].isin(
        selected_country_codes
    )
].copy()

filtered_population = population_data[
    population_data["country_code"].isin(
        selected_country_codes
    )
].copy()

filtered_gdp = gdp_data[
    gdp_data["country_code"].isin(
        selected_country_codes
    )
].copy()

filtered_merged_data = merged_data[
    merged_data["country_code"].isin(
        selected_country_codes
    )
].copy()


st.header("Forest Area Over Time")

st.write(
    """
    This chart shows the percentage of each country's land area
    classified as forest. A decline indicates that forest area
    represents a smaller share of the country's total land area.
    """
)

st.subheader("Forest Change Summary")

summary_rows = []

for country_code in selected_country_codes:
    country_data = (
        filtered_forest[
            filtered_forest["country_code"] == country_code
        ]
        .sort_values("year")
    )

    if country_data.empty:
        continue

    first_row = country_data.iloc[0]
    latest_row = country_data.iloc[-1]

    summary_rows.append(
        {
            "country": latest_row["country"],
            "start_year": int(first_row["year"]),
            "latest_year": int(latest_row["year"]),
            "start_value": float(first_row["value"]),
            "latest_value": float(latest_row["value"]),
            "change": (
                float(latest_row["value"])
                - float(first_row["value"])
            ),
        }
    )

if summary_rows:
    summary_columns = st.columns(len(summary_rows))

    for column, summary in zip(
        summary_columns,
        summary_rows,
    ):
        column.metric(
            label=summary["country"],
            value=f'{summary["latest_value"]:.1f}%',
            delta=(
                f'{summary["change"]:+.1f} percentage points '
                f'since {summary["start_year"]}'
            ),
        )

    st.caption(
        "The cards show the latest available forest share "
        "and its change from the first available year."
    )

forest_figure = px.line(
    filtered_forest,
    x="year",
    y="value",
    color="country",
    markers=True,
    labels={
        "year": "Year",
        "value": "Forest area (% of land area)",
        "country": "Country",
    },
    title=(
        "Forest Area as a Percentage of Total Land Area, "
        "1990–2023"
    ),
)

forest_figure.update_layout(
    hovermode="x unified",
    legend_title_text="Country",
)

st.plotly_chart(
    forest_figure,
    width="stretch",
)

st.caption(
    "Source: World Bank World Development Indicators, "
    "indicator AG.LND.FRST.ZS."
)

with st.expander("View the underlying forest data"):
    st.dataframe(
        filtered_forest,
        width="stretch",
        hide_index=True,
    )


st.header("Population and Economic Development")

st.write(
    """
    Forest change does not happen in isolation. Population growth
    and economic development may increase demand for housing,
    agriculture, infrastructure, energy, and other land uses.
    """
)

population_figure = px.line(
    filtered_population,
    x="year",
    y="value",
    color="country",
    labels={
        "year": "Year",
        "value": "Population",
        "country": "Country",
    },
    title="Total Population, 1990–2023",
)

population_figure.update_layout(
    hovermode="x unified",
    legend_title_text="Country",
)

st.plotly_chart(
    population_figure,
    width="stretch",
)

gdp_figure = px.line(
    filtered_gdp,
    x="year",
    y="value",
    color="country",
    labels={
        "year": "Year",
        "value": "GDP per capita (current US$)",
        "country": "Country",
    },
    title="GDP per Capita, 1990–2023",
)

gdp_figure.update_layout(
    hovermode="x unified",
    legend_title_text="Country",
)

st.plotly_chart(
    gdp_figure,
    width="stretch",
)

st.caption(
    "Source: World Bank World Development Indicators. "
    "Population indicator: SP.POP.TOTL. "
    "GDP per capita indicator: NY.GDP.PCAP.CD."
)


st.header("Combined Environmental Dataset")

st.write(
    """
    This table combines forest area, population, and GDP per
    capita for the same country and year.
    """
)

with st.expander("View combined data"):
    st.dataframe(
        filtered_merged_data,
        width="stretch",
        hide_index=True,
    )


st.header("How to Interpret This Information")

st.markdown(
    """
    A declining forest percentage may indicate deforestation,
    land conversion, or other changes in land use.

    However, these charts alone cannot establish why forest area
    changed. Economic growth, agricultural expansion, population
    change, conservation policy, and other factors must be
    investigated separately.

    Relationships between the variables should be interpreted as
    associations rather than proof that one variable caused changes
    in another.
    """
)