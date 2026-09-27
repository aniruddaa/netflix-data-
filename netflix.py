from pathlib import Path
from io import BytesIO, StringIO

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt


st.set_page_config(
    page_title="Netflix Data Analysis",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="expanded",
)

REQUIRED_COLUMNS = [
    "Watch_Date",
    "Monthly_Revenue",
    "Rating",
    "Region",
    "Device",
    "Subscription_Plan",
    "Watch_Count",
]

st.markdown(
    """
    <style>
    :root {
        --ink: #202124;
        --muted: #6b7078;
        --accent: #e50914;
        --rule: #e6e7e9;
        --paper: #f7f7f5;
    }
    .stApp { background: var(--paper); color: var(--ink); }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background: #efefed; }
    .dashboard-kicker {
        color: var(--accent); font-size: 0.76rem; font-weight: 700;
        letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.25rem;
    }
    .dashboard-title {
        color: var(--ink); font-family: Georgia, 'Times New Roman', serif;
        font-size: 2.65rem; line-height: 1.05; margin: 0;
    }
    .dashboard-subtitle { color: var(--muted); margin: 0.45rem 0 1.2rem; }
    .section-title {
        border-bottom: 1px solid var(--rule); color: var(--ink);
        font-size: 1.05rem; font-weight: 650; padding-bottom: 0.55rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def read_csv(contents: bytes) -> pd.DataFrame:
    frame = pd.read_csv(BytesIO(contents))
    if len(frame.columns) == 1 and "," in str(frame.columns[0]):
        text = contents.decode("utf-8-sig")
        normalized_lines = [
            line[1:-1] if line.startswith('"') and line.endswith('"') else line
            for line in text.splitlines()
        ]
        frame = pd.read_csv(StringIO("\n".join(normalized_lines)))
    return frame


def prepare_data(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["Watch_Date"] = pd.to_datetime(frame["Watch_Date"], errors="coerce")
    frame["Monthly_Revenue"] = pd.to_numeric(
        frame["Monthly_Revenue"], errors="coerce"
    )
    frame["Watch_Count"] = pd.to_numeric(frame["Watch_Count"], errors="coerce")
    frame["Rating"] = pd.to_numeric(frame["Rating"], errors="coerce")
    if "Watch_Time_Minutes" in frame.columns:
        frame["Watch_Time_Minutes"] = pd.to_numeric(
            frame["Watch_Time_Minutes"], errors="coerce"
        )
    frame = frame.drop_duplicates()
    frame["Month"] = frame["Watch_Date"].dt.to_period("M").dt.to_timestamp()
    return frame


def show_percentage_bar(series: pd.Series, title: str, color: str) -> None:
    totals = series.dropna().sort_values(ascending=True)
    total = totals.sum()
    if totals.empty or total <= 0:
        st.info("No positive values are available for this chart.")
        return

    percentages = totals / total * 100
    figure, axis = plt.subplots(figsize=(6, 3.6))
    bars = axis.barh(percentages.index.astype(str), percentages, color=color, height=0.62)
    axis.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=12)
    axis.set_xlabel("Share of total (%)")
    axis.set_xlim(0, max(100, percentages.max() * 1.18))
    axis.grid(axis="x", color="#e6e7e9", linewidth=0.8)
    axis.set_axisbelow(True)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.spines["bottom"].set_color("#d2d4d7")
    axis.tick_params(axis="y", length=0, labelsize=9)
    axis.tick_params(axis="x", colors="#6b7078", labelsize=8)
    for bar, percentage in zip(bars, percentages):
        axis.text(
            percentage + 1,
            bar.get_y() + bar.get_height() / 2,
            f"{percentage:.1f}%",
            va="center",
            fontsize=9,
            color="#202124",
        )
    figure.tight_layout()
    st.pyplot(figure, use_container_width=True)
    plt.close(figure)


logo_column, heading_column = st.columns([0.8, 4], vertical_alignment="center")
with logo_column:
    st.image(Path(__file__).with_name("netflix_logo.svg"), width=150)
with heading_column:
    st.markdown('<p class="dashboard-kicker">Viewing & revenue overview</p>', unsafe_allow_html=True)
    st.markdown('<h1 class="dashboard-title">Netflix Data Analysis</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="dashboard-subtitle">Explore audience activity, subscription mix, and monthly revenue.</p>',
        unsafe_allow_html=True,
    )

with st.sidebar:
    st.markdown("### Dataset")
    uploaded_file = st.file_uploader("Upload a Netflix CSV", type=["csv"])

    app_directory = Path(__file__).parent
    default_path = next(
        (
            candidate
            for candidate in (
                app_directory / "netflix.csv",
                app_directory / "netflix.csv.txt",
            )
            if candidate.exists()
        ),
        None,
    )
    if uploaded_file is not None:
        try:
            source = read_csv(uploaded_file.getvalue())
        except Exception as error:
            st.error(f"Could not read this CSV: {error}")
            st.stop()
    elif default_path is not None:
        try:
            source = read_csv(default_path.read_bytes())
            st.caption(f"Loaded local `{default_path.name}`.")
        except Exception as error:
            st.error(f"Could not read {default_path.name}: {error}")
            st.stop()
    else:
        st.info("Upload `netflix.csv` to begin. A local `netflix.csv` or `netflix.csv.txt` loads automatically.")
        st.stop()

missing_columns = [column for column in REQUIRED_COLUMNS if column not in source.columns]
if missing_columns:
    st.error("This file is missing required columns: " + ", ".join(missing_columns))
    st.caption("Expected: " + ", ".join(REQUIRED_COLUMNS))
    st.stop()

data = prepare_data(source)
if data.empty:
    st.warning("No rows are available after removing duplicate records.")
    st.stop()

with st.sidebar:
    st.markdown("### Filters")
    regions = sorted(data["Region"].dropna().astype(str).unique())
    plans = sorted(data["Subscription_Plan"].dropna().astype(str).unique())
    devices = sorted(data["Device"].dropna().astype(str).unique())
    selected_regions = st.multiselect("Region", regions, default=regions)
    selected_plans = st.multiselect("Subscription plan", plans, default=plans)
    selected_devices = st.multiselect("Device", devices, default=devices)

    valid_dates = data["Watch_Date"].dropna()
    if not valid_dates.empty:
        date_range = st.date_input(
            "Watch date",
            value=(valid_dates.min().date(), valid_dates.max().date()),
            min_value=valid_dates.min().date(),
            max_value=valid_dates.max().date(),
        )
    else:
        date_range = None

filtered = data[
    data["Region"].astype(str).isin(selected_regions)
    & data["Subscription_Plan"].astype(str).isin(selected_plans)
    & data["Device"].astype(str).isin(selected_devices)
]
if date_range and len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    filtered = filtered[
        filtered["Watch_Date"].between(start_date, end_date, inclusive="both")
    ]

if filtered.empty:
    st.warning("No records match these filters. Adjust the selections in the sidebar.")
    st.stop()

st.markdown('<p class="section-title">Netflix viewing & revenue charts</p>', unsafe_allow_html=True)

line_columns = st.columns(2)
with line_columns[0]:
    revenue_by_month = (
        filtered.dropna(subset=["Month"])
        .groupby("Month", as_index=True)["Monthly_Revenue"]
        .sum()
        .sort_index()
    )
    st.markdown("**Monthly revenue trend**")
    if revenue_by_month.empty:
        st.info("No valid watch dates are available for the monthly revenue trend.")
    else:
        st.line_chart(revenue_by_month, color="#e50914", height=280)

with line_columns[1]:
    st.markdown("**Monthly watch time**")
    if "Watch_Time_Minutes" not in filtered.columns:
        st.info("This dataset does not include `Watch_Time_Minutes`.")
    else:
        watch_time_by_month = (
            filtered.dropna(subset=["Month"])
            .groupby("Month", as_index=True)["Watch_Time_Minutes"]
            .sum()
            .sort_index()
        )
        if watch_time_by_month.empty:
            st.info("No valid dates or watch-time values are available.")
        else:
            st.line_chart(watch_time_by_month, color="#282a2e", height=280)

bar_columns = st.columns(2)
with bar_columns[0]:
    revenue_by_region = filtered.groupby("Region")["Monthly_Revenue"].sum()
    show_percentage_bar(revenue_by_region, "Revenue share by region", "#e50914")

with bar_columns[1]:
    watch_count_by_device = filtered.groupby("Device")["Watch_Count"].sum()
    show_percentage_bar(watch_count_by_device, "Watch share by device", "#282a2e")

pie_columns = st.columns(2)
with pie_columns[0]:
    st.markdown("**Watches by subscription plan**")
    watches_by_plan = filtered.groupby("Subscription_Plan")["Watch_Count"].sum()
    watches_by_plan = watches_by_plan[watches_by_plan > 0].sort_values(ascending=False)
    if watches_by_plan.empty:
        st.info("No watch-count values are available for the selected filters.")
    else:
        figure, axis = plt.subplots(figsize=(5, 3.2))
        axis.pie(
            watches_by_plan,
            labels=watches_by_plan.index,
            autopct="%1.1f%%",
            startangle=90,
            colors=["#e50914", "#282a2e", "#7f858d"],
            wedgeprops={"linewidth": 1, "edgecolor": "white"},
        )
        axis.axis("equal")
        st.pyplot(figure, use_container_width=True)
        plt.close(figure)

with pie_columns[1]:
    st.markdown("**Watches by content category**")
    if "Category" not in filtered.columns:
        st.info("This dataset does not include a `Category` column.")
    else:
        watches_by_category = filtered.groupby("Category")["Watch_Count"].sum()
        watches_by_category = watches_by_category[watches_by_category > 0].sort_values(
            ascending=False
        )
        if watches_by_category.empty:
            st.info("No watch-count values are available for the selected categories.")
        else:
            category_colors = [
                "#e50914",
                "#282a2e",
                "#7f858d",
                "#c5c7ca",
                "#b53b42",
                "#50545a",
                "#d77b80",
                "#92979e",
            ]
            figure, axis = plt.subplots(figsize=(5, 3.2))
            axis.pie(
                watches_by_category,
                labels=watches_by_category.index,
                autopct="%1.0f%%",
                startangle=90,
                colors=category_colors[: len(watches_by_category)],
                wedgeprops={"linewidth": 1, "edgecolor": "white"},
                textprops={"fontsize": 8},
            )
            axis.axis("equal")
            st.pyplot(figure, use_container_width=True)
            plt.close(figure)