def display_csv_and_charts():
    if os.path.exists(CSV_PATH):
        if os.stat(CSV_PATH).st_size == 0:
            st.warning("⚠️ The CSV file is empty. Nothing to display.")
            return

        df = pd.read_csv(CSV_PATH)

        if df.empty:
            st.warning("⚠️ The CSV contains no data.")
            return

        st.subheader("📊 Query Result Preview:")
        st.dataframe(df)

        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        if len(numeric_cols) >= 2:
            x_axis = st.selectbox("X-axis:", options=numeric_cols)
            y_axis = st.selectbox("Y-axis:", options=numeric_cols, index=1)

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
    else:
        st.error(f"❌ CSV file not found at: {CSV_PATH}")
