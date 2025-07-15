import streamlit as st
import pandas as pd
import plotly.express as px
import time
import re
import uuid
from dotenv import load_dotenv
from src.workflow_manager import WorkflowManager
import os

load_dotenv()

# Constants
CSV_PATH = "output/query_results.csv"

# Streamlit Page Configuration
st.set_page_config(page_title="Data Innovators", layout="wide")

# Initialize session state for summary
if "generated_summary" not in st.session_state:
    st.session_state.generated_summary = None

# CSS for styling
st.markdown("""
<style>
.main-title {
    font-size: 2.5em;
    color: #4CAF50;
    text-align: center;
    margin-bottom: 20px;
}
.button-container {
    display: flex;
    justify-content: center;
    margin-bottom: 20px;
}
.button {
    background-color: #4CAF50;
    color: white;
    border: none;
    padding: 10px 20px;
    text-align: center;
    text-decoration: none;
    display: inline-block;
    font-size: 16px;
    margin: 4px 2px;
    cursor: pointer;
    border-radius: 8px;
}
.warning {
    color: #FF5733;
}
.clear-button {
    width: 100%;
    background-color: #f44336;
    color: white;
    border: none;
    padding: 10px;
    text-align: center;
    text-decoration: none;
    display: inline-block;
    font-size: 16px;
    margin-top: 20px;
    cursor: pointer;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

def call_workflow_manager(user_input):
    workflow_manager = WorkflowManager()
    final_state = workflow_manager.run(input_message=user_input, thread_id=str(uuid.uuid4()))
    return final_state

def display_summary(summary):
    if "." in summary:
        sentences = [sentence.strip() for sentence in summary.split('.') if sentence.strip()]
        for sentence in sentences:
            message_placeholder = st.empty()
            full_response = ""
            for chunk in re.split(r'(\s+)', sentence):
                full_response += chunk
                time.sleep(0.01)
                message_placeholder.markdown(full_response + "▌")  # Blinking cursor
            message_placeholder.markdown(full_response + ".")  # Final response

def run_workflow(user_input):
    if user_input.strip() == "":
        st.warning("⚠️ Please enter something.")
    else:
        # Clean the CSV file before new run
        if os.path.exists(CSV_PATH):
            open(CSV_PATH, 'w').close()

        with st.spinner("Running your workflow..."):
            summary = call_workflow_manager(user_input)
            st.session_state.generated_summary = summary  # Cache the summary
            display_summary(summary)

def display_csv_and_charts():
    if os.path.exists(CSV_PATH):
        st.subheader("📊 Query Result Preview:")
        df = pd.read_csv(CSV_PATH)
        st.dataframe(df)

        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        if len(numeric_cols) >= 2:
            x_axis = st.selectbox("X-axis:", options=numeric_cols)
            y_axis = st.selectbox("Y-axis:", options=numeric_cols, index=1)

            # Tile-based chart selector
            st.subheader("🎨 Select Chart Type")
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

            # Chart rendering
            if chart_type == "Line":
                fig = px.line(df, x=x_axis, y=y_axis)
            elif chart_type == "Bar":
                fig = px.bar(df, x=x_axis, y=y_axis)
            elif chart_type == "Scatter":
                fig = px.scatter(df, x=x_axis, y=y_axis)
            elif chart_type == "Pie":
                fig = px.pie(df, names=x_axis, values=y_axis)

            fig.update_layout(
                template="plotly_white",
                title=f"{chart_type} Chart: {y_axis} vs {x_axis}" if chart_type != "Pie" else f"{y_axis} by {x_axis}",
                title_x=0.5,
                plot_bgcolor="#fafafa",
                paper_bgcolor="#fafafa",
                font=dict(size=14),
                margin=dict(l=30, r=30, t=60, b=30)
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Not enough numeric columns for plotting.")
        return df
    else:
        st.error(f"❌ CSV file not found at: {CSV_PATH}")

def main():
    st.markdown("<h1 class='main-title'>Data Explorer</h1>", unsafe_allow_html=True)
    user_input = st.text_input("Please describe your query in detail.")

    # Button Container for Run Workflow
    st.markdown("<div class='button-container'>", unsafe_allow_html=True)
    if st.button("Run Workflow", key="run", help="Run the workflow with the current query"):
        st.session_state.last_run_summary = user_input
        run_workflow(user_input)
    st.markdown("</div>", unsafe_allow_html=True)

    # Display cached summary (if available) after rerun
    if st.session_state.generated_summary:
        display_summary(st.session_state.generated_summary)

    display_csv_and_charts()

# Run the App
if __name__ == "__main__":
    main()
