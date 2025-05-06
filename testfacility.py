import os
import streamlit as st
import pandas as pd

STANDARD_MSG = "{}.json data is not available – upload it via **Edit Data**"

def render(project: dict) -> None:
    """
    Dynamic Test‑Facility view.
    • Any number of facilities supported.
    • 2‑column grid; additional rows appear automatically.
    • Shows equipment table for each facility.
    """
    folder   = project["folder"]
    csv_path = os.path.join(folder, "TestFacilities.csv")

    if not os.path.exists(csv_path):
        st.info(STANDARD_MSG.format("TestFacilities"))
        return

    df = pd.read_csv(csv_path)

    # Normalise column names just once
    df.columns = df.columns.str.replace(r"(?<!^)(?=[A-Z])", " ", regex=True).str.strip()
    facilities = df["Test Facility"].unique()

    # Build a 2‑col layout
    for i in range(0, len(facilities), 2):
        cols = st.columns(2)
        for idx, facility in enumerate(facilities[i : i + 2]):
            with cols[idx]:
                st.subheader(f"🏭 {facility.replace('_', ' ')}", divider="orange")
                equip = (
                    df.loc[df["Test Facility"] == facility, "Equipment"]
                    .dropna()
                    .value_counts()
                    .rename_axis("Equipment")
                    .reset_index(name="Count")
                )
                st.dataframe(equip, hide_index=True, use_container_width=True)
