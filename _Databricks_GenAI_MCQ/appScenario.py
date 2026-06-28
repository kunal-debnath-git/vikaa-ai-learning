"""
Scenario-based Q&A Application
==============================

This Streamlit application allows you to practice scenario-based questions
from the Databricks Big Book of Generative AI. Each session presents a
selection of scenarios where you can type your answer before revealing
the official solution and the recommended reading sections from the
book.

Usage
-----

Run the app with Streamlit:

```
streamlit run app.py
```

You can customize the number of scenarios per session and the time
limit by editing the constants at the top of this file.
"""

import json
import os
import random
import time
from datetime import timedelta

import streamlit as st


# Configuration
NUM_SCENARIOS = 10        # Number of scenario questions per session
TIME_LIMIT_MINUTES = 30   # Total time for a session (in minutes)


def load_scenarios(path: str) -> list:
    """Load scenario-based Q&A from a JSON file.

    The JSON must be a list of dictionaries with at least the keys
    ``scenario``, ``question``, ``answer`` and ``refer_to``.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def init_session_state(scenarios: list, num_questions: int = NUM_SCENARIOS, time_limit_minutes: int = TIME_LIMIT_MINUTES):
    """Initialize Streamlit session state for a new scenario practice session."""
    selected = random.sample(scenarios, min(num_questions, len(scenarios)))
    st.session_state.session_started = True
    st.session_state.scenarios = selected
    st.session_state.responses = ["" for _ in selected]
    st.session_state.current_index = 0
    st.session_state.session_completed = False
    st.session_state.start_time = time.time()
    st.session_state.time_limit = time_limit_minutes * 60
    # Force immediate refresh to display first scenario
    try:
        st.rerun()
    except Exception:
        pass


def format_time(seconds_remaining: float) -> str:
    if seconds_remaining < 0:
        seconds_remaining = 0
    td = timedelta(seconds=int(seconds_remaining))
    minutes = td.seconds // 60
    seconds = td.seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def check_time_limit() -> float:
    """Check remaining time and mark session completed if time has expired."""
    elapsed = time.time() - st.session_state.start_time
    remaining = st.session_state.time_limit - elapsed
    if remaining <= 0 and not st.session_state.session_completed:
        st.session_state.session_completed = True
        remaining = 0
    # Display timer
    st.sidebar.header("Time Remaining")
    st.sidebar.subheader(format_time(remaining))
    return remaining


def render_scenario(index: int):
    """Render a single scenario question and collect user input."""
    scenario_data = st.session_state.scenarios[index]
    st.write(f"**Scenario {index + 1} of {len(st.session_state.scenarios)}**")
    st.write(f"_Background:_ {scenario_data['scenario']}")
    st.write(f"_Question:_ {scenario_data['question']}")
    # Text area for user answer
    user_answer = st.text_area(
        label="Your answer:",
        value=st.session_state.responses[index],
        height=150,
        key=f"answer_{index}"
    )
    st.session_state.responses[index] = user_answer.strip()

    # Navigation controls
    col1, col2 = st.columns([1, 1])
    with col1:
        if index > 0 and st.button("← Previous", key=f"prev_{index}"):
            st.session_state.current_index -= 1
            try:
                st.rerun()
            except Exception:
                pass
    with col2:
        if index < len(st.session_state.scenarios) - 1:
            if st.button("Next →", key=f"next_{index}"):
                st.session_state.current_index += 1
                try:
                    st.rerun()
                except Exception:
                    pass
        else:
            if st.button("Finish Session", key="finish"):
                st.session_state.session_completed = True
                try:
                    st.rerun()
                except Exception:
                    pass


def render_results():
    """Display results at the end of the scenario session."""
    st.header("Session Summary")
    total = len(st.session_state.scenarios)
    for idx, scenario_data in enumerate(st.session_state.scenarios):
        st.write(f"**Scenario {idx + 1}:** {scenario_data['question']}")
        user_answer = st.session_state.responses[idx]
        if user_answer:
            st.write(f"Your answer:\n{user_answer}")
        else:
            st.write("You did not provide an answer.")
        st.write(f"**Official answer:** {scenario_data['answer']}")
        st.write(f"**Refer to:** {scenario_data['refer_to']}")
        st.markdown("---")
    # Allow user to start another session
    if st.button("Start Another Session"):
        st.session_state.session_started = False
        st.session_state.session_completed = False
        try:
            st.rerun()
        except Exception:
            pass


def main():
    st.set_page_config(page_title="GenAI Scenario Practice", layout="wide")
    st.title("Databricks GenAI Scenario Practice")
    st.write("Work through scenario‑based questions from the Big Book of Generative AI.")

    # Load scenarios
    scenario_path = os.path.join(os.path.dirname(__file__), "scenarios.json")
    scenarios = load_scenarios(scenario_path)

    # Initialize session state flags if not present
    if "session_started" not in st.session_state:
        st.session_state.session_started = False
        st.session_state.session_completed = False

    # If session not started yet
    if not st.session_state.session_started:
        st.write(
            f"Each practice session will present {NUM_SCENARIOS} scenario questions selected at random from the available pool of {len(scenarios)}."
        )
        st.write(
            f"You will have {TIME_LIMIT_MINUTES} minutes to work through them. There is no automated grading – compare your responses with the official answers at the end."
        )
        if st.button("Start Session"):
            init_session_state(scenarios)
        return

    # If session completed or time ran out
    remaining = check_time_limit()
    if st.session_state.session_completed:
        render_results()
        return

    # Display current scenario
    current_idx = st.session_state.current_index
    render_scenario(current_idx)


if __name__ == "__main__":
    main()