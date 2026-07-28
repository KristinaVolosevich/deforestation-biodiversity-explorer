import streamlit as st


st.set_page_config(
    page_title="What Is a Forest Worth?",
    page_icon="🌳",
    layout="wide",
)

st.title("🌳 What Is a Forest Worth?")

st.subheader(
    "An Interactive Deforestation, Biodiversity, "
    "and Conservation Policy Explorer"
)

st.write(
    """
    This application will examine how tropical countries balance
    economic development with forest conservation and biodiversity
    protection.
    """
)

st.info(
    "Version 0.1: Project environment successfully created."
)

st.header("Questions this project will investigate")

st.markdown(
    """
    - How has forest area changed across selected tropical countries?
    - Is forest loss associated with economic or population growth?
    - What biodiversity is documented within these countries?
    - What are the environmental and economic tradeoffs of conservation?
    """
)