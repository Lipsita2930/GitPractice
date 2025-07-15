import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os
from src.workflow_manager import WorkflowManager
import uuid
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Dashboard Runner", layout="wide")

CSV_PATH = "output/query_results.csv" 

if "workflow_ran" not in st.session_state:
    st.session_state.workflow_ran = False
    st.session_state.result_message = []

def call_workFlowManager(user_input):
    workflow_manager = WorkflowManager()
    final_state = workflow_manager.run(input_message=user_input, thread_id=str(uuid.uuid4()))
    return final_state

st.title("Dynamic Dashboard")

user_input = st.text_input("Enter your query.")

if st.button("Run Workflow"):
    if user_input.strip() == "":
        st.warning("⚠️ Please enter something.")
    else:
        with st.spinner("Running your workflow..."):
            summary = call_workFlowManager(user_input)
            print(summary)
            st.session_state.workflow_ran = True
            st.session_state.result_message = [summary]

if st.session_state.workflow_ran:

    st.success("Workflow finished!")
    st.subheader("Detailed Summary:")

    for msg in st.session_state.result_message:
        st.markdown(f"<li style='color:#0a9396; font-weight:600;'>{msg}</li>", unsafe_allow_html=True)

    if os.path.exists(CSV_PATH):
        st.subheader("📊 Query Result Preview:")
        df = pd.read_csv(CSV_PATH)
        st.dataframe(df)

        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        if len(numeric_cols) >= 2:
            x_axis = st.selectbox("X-axis:", options=numeric_cols)
            y_axis = st.selectbox("Y-axis:", options=numeric_cols, index=1)

            st.subheader("🎨 Select Chart Type")

            # ✅ Replace st.radio with tile buttons
            chart_types = {
                "Line": "📈",
                "Bar": "📊",
                "Scatter": "🔵",
                "Pie": "🥧"
            }

            if "selected_chart" not in st.session_state:
                st.session_state.selected_chart = "Line"

            cols = st.columns(len(chart_types))
            for i, (chart, icon) in enumerate(chart_types.items()):
                with cols[i]:
                    if st.button(f"{icon} {chart}"):
                        st.session_state.selected_chart = chart

            chart_type = st.session_state.selected_chart

            # Chart rendering (unchanged)
            if chart_type == "Line":
                fig = px.line(df, x=x_axis, y=y_axis)
            elif chart_type == "Bar":
                fig = px.bar(df, x=x_axis, y=y_axis)
            elif chart_type == "Scatter":
                fig = px.scatter(df, x=x_axis, y=y_axis)
            elif chart_type == "Pie":
                fig = px.pie(df, names=x_axis, values=y_axis)

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Not enough numeric columns for plotting.")
    else:
        st.error(f"❌ CSV file not found at: {CSV_PATH}")
