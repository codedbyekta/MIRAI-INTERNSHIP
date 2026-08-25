"""
Viva Panel Simulator
A multi-persona AI mock interview app built with Streamlit + Gemini
(google-genai SDK).

Features:
- AI-generated interview questions
- Audio answer recording + transcription
- Optional camera posture analysis
- HR, Technical, and Mentor evaluation
- Adaptive technical follow-up questions
- SQLite interview history
- Graceful handling of temporary Gemini API errors
- Fresh camera + microphone for every question
"""

import uuid

import streamlit as st
import pandas as pd

from prompts import (
    get_question_generator_prompt,
    get_evaluation_prompt,
    get_technical_evaluation_prompt,
    PERSONAS,
)

from gemini_client import (
    configure_gemini,
    generate_questions,
    transcribe_audio,
    analyze_posture,
    evaluate_answer,
    evaluate_technical_with_followup,
)

import db


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Viva Panel Simulator",
    page_icon="🎤",
    layout="wide",
)

db.init_db()

MAX_FOLLOWUPS_PER_SESSION = 3


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "stage": "setup",
    "view": "interview",

    "role": "",

    # List of question dictionaries:
    #
    # {
    #     "id": "...",
    #     "text": "...",
    #     "is_followup": False
    # }
    #
    "questions": [],

    "current_q_index": 0,

    "records": [],

    "followups_used": 0,

    "api_configured": False,

    "saved_to_db": False,

    # Prevent duplicate processing
    "processed_audio_hash": None,
}


for key, value in defaults.items():

    if key not in st.session_state:

        st.session_state[key] = value


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_question(text, is_followup=False):
    """
    Create a question object with a unique ID.

    The unique ID is extremely important because Streamlit
    widgets such as st.audio_input and st.camera_input
    maintain their state using widget keys.
    """

    return {
        "id": str(uuid.uuid4()),
        "text": text,
        "is_followup": is_followup,
    }


def reset_session():
    """
    Completely reset the interview session.
    """

    for key, value in defaults.items():

        st.session_state[key] = value


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Setup")

    # --------------------------------------------------------
    # GEMINI API KEY
    # --------------------------------------------------------

    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        help="Used only for this session and not stored.",
    )

    if api_key:

        if not st.session_state.api_configured:

            try:

                configure_gemini(api_key)

                st.session_state.api_configured = True

                st.success("Gemini configured ✅")

            except Exception as e:

                st.session_state.api_configured = False

                st.error(
                    f"Gemini configuration failed: {e}"
                )

        else:

            st.success("Gemini configured ✅")

    # --------------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------------

    st.divider()

    st.session_state.view = st.radio(
        "Navigate",
        ["interview", "history"],
        format_func=str.title,
    )

    # --------------------------------------------------------
    # RESTART
    # --------------------------------------------------------

    st.divider()

    if st.button("🔄 Restart Session"):

        reset_session()

        st.rerun()


# ============================================================
# HISTORY VIEW
# ============================================================

if st.session_state.view == "history":

    st.title("📚 Interview History")

    interviews = db.get_all_interviews()

    # --------------------------------------------------------
    # NO HISTORY
    # --------------------------------------------------------

    if not interviews:

        st.info(
            "No past interviews yet. "
            "Complete a session to see it here."
        )

    else:

        # ----------------------------------------------------
        # HISTORY TABLE
        # ----------------------------------------------------

        hist_df = pd.DataFrame(interviews)[
            [
                "id",
                "created_at",
                "role",
                "question_count",
                "hr_avg",
                "technical_avg",
                "mentor_avg",
                "overall_avg",
            ]
        ]

        hist_df.columns = [
            "ID",
            "Date",
            "Role",
            "Questions",
            "HR Avg",
            "Technical Avg",
            "Mentor Avg",
            "Overall Avg",
        ]

        st.dataframe(
            hist_df,
            use_container_width=True,
        )

        st.divider()

        # ----------------------------------------------------
        # TREND
        # ----------------------------------------------------

        st.subheader("📈 Trend Across Sessions")

        trend_df = pd.DataFrame(
            interviews
        ).set_index(
            "created_at"
        )[
            [
                "hr_avg",
                "technical_avg",
                "mentor_avg",
            ]
        ]

        trend_df.columns = [
            "HR",
            "Technical",
            "Mentor",
        ]

        st.line_chart(trend_df)

        st.divider()

        # ----------------------------------------------------
        # SESSION DETAILS
        # ----------------------------------------------------

        selected_id = st.selectbox(
            "View a past session in detail",
            [item["id"] for item in interviews],
        )

        if selected_id:

            detail = db.get_interview_detail(
                selected_id
            )

            st.caption(
                f"Role: {detail['role']} — "
                f"{detail['created_at']}"
            )

            for i, record in enumerate(
                detail["records"]
            ):

                with st.expander(
                    f"Q{i + 1}: {record['question']}"
                ):

                    st.markdown(
                        f"**Answer:** "
                        f"{record['answer']}"
                    )

                    for (
                        persona_name,
                        evaluation,
                    ) in record[
                        "evaluations"
                    ].items():

                        st.markdown(
                            f"**{persona_name}** — "
                            f"{evaluation['score']}/10 — "
                            f"{evaluation['feedback']}"
                        )

    st.stop()


