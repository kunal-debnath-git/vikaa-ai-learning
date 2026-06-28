"""
Interactive MCQ Exam App using Streamlit
=======================================

This Streamlit application presents a randomized exam based on the
Databricks GenAI MCQ dataset. Each exam draws 45 questions at random
from the available pool and tracks the user's answers against the
correct responses. A simple countdown timer reminds the user of
remaining time. Once all questions are answered or time runs out,
the app displays a summary with explanations and guidance on where
to study further.

To run locally, install the dependencies listed in ``requirements.txt``
and execute ``streamlit run app.py`` from the project directory.
"""

import json
import os
import random
import time
from datetime import timedelta

import streamlit as st


def load_mcqs(json_path: str):
    """Load MCQs from a JSON file.

    The JSON must contain a list of objects with keys:
    ``number``, ``question``, ``options``, ``correct_answer``, and
    ``explanation``.

    Parameters
    ----------
    json_path : str
        Path to the JSON file containing MCQs.

    Returns
    -------
    list[dict]
        A list of MCQ dictionaries.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def init_exam_state(mcq_pool: list, num_questions: int = 45, time_limit_minutes: int = 45):
    """Initialize session state for a new exam.

    Selects ``num_questions`` random MCQs from ``mcq_pool`` and
    stores them along with other bookkeeping variables in
    ``st.session_state``.

    Parameters
    ----------
    mcq_pool : list
        The full list of MCQ dictionaries.
    num_questions : int, optional
        Number of questions in a single exam attempt, by default 45.
    time_limit_minutes : int, optional
        Total time limit for the exam in minutes, by default 45.
    """
    questions = random.sample(mcq_pool, num_questions)
    st.session_state.exam_started = True
    st.session_state.questions = questions
    st.session_state.responses = [None] * len(questions)
    st.session_state.current_index = 0
    st.session_state.start_time = time.time()
    st.session_state.time_limit = time_limit_minutes * 60  # seconds
    st.session_state.exam_completed = False

    # Immediately rerun the app so the first question appears without an extra click
    # Requires Streamlit version >= 1.24
    try:
        st.rerun()
    except Exception:
        pass


def format_timedelta(seconds_remaining: float) -> str:
    """Convert a number of seconds to a MM:SS formatted string."""
    if seconds_remaining < 0:
        seconds_remaining = 0
    td = timedelta(seconds=int(seconds_remaining))
    # Only show minutes and seconds (e.g., '05:30')
    return f"{td.seconds // 60:02d}:{td.seconds % 60:02d}"


def render_question(question_dict: dict, question_idx: int):
    """Render a single MCQ and collect user response.

    Parameters
    ----------
    question_dict : dict
        The question to display (contains ``question``, ``options`` etc.).
    question_idx : int
        Zero‑based index of the current question in the exam.

    Notes
    -----
    The function stores the user's selection in ``st.session_state.responses``.
    """
    st.write(f"**Question {question_idx + 1} of {len(st.session_state.questions)}**")
    st.write(question_dict["question"])
    # Display options as radio buttons
    option_labels = ['A', 'B', 'C', 'D']
    # Create a mapping between label and text for display
    options_display = [f"{label}. {text}" for label, text in zip(option_labels, question_dict["options"])]
    # Retrieve previously selected answer if any
    prev_answer = st.session_state.responses[question_idx]
    selected = st.radio(
        "Select your answer:",
        options_display,
        index=option_labels.index(prev_answer) if prev_answer in option_labels else None,
        format_func=lambda x: x,
        key=f"question_{question_idx}"
    )
    # Save the selected answer letter ('A','B','C','D')
    if selected:
        answer_letter = selected.split('.')[0]
        st.session_state.responses[question_idx] = answer_letter

    # Navigation buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        # Previous button only shown if not first question
        if question_idx > 0 and st.button("← Previous", key=f"prev_{question_idx}"):
            # decrement index to show previous question
            st.session_state.current_index -= 1
            # Force rerun to display the previous question immediately
            try:
                st.rerun()
            except Exception:
                pass
    with col2:
        # Next or Finish button depending on progress
        if question_idx < len(st.session_state.questions) - 1:
            if st.button("Next →", key=f"next_{question_idx}"):
                # Ensure an answer is recorded before moving forward
                if st.session_state.responses[question_idx] is None:
                    st.warning("Please select an answer before proceeding.")
                else:
                    st.session_state.current_index += 1
                    # Force rerun to display the next question
                    try:
                        st.rerun()
                    except Exception:
                        pass
        else:
            # Last question: finish exam
            if st.button("Finish Exam", key="finish"):
                if st.session_state.responses[question_idx] is None:
                    st.warning("Please select an answer before finishing.")
                else:
                    st.session_state.exam_completed = True
                    # Force rerun to show results immediately
                    try:
                        st.rerun()
                    except Exception:
                        pass


def render_results():
    """Render the exam results after completion or when time runs out."""
    st.header("Exam Results")
    questions = st.session_state.questions
    responses = st.session_state.responses
    total_correct = 0
    # Iterate through each question and show explanation
    for idx, q in enumerate(questions):
        user_answer = responses[idx]
        correct_answer = q["correct_answer"]
        correct = user_answer == correct_answer
        if correct:
            total_correct += 1
        st.write(f"**Question {idx + 1}:** {q['question']}")
        # Show user answer and whether it was correct
        if user_answer:
            st.write(f"Your answer: {user_answer}")
        else:
            st.write("You skipped this question.")
        st.write(f"Correct answer: {correct_answer}")
        # Indicate correct/incorrect
        if correct:
            st.success("Correct!")
        else:
            st.error("Incorrect.")
        # Show explanation
        st.write(f"Explanation: {q['explanation']}")
        st.markdown("---")
    # Score summary
    st.subheader(f"Final Score: {total_correct} out of {len(questions)}")
    # Offer to restart exam
    if st.button("Retake Exam"):
        st.session_state.exam_started = False
        st.session_state.exam_completed = False
        # Rerun to return to the start page
        try:
            st.rerun()
        except Exception:
            pass



def check_time():
    """Check if the time limit has been reached and update exam state."""
    elapsed = time.time() - st.session_state.start_time
    remaining = st.session_state.time_limit - elapsed
    if remaining <= 0:
        # Time is up
        st.session_state.exam_completed = True
        remaining = 0
    # Display timer
    timer_str = format_timedelta(remaining)
    st.sidebar.header("Time Remaining")
    st.sidebar.subheader(timer_str)
    return remaining


def main():
    # Only set page configuration on the first run. Calling set_page_config more than
    # once in a Streamlit session will raise an exception. Use a try/except so
    # that importing this module from a wrapper does not crash.
    try:
        st.set_page_config(page_title="GenAI MCQ Exam", layout="wide")
    except Exception:
        pass
    st.title("Databricks GenAI Associate Exam Practice")
    st.write(
        "Prepare for the Databricks GenAI Associate certification with a randomized practice exam."
    )

    # Load MCQ dataset
    mcq_path = os.path.join(os.path.dirname(__file__), "mcqs.json")
    mcqs = load_mcqs(mcq_path)

    # Check if exam state exists
    if "exam_started" not in st.session_state:
        st.session_state.exam_started = False
        st.session_state.exam_completed = False

    # If exam hasn't started yet
    if not st.session_state.exam_started:
        st.write(
            "Each exam consists of 45 questions selected at random from a pool of 198. You will have 45 minutes to complete the exam."
        )
        if st.button("Start Exam"):
            # Initialize a new exam. init_exam_state will trigger a rerun.
            init_exam_state(mcqs)
        return

    # If exam is completed (either by finishing or time up)
    if st.session_state.exam_completed:
        render_results()
        return

    # Exam in progress
    # Check timer and update remaining time
    remaining = check_time()
    # If time ran out, display results
    if st.session_state.exam_completed:
        render_results()
        return

    # Display current question
    q_idx = st.session_state.current_index
    current_question = st.session_state.questions[q_idx]
    render_question(current_question, q_idx)


if __name__ == "__main__":
    main()