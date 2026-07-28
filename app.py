import pandas as pd
import plotly.express as px
import streamlit as st

from database import (
    initialize_database,
    query_annual_change_summary,
)
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


def calculate_annual_changes(
    merged_data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate annual changes in forest area, population,
    and GDP per capita within each country.
    """

    change_data = (
        merged_data
        .sort_values(["country_code", "year"])
        .copy()
    )

    grouped_data = change_data.groupby(
        "country_code",
        group_keys=False,
    )

    change_data["year_gap"] = (
        grouped_data["year"]
        .diff()
    )

    change_data["forest_change_pp"] = (
        grouped_data["forest_percent"]
        .diff()
    )

    change_data["population_growth_pct"] = (
        grouped_data["population"]
        .transform(
            lambda series: (
                series.pct_change(
                    fill_method=None
                ) * 100
            )
        )
    )

    change_data["gdp_growth_pct"] = (
        grouped_data["gdp_per_capita"]
        .transform(
            lambda series: (
                series.pct_change(
                    fill_method=None
                ) * 100
            )
        )
    )

    change_data = change_data.dropna(
        subset=[
            "forest_change_pp",
            "population_growth_pct",
            "gdp_growth_pct",
        ]
    )

    change_data = change_data[
        change_data["year_gap"] == 1
    ]

    return change_data.reset_index(drop=True)


def build_correlation_table(
    change_data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate Pearson correlations separately for each country.
    """

    correlation_rows = []

    for country, country_data in change_data.groupby(
        "country"
    ):
        if len(country_data) < 2:
            continue

        population_correlation = country_data[
            "forest_change_pp"
        ].corr(
            country_data[
                "population_growth_pct"
            ]
        )

        gdp_correlation = country_data[
            "forest_change_pp"
        ].corr(
            country_data[
                "gdp_growth_pct"
            ]
        )

        correlation_rows.append(
            {
                "Country": country,
                (
                    "Forest change vs. population "
                    "growth (r)"
                ): population_correlation,
                (
                    "Forest change vs. GDP growth (r)"
                ): gdp_correlation,
            }
        )

    if not correlation_rows:
        return pd.DataFrame()

    return (
        pd.DataFrame(correlation_rows)
        .round(3)
        .sort_values("Country")
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


@st.cache_data(ttl=86400)
def load_biodiversity_data() -> pd.DataFrame:
    """
    Retrieve threatened-species indicators.

    Keep the latest available observation for each country
    and species category.
    """

    indicators = {
        "Threatened mammals": "EN.MAM.THRD.NO",
        "Threatened birds": "EN.BIR.THRD.NO",
        "Threatened higher plants": "EN.HPT.THRD.NO",
    }

    biodiversity_frames = []

    for category, indicator_code in indicators.items():
        indicator_data = get_indicator_data(
            country_codes=list(COUNTRIES.values()),
            indicator=indicator_code,
            start_year=1990,
            end_year=2023,
        )

        if indicator_data.empty:
            continue

        indicator_data = indicator_data.copy()
        indicator_data["category"] = category
        indicator_data["indicator"] = indicator_code

        biodiversity_frames.append(
            indicator_data
        )

    if not biodiversity_frames:
        return pd.DataFrame(
            columns=[
                "country",
                "country_code",
                "year",
                "value",
                "category",
                "indicator",
            ]
        )

    combined_data = pd.concat(
        biodiversity_frames,
        ignore_index=True,
    )

    latest_data = (
        combined_data
        .sort_values("year")
        .groupby(
            ["country_code", "category"],
            group_keys=False,
        )
        .tail(1)
        .sort_values(["country", "category"])
        .reset_index(drop=True)
    )

    return latest_data


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
    biodiversity_data = load_biodiversity_data()

    merged_data = merge_environmental_data(
        forest_data=forest_data,
        population_data=population_data,
        gdp_data=gdp_data,
    )

    annual_change_data = calculate_annual_changes(
        merged_data
    )

    initialize_database(
        merged_data=merged_data,
        annual_change_data=annual_change_data,
    )

except Exception as error:
    st.error(
        "The application could not retrieve or process "
        "the required environmental data."
    )
    st.exception(error)
    st.stop()


if (
    forest_data.empty
    or population_data.empty
    or gdp_data.empty
    or merged_data.empty
    or annual_change_data.empty
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

filtered_change_data = annual_change_data[
    annual_change_data["country_code"].isin(
        selected_country_codes
    )
].copy()

filtered_biodiversity = biodiversity_data[
    biodiversity_data["country_code"].isin(
        selected_country_codes
    )
].copy()

correlation_table = build_correlation_table(
    filtered_change_data
)

sql_change_summary = query_annual_change_summary(
    selected_country_codes
)


# ---------------------------------------------------------
# FOREST AREA
# ---------------------------------------------------------

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
            filtered_forest["country_code"]
            == country_code
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
            "start_value": float(
                first_row["value"]
            ),
            "latest_value": float(
                latest_row["value"]
            ),
            "change": (
                float(latest_row["value"])
                - float(first_row["value"])
            ),
        }
    )


if summary_rows:
    summary_columns = st.columns(
        len(summary_rows)
    )

    for column, summary in zip(
        summary_columns,
        summary_rows,
    ):
        column.metric(
            label=summary["country"],
            value=(
                f'{summary["latest_value"]:.1f}%'
            ),
            delta=(
                f'{summary["change"]:+.1f} '
                "percentage points since "
                f'{summary["start_year"]}'
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

with st.expander(
    "View the underlying forest data"
):
    st.dataframe(
        filtered_forest,
        width="stretch",
        hide_index=True,
    )


# ---------------------------------------------------------
# POPULATION AND ECONOMIC DEVELOPMENT
# ---------------------------------------------------------

st.header("Population and Economic Development")

st.write(
    """
    Forest change does not happen in isolation. Population
    growth and economic development may increase demand for
    housing, agriculture, infrastructure, energy, and other
    land uses.
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


# ---------------------------------------------------------
# BIODIVERSITY
# ---------------------------------------------------------

st.header("Biodiversity at Risk")

st.write(
    """
    Tropical forests provide habitat for large numbers of
    plant and animal species. The chart below shows the latest
    available reported counts of threatened mammals, birds,
    and higher plants for the selected countries.
    """
)

if filtered_biodiversity.empty:
    st.warning(
        "No threatened-species data were available for "
        "the selected countries."
    )

else:
    biodiversity_figure = px.bar(
        filtered_biodiversity,
        x="country",
        y="value",
        color="category",
        barmode="group",
        hover_data={
            "year": True,
            "indicator": True,
            "value": ":,.0f",
        },
        labels={
            "country": "Country",
            "value": "Number of threatened species",
            "category": "Species category",
            "year": "Data year",
            "indicator": "World Bank indicator",
        },
        title=(
            "Latest Available Threatened-Species "
            "Counts by Country"
        ),
    )

    biodiversity_figure.update_layout(
        legend_title_text="Species category",
    )

    st.plotly_chart(
        biodiversity_figure,
        width="stretch",
    )

    st.caption(
        """
        Source: World Bank World Development Indicators,
        using threatened-species indicators associated with
        international conservation assessments.
        """
    )

    with st.expander(
        "View the underlying biodiversity data"
    ):
        st.dataframe(
            filtered_biodiversity,
            width="stretch",
            hide_index=True,
        )

st.info(
    """
    Important limitation: threatened-species counts are not a
    complete measurement of biodiversity. Countries differ in
    total species richness, geographic size, research effort,
    assessment coverage, and reporting year. A larger count may
    reflect greater extinction risk, greater natural species
    richness, more extensive assessment, or a combination of
    these factors.
    """
)


# ---------------------------------------------------------
# STATISTICAL ANALYSIS
# ---------------------------------------------------------

st.header("Statistical Relationships")

st.write(
    """
    The charts below compare annual changes rather than raw
    levels. This reduces the risk of finding misleading
    correlations simply because multiple variables trend over
    time.
    """
)

analysis_column_1, analysis_column_2 = (
    st.columns(2)
)

population_scatter = px.scatter(
    filtered_change_data,
    x="population_growth_pct",
    y="forest_change_pp",
    color="country",
    hover_data=["year"],
    labels={
        "population_growth_pct": (
            "Annual population growth (%)"
        ),
        "forest_change_pp": (
            "Annual forest-area change "
            "(percentage points)"
        ),
        "country": "Country",
        "year": "Year",
    },
    title=(
        "Forest Change vs. Population Growth"
    ),
)

analysis_column_1.plotly_chart(
    population_scatter,
    width="stretch",
)

gdp_scatter = px.scatter(
    filtered_change_data,
    x="gdp_growth_pct",
    y="forest_change_pp",
    color="country",
    hover_data=["year"],
    labels={
        "gdp_growth_pct": (
            "Annual GDP-per-capita growth (%)"
        ),
        "forest_change_pp": (
            "Annual forest-area change "
            "(percentage points)"
        ),
        "country": "Country",
        "year": "Year",
    },
    title=(
        "Forest Change vs. GDP-per-Capita Growth"
    ),
)

analysis_column_2.plotly_chart(
    gdp_scatter,
    width="stretch",
)

st.subheader("Country-Level Correlations")

if correlation_table.empty:
    st.warning(
        "There were not enough observations to calculate "
        "the selected correlations."
    )

else:
    st.dataframe(
        correlation_table,
        width="stretch",
        hide_index=True,
    )

st.caption(
    """
    Pearson correlation coefficients range from -1 to +1.
    Negative values indicate that higher growth tended to occur
    during years with greater forest decline. Positive values
    indicate that higher growth tended to occur during years
    with increasing or less rapidly declining forest area.
    """
)


# ---------------------------------------------------------
# SQL
# ---------------------------------------------------------

st.header("SQL Database Analysis")

st.write(
    """
    The project stores its cleaned datasets in a DuckDB
    database. The table below was produced with a SQL query
    that groups annual forest changes by country.
    """
)

st.dataframe(
    sql_change_summary,
    width="stretch",
    hide_index=True,
)

sql_figure = px.bar(
    sql_change_summary,
    x="Country",
    y="Average annual forest change (pp)",
    labels={
        "Average annual forest change (pp)": (
            "Average annual forest change "
            "(percentage points)"
        ),
    },
    title=(
        "Average Annual Change in Forest Share "
        "by Country"
    ),
)

st.plotly_chart(
    sql_figure,
    width="stretch",
)

st.caption(
    """
    Negative values indicate that forest's share of total land
    declined on average during the years included in the merged
    dataset.
    """
)

with st.expander("View the SQL query"):
    st.code(
        """
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
WHERE country_code IN (...)
GROUP BY country
ORDER BY
    "Average annual forest change (pp)" ASC;
        """,
        language="sql",
    )


# ---------------------------------------------------------
# COMBINED DATA
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# INTERPRETATION
# ---------------------------------------------------------

st.header("How to Interpret This Information")

st.markdown(
    """
    A decline in forest percentage may reflect deforestation,
    conversion of forests to agriculture, infrastructure
    development, or other changes in land use.

    The scatterplots and correlations identify statistical
    associations, not cause-and-effect relationships. Population
    or economic growth may occur alongside forest loss without
    directly causing it.

    Other possible influences include agricultural exports,
    logging, mining, road construction, government enforcement,
    protected areas, conservation funding, political conditions,
    and changes in how land is measured.

    Using annual changes reduces the problem of shared time
    trends, but it does not eliminate confounding variables,
    delayed effects, measurement limitations, or differences
    among countries.

    Threatened-species counts provide evidence about biodiversity
    risk, but they are not equivalent to total biodiversity or
    the annual rate of biodiversity loss. Differences in species
    richness, country size, scientific assessment, and reporting
    coverage limit direct comparisons.

    Costa Rica is particularly important because its forest share
    increased over the study period. Its results demonstrate that
    economic and population growth do not automatically require
    continuing forest decline when conservation policy and forest
    recovery alter the relationship.
    """
)