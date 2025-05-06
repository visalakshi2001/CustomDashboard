import os, re
import pandas as pd
import streamlit as st

STANDARD_MSG = "{}.json data is not available – upload it via **Edit Data**"

def render(project: dict) -> None:
    """
    Master Warnings / Issues tab.
    Shows three sub‑sections: test‑strategy, requirements, test‑results.
    """
    st.markdown("## Warnings / Issues")
    for section in ("test_strategy", "requirements", "test_results"):
        issuesinfo(project, section)
        st.divider()


# ────────────────────────────────────────────────────────────────
#  Display helpers
# ────────────────────────────────────────────────────────────────
def issuesinfo(project: dict, curr_tab: str) -> None:
    """
    Render a coloured list of issues for the chosen sub‑area.
    """
    cont = st.container(border=True)
    issues = create_issues(project)[curr_tab]

    title_map = {
        "test_strategy":  "Test‑Strategy Checks",
        "requirements":   "Requirements Checks",
        "test_results":   "Test‑Results Checks",
    }
    cont.markdown(f"### {title_map[curr_tab]}")

    if not issues:
        ok_msg = {
            "test_strategy": "All test cases are scheduled without any resource clashes",
            "requirements":  "No requirement‑level issues detected",
            "test_results":  "No test‑result issues detected",
        }[curr_tab]
        cont.success(ok_msg, icon="✅")
        return

    for iss in issues:
        if iss["type"] == "warning":
            cont.warning(iss["message"], icon="⚠️")
        elif iss["type"] == "error":
            cont.error(iss["message"], icon="❗")


# ────────────────────────────────────────────────────────────────
#  Core logic  (temperature‑related checks REMOVED)
# ────────────────────────────────────────────────────────────────
def create_issues(project: dict) -> dict:
    """
    Returns a dict with keys
        { "test_strategy": [...], "requirements": [...], "test_results": [...] }
    Each list holds dicts {type: "warning"/"error", message: str}
    """
    folder = project["folder"]
    p      = lambda f: os.path.join(folder, f)

    issues = {"test_strategy": [], "requirements": [], "test_results": []}

    # ---------- Strategy & Facility data ------------------------------------
    try:
        strategy  = pd.read_csv(p("TestStrategy.csv"))
        facilities = pd.read_csv(p("TestFacilities.csv"))
    except FileNotFoundError:
        return issues  # if one is missing we can't compute anything

    # normalise cols
    strategy.columns = (
        strategy.columns.str.replace(r"\s{2,}", " ", regex=True)
                         .str.replace(r"(?<!^)(?=[A-Z])", " ", regex=True)
                         .str.strip()
                         .str.replace("Org$", "Organization", regex=True)
    )

    # ---> A) duration > 60d
    strategy["Duration Value"] = pd.to_numeric(strategy["Duration Value"], errors="coerce")
    days = strategy.groupby("Test Case")["Duration Value"].max().sum()

    # count facility changes
    link = strategy[["Test Case", "Occurs Before"]].dropna()
    parent = dict(zip(link["Test Case"], link["Occurs Before"]))
    head = (set(parent.keys()) - set(parent.values())).pop()
    ordered = []
    while head:
        ordered.append(head)
        head = parent.get(head)

    fac_seq = strategy.set_index("Test Case").loc[ordered, "Facility"].tolist()
    days += sum(a != b for a, b in zip(fac_seq[:-1], fac_seq[1:])) * 6

    if days > 60:
        issues["test_strategy"].append(
            {"type": "warning", "message": f"Total campaign duration is {int(days)} days (> 60)"}
        )

    # ---> B) researcher & equipment location consistency
    df_chk = strategy[["Test Case", "Researcher", "Facility", "Test Equipment"]].drop_duplicates()
    for _, r in df_chk.iterrows():
        tc, res, fac, eq = r["Test Case"], r["Researcher"], r["Facility"], r["Test Equipment"]

        eq_loc = eq.split("_")[0]
        fac_loc = fac.split("_")[0]
        res_loc = res.split("_")[0]

        if fac_loc not in res_loc and res_loc != fac_loc and res_loc not in fac_loc:
            issues["test_strategy"].append(
                {"type": "error",
                 "message": f"Researcher {res} for Test Case {tc} is not available at Facility {fac}"}
            )
        if fac_loc not in eq_loc and eq_loc not in fac_loc:
            issues["test_strategy"].append(
                {"type": "error",
                 "message": f"Equipment {eq} for Test Case {tc} is not available at Facility {fac}"}
            )

    # ---------- No temperature checks kept for requirements / results -------
    # You can add other requirement‑level rules here later if needed.

    issues["test_strategy"] = pd.DataFrame(issues["test_strategy"]).drop_duplicates().to_dict('records')
    issues["requirements"] = pd.DataFrame(issues["requirements"]).drop_duplicates().to_dict('records')
    issues["test_results"] = pd.DataFrame(issues["test_results"]).drop_duplicates().to_dict('records')
    

    return issues
