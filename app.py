"""
Streamlit job board.

Setup:
    pip install streamlit requests pandas

Run:
    streamlit run app.py
"""

import pandas as pd
import requests
import streamlit as st

HEADERS = {"User-Agent": "job-board/1.0"}

st.set_page_config(page_title="Job Openings", page_icon="💼", layout="wide")


@st.cache_data(ttl=900, show_spinner=False)  # cache for 15 minutes
def fetch_remotive(keyword: str):
    rows = []
    try:
        r = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": keyword} if keyword else {},
            headers=HEADERS,
            timeout=20,
        )
        r.raise_for_status()
        for j in r.json().get("jobs", []):
            rows.append({
                "Title": j.get("title", ""),
                "Company": j.get("company_name", ""),
                "Location": j.get("candidate_required_location", "Remote"),
                "Type": j.get("job_type", "").replace("_", " "),
                "Posted": j.get("publication_date", "")[:10],
                "Source": "Remotive",
                "Link": j.get("url", ""),
            })
    except Exception as e:
        st.warning(f"Remotive failed: {e}")
    return rows


@st.cache_data(ttl=900, show_spinner=False)
def fetch_arbeitnow():
    rows = []
    try:
        r = requests.get(
            "https://www.arbeitnow.com/api/job-board-api",
            headers=HEADERS,
            timeout=20,
        )
        r.raise_for_status()
        for j in r.json().get("data", []):
            posted = ""
            if j.get("created_at"):
                posted = pd.to_datetime(j["created_at"], unit="s").strftime("%Y-%m-%d")
            rows.append({
                "Title": j.get("title", ""),
                "Company": j.get("company_name", ""),
                "Location": j.get("location", "") + (" (Remote)" if j.get("remote") else ""),
                "Type": ", ".join(j.get("job_types", [])),
                "Posted": posted,
                "Source": "Arbeitnow",
                "Link": j.get("url", ""),
                "_tags": " ".join(j.get("tags", [])),
            })
    except Exception as e:
        st.warning(f"Arbeitnow failed: {e}")
    return rows


# ---------------- UI ----------------
st.title("💼 Job Openings")
st.caption("Aggregated from Remotive and Arbeitnow. Refreshes every 15 minutes.")

with st.sidebar:
    st.header("Filters")
    keyword = st.text_input("Keyword", value="python", placeholder="e.g. data analyst")
    location = st.text_input("Location contains", placeholder="e.g. india, europe, remote")
    company = st.text_input("Company contains")
    sources = st.multiselect(
        "Sources", ["Remotive", "Arbeitnow"], default=["Remotive", "Arbeitnow"]
    )
    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()

with st.spinner("Fetching jobs..."):
    rows = []
    if "Remotive" in sources:
        rows += fetch_remotive(keyword.strip())
    if "Arbeitnow" in sources:
        rows += fetch_arbeitnow()

if not rows:
    st.info("No jobs found. Try a different keyword or source.")
    st.stop()

df = pd.DataFrame(rows)
if "_tags" not in df.columns:
    df["_tags"] = ""
df["_tags"] = df["_tags"].fillna("")

# Remotive is already filtered by keyword; Arbeitnow needs a local filter
if keyword.strip():
    kw = keyword.strip().lower()
    text = (df["Title"] + " " + df["_tags"]).str.lower()
    is_arbeitnow = df["Source"] == "Arbeitnow"
    df = df[~is_arbeitnow | text.str.contains(kw, regex=False)]

if location.strip():
    df = df[df["Location"].str.contains(location.strip(), case=False, na=False, regex=False)]
if company.strip():
    df = df[df["Company"].str.contains(company.strip(), case=False, na=False, regex=False)]

df = df.drop(columns=["_tags"]).drop_duplicates(subset=["Link"])
df = df.sort_values("Posted", ascending=False).reset_index(drop=True)

c1, c2 = st.columns(2)
c1.metric("Jobs found", len(df))
c2.metric("Companies", df["Company"].nunique())

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={"Link": st.column_config.LinkColumn("Apply", display_text="Open")},
)

st.download_button(
    "⬇️ Download CSV",
    df.to_csv(index=False).encode("utf-8"),
    file_name="jobs.csv",
    mime="text/csv",
)
