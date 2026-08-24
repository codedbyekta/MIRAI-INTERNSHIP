"""
Life-OS Wellbeing Dashboard
----------------------------
A Streamlit dashboard that visualizes screen-time data and uses the
Google Gemini API as a brutal-but-fair productivity/lifestyle coach.

Run with:
    streamlit run app.py
"""

import os
import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Task 11: Load API key from .env (never hardcode secrets)
# ---------------------------------------------------------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    from google import genai  # current unified Google GenAI SDK
    GEMINI_SDK_AVAILABLE = True
except ImportError:
    GEMINI_SDK_AVAILABLE = False

gemini_client = None
if GEMINI_SDK_AVAILABLE and GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)


# ---------------------------------------------------------------------------
# Page config & light custom CSS for a "professional SaaS" feel
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Life-OS | Wellbeing Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .main > div { padding-top: 1.5rem; }
        [data-testid="stMetric"] {
            background-color: #131722;
            border: 1px solid #262b3d;
            border-radius: 12px;
            padding: 14px 18px;
        }
        [data-testid="stMetricLabel"] { font-weight: 600; opacity: 0.8; }
        h1, h2, h3 { letter-spacing: -0.02em; }
        .life-os-badge {
            display: inline-block; padding: 2px 10px; border-radius: 999px;
            background: #1f2937; color: #a5b4fc; font-size: 0.75rem;
            margin-bottom: 8px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Task 2: Load the data
# ---------------------------------------------------------------------------
@st.cache_data
def load_data(path: str = "screentime.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    return df


try:
    df = load_data()
except FileNotFoundError:
    st.error("screentime.csv not found. Make sure it sits next to app.py.")
    st.stop()

all_dates = sorted(df["Date"].unique())

# ---------------------------------------------------------------------------
# Task 10 (Option C): Shareable Accountability Link — read query params first
# so a shared link can preselect the day.
# ---------------------------------------------------------------------------
query_params = st.query_params
default_date_str = query_params.get("day", None)
if default_date_str:
    try:
        default_date = pd.to_datetime(default_date_str).date()
        default_index = all_dates.index(default_date) if default_date in all_dates else len(all_dates) - 1
    except Exception:
        default_index = len(all_dates) - 1
else:
    default_index = len(all_dates) - 1

default_goal = int(query_params.get("goal", 180))


# ---------------------------------------------------------------------------
# Task 3: Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<span class="life-os-badge">LIFE-OS</span>', unsafe_allow_html=True)
    st.title("⚙️ Controls")

    selected_date = st.selectbox(
        "Select a day",
        options=all_dates,
        index=default_index,
        format_func=lambda d: d.strftime("%A, %b %d"),
    )

    daily_goal = st.slider(
        "Daily screen-time goal (minutes)",
        min_value=30,
        max_value=600,
        value=default_goal,
        step=10,
        help="Set your target max screen time for a day.",
    )

    st.divider()
    st.caption("Data source: screentime.csv · 14-day synthetic log")


# ---------------------------------------------------------------------------
# Data prep for the selected day
# ---------------------------------------------------------------------------
day_df = df[df["Date"] == selected_date].copy()
total_minutes_today = int(day_df["Minutes_Used"].sum())

if not day_df.empty:
    top_app_row = day_df.loc[day_df["Minutes_Used"].idxmax()]
    top_app_name = top_app_row["App_Name"]
    top_app_minutes = int(top_app_row["Minutes_Used"])
else:
    top_app_name, top_app_minutes = "—", 0

diff_from_goal = total_minutes_today - daily_goal


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🧠 Life-OS Wellbeing Dashboard")
st.caption(f"Snapshot for **{selected_date.strftime('%A, %B %d, %Y')}**")


# ---------------------------------------------------------------------------
# Task 4: KPI row
# ---------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Total Screen Time",
        value=f"{total_minutes_today} min",
        delta=f"{total_minutes_today - daily_goal:+d} min vs goal",
        delta_color="inverse",
    )

with col2:
    st.metric(
        label="Most-Used App",
        value=top_app_name,
        delta=f"{top_app_minutes} min",
        delta_color="off",
    )

with col3:
    status = "Over goal" if diff_from_goal > 0 else "Under goal"
    st.metric(
        label="Goal Difference",
        value=f"{abs(diff_from_goal)} min {'over' if diff_from_goal > 0 else 'under'}",
        delta=status,
        delta_color="inverse" if diff_from_goal > 0 else "normal",
    )

st.divider()


# ---------------------------------------------------------------------------
# Task 5: Visualizations
# ---------------------------------------------------------------------------
viz_col1, viz_col2 = st.columns([1.4, 1])

with viz_col1:
    st.subheader("📈 14-Day Screen-Time Trend")
    trend_df = (
        df.groupby("Date")["Minutes_Used"]
        .sum()
        .reset_index()
        .rename(columns={"Minutes_Used": "Total Minutes"})
        .set_index("Date")
    )
    st.line_chart(trend_df, height=280)

with viz_col2:
    st.subheader("📊 Category Breakdown")
    category_today = (
        day_df.groupby("Category")["Minutes_Used"].sum().sort_values(ascending=False)
    )
    st.bar_chart(category_today, height=280)

st.subheader("📱 App-wise Usage — Selected Day")
app_today = day_df.groupby("App_Name")["Minutes_Used"].sum().sort_values(ascending=False)
st.bar_chart(app_today, height=260)

st.divider()


# ---------------------------------------------------------------------------
# Task 6: Data bridge for Gemini — aggregate, don't send the raw dataframe
# ---------------------------------------------------------------------------
def build_summary_string(day_data: pd.DataFrame) -> str:
    """Aggregate the selected day's data by category and return a clean string."""
    category_summary = (
        day_data.groupby("Category")["Minutes_Used"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    app_summary = (
        day_data.groupby("App_Name")["Minutes_Used"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    payload = {
        "date": str(selected_date),
        "total_minutes": total_minutes_today,
        "daily_goal_minutes": daily_goal,
        "minutes_over_or_under_goal": diff_from_goal,
        "by_category": category_summary.to_dict(orient="records"),
        "top_apps": app_summary.to_dict(orient="records"),
    }
    return json.dumps(payload, indent=2)


summary_string = build_summary_string(day_df)


# ---------------------------------------------------------------------------
# Task 7 & 8: Gemini prompt construction
# ---------------------------------------------------------------------------
def build_coach_prompt(summary_json: str) -> str:
    return f"""
You are the "Life-OS Coach" — a brutal-but-fair productivity and lifestyle coach.
You speak directly and honestly, but you are never cruel, and you always back
your points with the actual numbers given to you. No generic filler advice
like "use your phone less" is allowed.

Here is the user's screen-time data for one day, aggregated by category and app
(all times in minutes), along with their self-set daily goal:

{summary_json}

Using ONLY this data, write a coaching report with these sections:

1. **The Verdict** — one blunt sentence on how the day went relative to the goal.
2. **Biggest Time-Wasting Categories** — name the top 1-3 categories that ate the
   most time, with exact minutes, and explain why they matter.
3. **Real-World Replacements** — for each flagged category, suggest a specific,
   realistic physical or real-world replacement activity (e.g. excessive social
   media -> a specific alternative like a 20-minute walk or calling a friend).
   Be concrete, not generic.
4. **Time You Can Reclaim** — estimate a realistic number of minutes per day the
   user could reclaim if they acted on this advice, and what that adds up to
   over a week.

Keep the tone motivating but direct. Use markdown formatting with headers.
"""


def call_gemini(prompt: str) -> str:
    if not GEMINI_SDK_AVAILABLE:
        return (
            "⚠️ The `google-genai` package isn't installed. "
            "Run `pip install google-genai` and try again."
        )
    if not gemini_client:
        return (
            "⚠️ No Gemini API key found. Add `GEMINI_API_KEY=your_key_here` "
            "to a `.env` file in the project root (see Task 11)."
        )
    # gemini-1.5-* models were fully retired. Try current models in order,
    # newest/cheapest-first, and fall back if one isn't available on this key.
    candidate_models = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.6-flash"]
    last_error = None
    for model_name in candidate_models:
        try:
            response = gemini_client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            last_error = e
            continue
    return (
        f"⚠️ Gemini API error: {last_error}\n\n"
        "None of the candidate models were available for this API key. "
        "Run `for m in gemini_client.models.list(): print(m.name)` to see "
        "which models your key supports, then update `candidate_models` "
        "in app.py."
    )


# ---------------------------------------------------------------------------
# Task 9: Display the AI Coach
# ---------------------------------------------------------------------------
st.subheader("🤖 Life-OS Coach")

with st.expander("See the data sent to Gemini (Task 6 data bridge)"):
    st.code(summary_string, language="json")

coach_col, _ = st.columns([1, 3])
with coach_col:
    generate_clicked = st.button("Generate Coaching Report", type="primary", use_container_width=True)

if generate_clicked:
    with st.spinner("The coach is reviewing your day..."):
        prompt = build_coach_prompt(summary_string)
        advice = call_gemini(prompt)

    # Severity-based alert styling
    if diff_from_goal > 120:
        st.error("🚨 Significantly over your goal today.")
    elif diff_from_goal > 0:
        st.warning("⚠️ Slightly over your goal today.")
    else:
        st.info("✅ You stayed within your goal today.")

    st.markdown(advice)

st.divider()


# ---------------------------------------------------------------------------
# Task 10 (Option C): Shareable Accountability Link
# ---------------------------------------------------------------------------
st.subheader("🔗 Shareable Accountability Link")
st.write(
    "Put this day's screen-time stat into a URL so anyone with the link can "
    "see it — no login required."
)

# Update the query params so the current view is reflected in the URL
st.query_params["day"] = selected_date.strftime("%Y-%m-%d")
st.query_params["goal"] = str(daily_goal)
st.query_params["total"] = str(total_minutes_today)

share_col1, share_col2 = st.columns([2, 1])
with share_col1:
    st.text_input(
        "Copy this link to share",
        value=(
            f"?day={selected_date.strftime('%Y-%m-%d')}"
            f"&goal={daily_goal}&total={total_minutes_today}"
        ),
        help="Append this query string to your deployed app's base URL and share it.",
    )
with share_col2:
    st.metric("Shared Stat", f"{total_minutes_today} min", f"goal: {daily_goal} min")

# If someone opened a link with a shared "total" that isn't the current
# session's computed total (e.g. viewing a friend's shared stat), show it.
shared_total = query_params.get("total", None)
if shared_total and shared_total != str(total_minutes_today):
    st.info(f"📬 Someone shared a screen-time stat of **{shared_total} minutes** with this link.")

st.divider()
st.caption("Life-OS Wellbeing Dashboard · Built with Streamlit + Gemini")