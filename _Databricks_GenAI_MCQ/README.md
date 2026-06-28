activate : venv\Scripts\Activate.ps1

To access the app at http://localhost:8501, you need to start the Streamlit server from within your project’s virtual environment. After activating your environment, run this command in the project directory:

streamlit run app.py

----------------------------
GenAI Associate MCQ Exam Application
This project contains a simple web application built with Streamlit to help you prepare for the Databricks GenAI Associate certification. The app serves randomly selected multiple‑choice questions based on the Databricks Big Book of Generative AI. After completing an exam, you receive immediate feedback along with explanations and pointers to the relevant sections of the book.

Features
Randomized exams – Each session draws 45 questions from a pool of 198 MCQs so you get a fresh experience every time.

Countdown timer – A timer in the sidebar reminds you how much time remains (45 minutes per exam).

Immediate feedback – Once you finish or time runs out, the app shows your selected answers, the correct answers and explanations with citations.

Retake option – Easily restart to try another randomized set of questions.

File Overview
File	Description
app.py	Main Streamlit application. Controls exam flow, timer, question rendering and results display.
mcqs.json	Dataset of 198 MCQs parsed from the Big Book of Generative AI, including options, correct answer and explanation with citation.
requirements.txt	Python dependencies required to run the app.

Running the App
Install dependencies

Use a virtual environment if desired. Install requirements via pip:

bash
Copy
Edit
pip install -r requirements.txt
Launch the app

From the mcq_exam_app directory, run:

bash
Copy
Edit
streamlit run app.py
Take the exam

Open the link that Streamlit prints in your terminal (typically http://localhost:8501). Press Start Exam to begin. Answer each question; a timer in the sidebar counts down from 45 minutes. When you finish all questions or time expires, you’ll see a score summary and explanations.

Feel free to explore the source code and adjust the number of questions, time limit or dataset as needed. Good luck with your studies!