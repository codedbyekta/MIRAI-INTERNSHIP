# 🌀 The Identity Echo Interface

A simple **Streamlit** application built for Session 2 to practice user input, button actions, validation, and conditional output.

## ✨ Features

* Collects **Name** and **Message**
* `Transmit` button to process input
* Validates empty fields using `st.error()` and `st.warning()`
* Displays personalized success message
* Estimates token usage using `characters / 4`

## 🛠️ Tech Stack

* Python
* Streamlit

## 🚀 Run Locally

```bash
python -m venv venv
venv\Scripts\activate
pip install streamlit
streamlit run app.py
```

Then open `http://localhost:8501`.

## 📂 Structure

```text
Identity-Echo-Interface/
├── app.py
└── README.md
```

## 🎯 Assignment Tasks

* [x] Task 1: UI Shell
* [x] Task 2: Multi-Data Collection
* [x] Task 3: Action Gate
* [x] Task 4: Conditional Routing
* [x] Task 5: Formatted Output
* [x] Advanced Challenge: Token Cost Estimator

**Author:** Ekta