# ============================================================
# STAGE 1 — SETUP
# ============================================================

if st.session_state.stage == "setup":

    st.title("🎤 Viva Panel Simulator")

    st.caption(
        "Multi-persona AI mock interview — "
        "HR, Technical Panelist & Mentor grade your answers. "
        "The Technical Panelist can also ask adaptive "
        "follow-up questions."
    )

    # --------------------------------------------------------
    # SETUP FORM
    # --------------------------------------------------------

    with st.form("setup_form"):

        role = st.text_input(
            "Target Role",
            placeholder="SDE Intern / AI-ML Engineer",
        )

        num_q = st.slider(
            "Number of Questions",
            min_value=3,
            max_value=7,
            value=5,
        )

        submitted = st.form_submit_button(
            "Generate Interview →"
        )

    # --------------------------------------------------------
    # GENERATE QUESTIONS
    # --------------------------------------------------------

    if submitted:

        if not st.session_state.api_configured:

            st.error(
                "⚠️ Add your Gemini API key "
                "in the sidebar first."
            )

        elif not role.strip():

            st.error(
                "⚠️ Enter a target role."
            )

        else:

            try:

                with st.spinner(
                    "🤖 Generating tailored questions..."
                ):

                    prompt = get_question_generator_prompt(
                        role,
                        num_q,
                    )

                    generated_questions = generate_questions(
                        prompt
                    )

                # --------------------------------------------
                # Validate response
                # --------------------------------------------

                if not generated_questions:

                    st.error(
                        "Gemini did not return any questions. "
                        "Please try again."
                    )

                else:

                    # ----------------------------------------
                    # Convert questions into objects
                    # with unique IDs.
                    # ----------------------------------------

                    question_objects = []

                    for question in generated_questions:

                        question_objects.append(
                            create_question(
                                question,
                                is_followup=False,
                            )
                        )

                    # ----------------------------------------
                    # Save interview state
                    # ----------------------------------------

                    st.session_state.role = role

                    st.session_state.questions = (
                        question_objects
                    )

                    st.session_state.stage = "interview"

                    st.session_state.current_q_index = 0

                    st.session_state.records = []

                    st.session_state.followups_used = 0

                    st.session_state.saved_to_db = False

                    st.session_state.processed_audio_hash = None

                    st.rerun()

            except Exception as e:

                st.error(
                    "❌ Could not generate interview questions."
                )

                st.warning(
                    "Gemini may be temporarily busy. "
                    "Please wait a few seconds and try again."
                )

                st.caption(
                    f"Technical error: {e}"
                )


# ============================================================
# STAGE 2 — INTERVIEW
# ============================================================

