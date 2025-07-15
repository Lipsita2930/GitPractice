def main():
    st.markdown("<h1 class='main-title'>Data Explorer</h1>", unsafe_allow_html=True)
    user_input = st.text_input("Please describe your query in detail.")

    # Track if button was just clicked
    run_clicked = st.button("Run Workflow", key="run", help="Run the workflow with the current query")

    # Button Container for Run Workflow
    st.markdown("<div class='button-container'>", unsafe_allow_html=True)
    if run_clicked:
        st.session_state.last_run_summary = user_input
        run_workflow(user_input)
    st.markdown("</div>", unsafe_allow_html=True)

    # 🧠 Show cached summary only on rerun, not when button is just clicked
    if st.session_state.generated_summary and not run_clicked:
        display_summary(st.session_state.generated_summary)

    display_csv_and_charts()
