import streamlit as st
import pandas as pd
import plotly.express as px
import io
from groq import Groq
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    st.error("GROQ_API_KEY not found in .env file. Please set it up.")
    st.stop()
st.set_page_config(page_title="Epidemic Dashboard", layout="wide")
st.title("🦠 Epidemic Spread Intelligence Dashboard")

uploaded_file = st.file_uploader("Upload CSV/Excel file", type=['csv', 'xlsx', 'xls'])

if uploaded_file:

    # ---------------- READ FILE ----------------
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip().str.lower()

    st.sidebar.success(f"Loaded {df.shape[0]} rows, {df.shape[1]} columns")

    # ---------------- AUTO DETECT ----------------
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

    # Try detect case column
    case_col = next((c for c in numeric_cols if 'case' in c), None)

    # Try detect date column
    date_col = None
    for col in df.columns:
        try:
            df[col] = pd.to_datetime(df[col])
            date_col = col
            break
        except:
            continue

    # ---------------- USER SELECTION ----------------
    st.sidebar.header("Column Selection")

    if not case_col:
        case_col = st.sidebar.selectbox("Select Cases Column", numeric_cols)

    if not date_col:
        date_col = st.sidebar.selectbox("Select Date Column (optional)", df.columns)

    st.sidebar.write(f"Using Cases: {case_col}")
    st.sidebar.write(f"Using Date: {date_col}")

    # Clean data
    df[case_col] = pd.to_numeric(df[case_col], errors='coerce')
    df = df.dropna(subset=[case_col])

    # ---------------- TABS ----------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Data", "📈 Model", "🔮 Prediction", "🛡️ Intervention", "📋 Report"]
    )

    # ---------------- TAB 1 ----------------
    with tab1:
        st.dataframe(df.head())
        st.write("Shape:", df.shape)

    # ---------------- TAB 2 ----------------
    with tab2:
        st.subheader("Trend")

        if date_col:
            fig = px.line(df, x=date_col, y=case_col)
        else:
            fig = px.line(df, y=case_col)

        st.plotly_chart(fig)

        total = df[case_col].sum()
        peak = df[case_col].max()

        growth = 0
        if df[case_col].iloc[0] != 0:
            growth = ((df[case_col].iloc[-1] - df[case_col].iloc[0]) /
                      df[case_col].iloc[0]) * 100

        col1, col2, col3 = st.columns(3)
        col1.metric("Total", f"{total:,.0f}")
        col2.metric("Peak", f"{peak:,.0f}")
        col3.metric("Growth %", f"{growth:.2f}")

    # ---------------- TAB 3 ----------------
    with tab3:
        st.subheader("Prediction")

        days = st.slider("Days", 1, 30, 7)

        last_val = df[case_col].iloc[-1]

        growth_rate = (
            df[case_col].pct_change()
            .replace([float('inf'), -float('inf')], 0)
            .fillna(0)
            .mean()
        )

        future = [last_val * (1 + growth_rate) ** i for i in range(1, days + 1)]

        if date_col:
            future_dates = pd.date_range(df[date_col].iloc[-1], periods=days+1)[1:]
        else:
            future_dates = list(range(1, days+1))

        pred_df = pd.DataFrame({
            "Date": future_dates,
            "Predicted": future
        })

        st.dataframe(pred_df)

        st.plotly_chart(px.line(pred_df, x="Date", y="Predicted"))

    # ---------------- TAB 4 ----------------
    with tab4:
        st.subheader("Intervention")

        options = ["Lockdown", "Vaccination", "Mask", "Distancing"]
        selected = st.multiselect("Select", options)

        eff = st.slider("Effectiveness %", 0, 100, 50)

        base = df[case_col].iloc[-1]

        if selected:
            impact = min(len(selected) * eff * 0.2, 95)
            reduced = base * (1 - impact / 100)

            st.metric("Reduced Cases", f"{reduced:,.0f}", delta=f"-{impact:.1f}%")

            st.plotly_chart(px.bar(
                pd.DataFrame({
                    "Scenario": ["Current", "After"],
                    "Cases": [base, reduced]
                }),
                x="Scenario", y="Cases"
            ))
        else:
            st.warning("Select interventions")

    # ---------------- TAB 5 ----------------
    with tab5:
        if st.button("Download PDF"):
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            story.append(Paragraph("Epidemic Report", styles['Title']))
            story.append(Spacer(1, 12))
            story.append(Paragraph(f"Total Cases: {total}", styles['Normal']))

            doc.build(story)
            buffer.seek(0)

            st.download_button("Download", buffer, "report.pdf")

st.sidebar.info("Upload any dataset")