elif st.session_state.stage == "interview":

    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------

    if not st.session_state.questions:

        st.error(
            "No interview questions found. "
            "Please restart the session."
        )

        st.stop()

    # --------------------------------------------------------
    # CURRENT QUESTION INDEX
    # --------------------------------------------------------

    idx = st.session_state.current_q_index

    total = len(
        st.session_state.questions
    )

    # --------------------------------------------------------
    # SAFETY CHECK FOR INDEX
    # --------------------------------------------------------

    if idx >= total:

        st.session_state.stage = "results"

        st.rerun()

    # --------------------------------------------------------
    # CURRENT QUESTION OBJECT
    # --------------------------------------------------------

    current_question_data = (
        st.session_state.questions[idx]
    )

    current_question = (
        current_question_data["text"]
    )

    current_question_id = (
        current_question_data["id"]
    )

    is_followup = (
        current_question_data["is_followup"]
    )

    # --------------------------------------------------------
    # PROGRESS
    # --------------------------------------------------------

    progress_value = (
        (idx + 1) / total
    )

    st.progress(
        progress_value,
        text=f"Question {idx + 1} of {total}",
    )

    # --------------------------------------------------------
    # QUESTION TYPE
    # --------------------------------------------------------

    if is_followup:

        st.info(
            "⚡ Adaptive Technical Follow-up"
        )

    # --------------------------------------------------------
    # QUESTION
    # --------------------------------------------------------

    st.subheader(
        f"Q{idx + 1}: {current_question}"
    )

    # ========================================================
    # CAMERA + AUDIO
    # ========================================================

    col1, col2 = st.columns(2)

    # --------------------------------------------------------
    # CAMERA
    # --------------------------------------------------------

    with col1:

        photo = st.camera_input(
            "📸 Capture your posture "
            "(optional but recommended)",

            # UNIQUE KEY
            #
            # This is based on the question's UUID,
            # NOT the index.
            #
            # Therefore even if a follow-up question
            # is inserted, the widgets never collide.

            key=f"camera_{current_question_id}",
        )

    # --------------------------------------------------------
    # AUDIO
    # --------------------------------------------------------

    with col2:

        audio = st.audio_input(
            "🎙️ Record your answer",

            # UNIQUE KEY

            key=f"audio_{current_question_id}",
        )

    # ========================================================
    # SUBMIT BUTTON
    # ========================================================

    with st.form(
        key=f"answer_form_{current_question_id}"
    ):

        submitted = st.form_submit_button(
            "Submit Answer →"
        )

    # ========================================================
    # PROCESS ANSWER
    # ========================================================

    if submitted:

        # ----------------------------------------------------
        # AUDIO REQUIRED
        # ----------------------------------------------------

        if audio is None:

            st.error(
                "⚠️ Please record an answer "
                "before submitting."
            )

        else:

            audio_bytes = audio.getvalue()

            audio_hash = hash(
                audio_bytes
            )

            # ------------------------------------------------
            # DUPLICATE PROTECTION
            # ------------------------------------------------

            if (
                audio_hash
                == st.session_state.processed_audio_hash
            ):

                st.warning(
                    "This answer was already processed."
                )

            else:

                # ====================================================
                # STEP 1 — TRANSCRIPTION
                # ====================================================

                try:

                    with st.spinner(
                        "🎙️ Transcribing your answer..."
                    ):

                        answer_text = transcribe_audio(
                            audio_bytes
                        )

                except Exception as e:

                    st.error(
                        "❌ Audio transcription failed."
                    )

                    st.warning(
                        "Gemini may be temporarily unavailable. "
                        "Please wait a few seconds and try again."
                    )

                    st.caption(
                        f"Technical error: {e}"
                    )

                    st.stop()

                # ------------------------------------------------
                # EMPTY TRANSCRIPTION
                # ------------------------------------------------

                if not answer_text.strip():

                    st.error(
                        "Gemini returned an empty transcription. "
                        "Please record your answer again."
                    )

                    st.stop()

                # ====================================================
                # STEP 2 — POSTURE ANALYSIS
                # ====================================================

                posture_note = ""

                if photo is not None:

                    try:

                        with st.spinner(
                            "📸 Reading posture cue..."
                        ):

                            posture_note = analyze_posture(
                                photo.getvalue()
                            )

                    except Exception as e:

                        # ----------------------------------------
                        # POSTURE IS OPTIONAL
                        # ----------------------------------------

                        posture_note = (
                            "Posture analysis temporarily "
                            "unavailable."
                        )

                        st.warning(
                            "⚠️ Posture analysis is temporarily "
                            "unavailable, but your interview "
                            "will continue normally."
                        )

                        print(
                            f"Posture analysis error: {e}"
                        )

                # ====================================================
                # STEP 3 — PERSONA EVALUATIONS
                # ====================================================

                evaluations = {}

                try:

                    with st.spinner(
                        "🧠 Panel is deliberating..."
                    ):

                        for (
                            persona_name,
                            persona_prompt,
                        ) in PERSONAS.items():

                            # ------------------------------------
                            # TECHNICAL PANELIST
                            # ------------------------------------

                            if (
                                persona_name
                                == "Technical Panelist"
                            ):

                                eval_prompt = (
                                    get_technical_evaluation_prompt(
                                        current_question,
                                        answer_text,
                                        st.session_state.role,
                                    )
                                )

                                evaluations[
                                    persona_name
                                ] = (
                                    evaluate_technical_with_followup(
                                        eval_prompt
                                    )
                                )

                            # ------------------------------------
                            # HR / MENTOR
                            # ------------------------------------

                            else:

                                eval_prompt = (
                                    get_evaluation_prompt(
                                        persona_prompt,
                                        current_question,
                                        answer_text,
                                        st.session_state.role,
                                    )
                                )

                                evaluations[
                                    persona_name
                                ] = evaluate_answer(
                                    eval_prompt
                                )

                except Exception as e:

                    st.error(
                        "❌ The AI panel could not "
                        "evaluate your answer."
                    )

                    st.warning(
                        "Gemini may be experiencing high demand. "
                        "Please wait a few seconds and try again."
                    )

                    st.caption(
                        f"Technical error: {e}"
                    )

                    st.stop()

                # ====================================================
                # STEP 4 — SAVE RECORD
                # ====================================================

                st.session_state.records.append(
                    {
                        "question": current_question,
                        "answer": answer_text,
                        "posture_note": posture_note,
                        "evaluations": evaluations,
                    }
                )

                # ====================================================
                # STEP 5 — ADAPTIVE FOLLOW-UP
                # ====================================================

                tech_eval = evaluations.get(
                    "Technical Panelist",
                    {},
                )

                follow_up_needed = tech_eval.get(
                    "follow_up_needed",
                    False,
                )

                next_question = tech_eval.get(
                    "next_question",
                    "",
                )

                # --------------------------------------------
                # Add adaptive follow-up
                # --------------------------------------------

                if (
                    follow_up_needed
                    and next_question
                    and st.session_state.followups_used
                    < MAX_FOLLOWUPS_PER_SESSION
                ):

                    followup_question = create_question(
                        next_question,
                        is_followup=True,
                    )

                    # Insert immediately after
                    # current question.

                    st.session_state.questions.insert(
                        idx + 1,
                        followup_question,
                    )

                    st.session_state.followups_used += 1

                # ====================================================
                # STEP 6 — MOVE TO NEXT QUESTION
                # ====================================================

                next_index = idx + 1

                if (
                    next_index
                    < len(
                        st.session_state.questions
                    )
                ):

                    # --------------------------------------------
                    # NEXT QUESTION EXISTS
                    # --------------------------------------------

                    st.session_state.current_q_index = (
                        next_index
                    )

                else:

                    # --------------------------------------------
                    # INTERVIEW FINISHED
                    # --------------------------------------------

                    st.session_state.stage = "results"

                # ------------------------------------------------
                # IMPORTANT
                # ------------------------------------------------
                #
                # We DO NOT reuse the old audio/camera widgets.
                #
                # st.rerun() causes Streamlit to render the
                # next question.
                #
                # Because every question has its own UUID:
                #
                # Q1:
                # camera_<uuid1>
                # audio_<uuid1>
                #
                # Q2:
                # camera_<uuid2>
                # audio_<uuid2>
                #
                # Follow-up:
                # camera_<uuid3>
                # audio_<uuid3>
                #
                # Therefore every question gets a fresh
                # microphone and camera widget.
                # ------------------------------------------------

                st.session_state.processed_audio_hash = None

                st.rerun()


