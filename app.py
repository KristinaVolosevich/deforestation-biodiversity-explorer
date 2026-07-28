
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


@st.cache_data(ttl=86400)
def load_forest_data():
    """
    Retrieve forest-area data and temporarily cache it.

    Caching prevents the app from repeatedly requesting the
    same information every time the page refreshes.
    """

    return get_indicator_data(
        country_codes=list(COUNTRIES.values()),
        indicator="AG.LND.FRST.ZS",
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

st.header("Forest Area Over Time")

st.write(
    """
    This chart shows the percentage of each country's land area
    classified as forest. A decline indicates that forest area
    represents a smaller share of the country's total land area.
    """
)

try:
    forest_data = load_forest_data()

except Exception as error:
    st.error(
        "The application could not retrieve data from "
        "the World Bank API."
    )

    st.exception(error)
    st.stop()


if forest_data.empty:
    st.warning(
        "The World Bank API returned no forest-area data."
    )
    st.stop()


filtered_data = forest_data[
    forest_data["country"].isin(selected_countries)
]


if not selected_countries:
    st.warning(
        "Select at least one country using the sidebar."
    )

else:
    figure = px.line(
        filtered_data,
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

    figure.update_layout(
        hovermode="x unified",
        legend_title_text="Country",
    )

    st.plotly_chart(
        figure,
        width="stretch",
    )

    st.caption(
        "Source: World Bank World Development Indicators, "
        "indicator AG.LND.FRST.ZS."
    )

    with st.expander("View the underlying data"):
        st.dataframe(
            filtered_data,
            width="stretch",
            hide_index=True,
        )


st.header("How to Interpret This Information")

st.markdown(
    """
    A declining forest percentage may indicate deforestation,
    land conversion, or other changes in land use.

    However, this chart alone cannot establish why forest area
    changed. Economic growth, agricultural expansion, population
    change, conservation policy, and other factors must be
    investigated separately.
    """
)