```
$ whoami
> viva-panel-simulator

$ cat description.txt
> A multi-persona AI mock interview app. Record your answer on camera + mic,
> and get graded by three distinct AI personas: a strict HR manager,
> a technical panelist, and a supportive mentor — each scoring you
> from a different lens.
```

## → Why this exists
Most mock-interview tools give you a single generic score. Real interview panels
don't work that way — different evaluators care about different things. This app
simulates that by running the *same* answer through three independent AI personas
and aggregating their verdicts into one scorecard.

## → Architecture

```
User sets target role
        ↓
Gemini generates N tailored questions
        ↓
Per question:
  camera_input (posture snapshot) + audio_input (spoken answer)
        ↓
  Gemini transcribes audio → plain text answer
        ↓
  3x Gemini calls (HR / Technical / Mentor personas)
        ↓
  Technical Panelist ALSO decides: does this answer need a follow-up?
  → If yes, an adaptive follow-up question is generated and inserted
    right after the current question (capped at 3 per session)
        ↓
  Structured JSON score + feedback per persona
        ↓
All responses stored in st.session_state across the full session
        ↓
On completion: session is saved to SQLite (viva_panel_history.db)
        ↓
Results dashboard: metrics, trend chart, editable table, expandable feedback
        ↓
History tab (sidebar): past sessions table + score trend across sessions
```

See `system_design.md` for the full Mermaid diagram and data flow notes.

## → Tech Stack
| Layer | Tool |
|---|---|
| UI | Streamlit |
| AI | Gemini API via the official `google-genai` SDK (text + audio + vision) |
| Data | Pandas |
| State | `st.session_state` |
| History | SQLite (single file, `db.py`) |
| Deployment | Streamlit Community Cloud |

**Note on SDK:** this project uses the current `google-genai` package
(`from google import genai`), not the deprecated `google.generativeai` package
which Google sunset in late 2025.

## → Setup

```bash
git clone <this-repo-url>
cd viva-panel-simulator
pip install -r requirements.txt
streamlit run app.py
```

You'll need a Gemini API key — get one from [Google AI Studio](https://aistudio.google.com/apikey)
and paste it into the sidebar when the app launches. The key is used only for your
session and is never stored.

For Streamlit Community Cloud deployment, add your key under **App settings → Secrets**
instead of a `.env` file:
```toml
GEMINI_API_KEY = "your-key-here"
```

## → Project Structure

```
viva-panel-simulator/
├── app.py                   # main Streamlit app — UI + session flow + history view
├── prompts.py                # persona system prompts + prompt builders
├── gemini_client.py          # Gemini API wrapper (google-genai SDK, audio/vision calls)
├── db.py                     # SQLite layer for interview history
├── viva_panel_history.db     # created automatically on first run (not committed)
├── requirements.txt
├── system_design.md          # architecture diagram + data flow doc
└── README.md
```

## → Adaptive Follow-Up Questions
The Technical Panelist persona doesn't just score your answer — it also judges whether
the answer was thorough enough. If it was vague or surface-level, Gemini generates a
targeted follow-up question and it gets inserted right after the current question in
the interview queue. This is capped at 3 follow-ups per session so the interview can't
grow unbounded.