# ============================================================
# STAGE 3 — RESULTS
# ============================================================

elif st.session_state.stage == "results":

    st.title("📊 Interview Scorecard")

    st.caption(
        f"Role: {st.session_state.role}"
    )

    # --------------------------------------------------------
    # FOLLOW-UP INFO
    # --------------------------------------------------------

    if st.session_state.followups_used:

        st.caption(
            f"⚡ {st.session_state.followups_used} "
            "adaptive follow-up question(s) were asked "
            "based on your answers."
        )

    records = st.session_state.records

    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------

    if not records:

        st.warning(
            "No interview records found."
        )

        st.stop()

    # ========================================================
    # AGGREGATE SCORES
    # ========================================================

    persona_avgs = {}

    for persona_name in PERSONAS:

        scores = [
            record["evaluations"][persona_name]["score"]
            for record in records
            if persona_name in record["evaluations"]
        ]

        if scores:

            persona_avgs[persona_name] = (
                sum(scores) / len(scores)
            )

        else:

            persona_avgs[persona_name] = 0

    # ========================================================
    # SAVE TO DATABASE
    # ========================================================

    if not st.session_state.saved_to_db:

        try:

            db.save_interview(
                st.session_state.role,
                records,
                persona_avgs,
            )

            st.session_state.saved_to_db = True

        except Exception as e:

            st.error(
                "Could not save this interview "
                "to history."
            )

            st.caption(
                f"Database error: {e}"
            )

    # ========================================================
    # SCORE CARDS
    # ========================================================

    cols = st.columns(
        len(persona_avgs)
    )

    for (
        col,
        (
            persona_name,
            average,
        ),
    ) in zip(
        cols,
        persona_avgs.items(),
    ):

        col.metric(
            persona_name,
            f"{average:.1f} / 10",
        )

    st.divider()

    # ========================================================
    # PERFORMANCE CHART
    # ========================================================

    st.subheader(
        "📈 Performance Across Questions"
    )

    trend_rows = []

    for i, record in enumerate(records):

        row = {
            "Question": f"Q{i + 1}"
        }

        for persona_name in PERSONAS:

            row[persona_name] = (
                record["evaluations"]
                [persona_name]
                ["score"]
            )

        trend_rows.append(row)

    trend_df = (
        pd.DataFrame(trend_rows)
        .set_index("Question")
    )

    st.line_chart(
        trend_df
    )

    st.divider()

    # ========================================================
    # SCORE BREAKDOWN
    # ========================================================

    st.subheader(
        "📋 Score Breakdown"
    )

    table_rows = []

    for i, record in enumerate(records):

        table_rows.append(
            {
                "Q#": i + 1,

                "Question": record[
                    "question"
                ],

                "HR Score": (
                    record["evaluations"]
                    ["HR Manager"]
                    ["score"]
                ),

                "Technical Score": (
                    record["evaluations"]
                    ["Technical Panelist"]
                    ["score"]
                ),

                "Mentor Score": (
                    record["evaluations"]
                    ["Mentor"]
                    ["score"]
                ),
            }
        )

    st.data_editor(
        pd.DataFrame(table_rows),
        use_container_width=True,
        disabled=[
            "Q#",
            "Question",
        ],
    )

    st.divider()

    # ========================================================
    # DETAILED FEEDBACK
    # ========================================================

    st.subheader(
        "📝 Detailed Feedback"
    )

    for i, record in enumerate(records):

        with st.expander(
            f"Q{i + 1}: {record['question']}"
        ):

            # ------------------------------------------------
            # ANSWER
            # ------------------------------------------------

            st.markdown(
                f"**Your answer:** "
                f"{record['answer']}"
            )

            # ------------------------------------------------
            # POSTURE
            # ------------------------------------------------

            if record["posture_note"]:

                st.markdown(
                    f"**📸 Posture note:** "
                    f"{record['posture_note']}"
                )

            # ------------------------------------------------
            # PERSONA FEEDBACK
            # ------------------------------------------------

            for (
                persona_name,
                evaluation,
            ) in record[
                "evaluations"
            ].items():

                st.markdown(
                    f"### {persona_name}"
                )

                st.markdown(
                    f"**Score:** "
                    f"{evaluation['score']}/10"
                )

                st.markdown(
                    f"- ✅ **Strengths:** "
                    f"{evaluation['strengths']}"
                )

                st.markdown(
                    f"- ⚠️ **Gaps:** "
                    f"{evaluation['gaps']}"
                )

                st.markdown(
                    f"- 💬 **Feedback:** "
                    f"{evaluation['feedback']}"
                )

    # ========================================================
    # SUCCESS
    # ========================================================

    if st.session_state.saved_to_db:

        st.success(
            "✅ This session has been saved to your history. "
            "Check the sidebar → History tab anytime."
        )

    # ========================================================
    # NEW INTERVIEW
    # ========================================================

    st.divider()

    if st.button(
        "🔄 Start New Interview"
    ):

        reset_session()

        st.rerun()