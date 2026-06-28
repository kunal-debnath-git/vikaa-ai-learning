"""
Combined Exam Practice Wrapper
=============================

This Streamlit application serves as a single entry point to both
the multiple‑choice exam and the scenario‑based practice apps. Use
the sidebar to select which mode you want to study, and the
corresponding module will render within the same Streamlit session.

Run with:

```
streamlit run app_combined.py
```
"""

import streamlit as st

# Import the main functions from the individual apps
from mcq_exam_app.app import main as mcq_main
from scenario_app.app import main as scenario_main


def main():
    # Set a general page configuration for the wrapper
    st.set_page_config(page_title="GenAI Practice Suite", layout="wide")
    st.sidebar.title("Practice Modes")
    selection = st.sidebar.radio(
        "Choose a practice mode:",
        ("Multiple‑Choice Exam", "Scenario Practice"),
        index=0
    )
    # Render the selected application
    if selection == "Multiple‑Choice Exam":
        mcq_main()
    else:
        scenario_main()


if __name__ == "__main__":
    main()