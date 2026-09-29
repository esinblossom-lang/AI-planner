import html
import json
import os
import re
import uuid
from datetime import date

import streamlit as st


# =========================================================
# SETTINGS
# =========================================================

MODEL = "gemini-2.5-flash"

PRIORITIES = ["High", "Medium", "Low"]

PRIORITY_RANK = {
    "High": 0,
    "Medium": 1,
    "Low": 2
}

PREFIXES = ("all", "active", "done")

SORT_OPTIONS = [
    "Order added",
    "Priority",
    "Due date"
]


# =========================================================
# PAGE SETTINGS
# =========================================================

st.set_page_config(
    page_title="My To-Do List",
    page_icon="💜",
    layout="centered"
)


# =========================================================
# COLOUR PALETTE & STYLING
# =========================================================

st.markdown("""
<style>

    /* =========================
       MAIN APP
       ========================= */

    .stApp {
        background-color: #F5CDD0;
    }


    /* =========================
       HEADINGS
       ========================= */

    h1, h2, h3 {
        color: #826E8B !important;
    }


    /* =========================
       HEADER
       ========================= */

    .header {
        background: linear-gradient(
            135deg,
            #826E8B,
            #EB6E9B
        );

        padding: 35px 25px;
        border-radius: 22px;
        text-align: center;
        color: white;
        margin-bottom: 25px;

        box-shadow:
            0 8px 25px rgba(130, 110, 139, 0.25);
    }

    .header h1 {
        color: white !important;
        font-size: 42px;
        margin-bottom: 5px;
    }

    .header p {
        color: white;
        font-size: 17px;
        margin: 0;
    }


    /* =========================
       STATISTICS CARDS
       ========================= */

    .stat-card {
        background-color: white;
        padding: 20px;
        border-radius: 18px;
        text-align: center;

        border: 2px solid #F4B3C7;

        box-shadow:
            0 5px 15px rgba(130, 110, 139, 0.12);
    }

    .stat-number {
        font-size: 30px;
        font-weight: bold;
        color: #826E8B;
    }

    .stat-label {
        color: #826E8B;
        font-size: 14px;
        font-weight: 600;
    }


    /* =========================
       TEXT INPUTS
       ========================= */

    .stTextInput input,
    .stTextArea textarea {
        border: 2px solid #E69CBA;
        border-radius: 12px;
        background-color: white;
    }

    .stTextInput input:focus,
    .stTextArea textarea:focus {
        border-color: #EB6E9B;
        box-shadow: 0 0 0 2px #F4B3C7;
    }

    .stTextInput input,
    .stTextArea textarea,
    .stDateInput input {
        color: #5A4A66 !important;
    }

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder,
    .stDateInput input::placeholder {
        color: #B58AA5 !important;
        opacity: 1;
    }


    /* =========================
       LABELS
       ========================= */

    .stSelectbox label p,
    .stDateInput label p,
    .stTextArea label p,
    .stTextInput label p,
    .stCheckbox label p {
        color: #826E8B !important;
        font-weight: 600;
    }

    .stSelectbox [data-baseweb="select"] div {
        color: #5A4A66;
    }


    /* =========================
       BUTTONS
       ========================= */

    .stButton > button,
    [data-testid="stPopover"] button,
    .stFormSubmitButton > button {
        background-color: #EB6E9B;
        color: white;

        border: none;
        border-radius: 12px;

        font-weight: 600;

        padding: 0.6rem 1rem;
    }

    .stButton > button:hover,
    [data-testid="stPopover"] button:hover,
    .stFormSubmitButton > button:hover {
        background-color: #826E8B;
        color: white;
    }


    /* =========================
       TABS
       ========================= */

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        color: #826E8B;
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        color: #EB6E9B !important;
    }


    /* =========================
       TASK NOTES
       ========================= */

    .task-note {
        background-color: #F5CDD0;

        border-left: 3px solid #E69CBA;

        padding: 9px 12px;

        margin: 4px 0 10px 32px;

        border-radius: 8px;

        color: #826E8B;

        font-size: 14px;

        line-height: 1.5;
    }


    /* =========================
       PRIORITY + DUE DATE
       ========================= */

    .badge {
        display: inline-block;

        padding: 2px 10px;

        border-radius: 20px;

        font-size: 12px;

        font-weight: 700;
    }

    .badge-high {
        background-color: #EB6E9B;
        color: white;
    }

    .badge-medium {
        background-color: #826E8B;
        color: white;
    }

    .badge-low {
        background-color: #F4B3C7;
        color: #826E8B;
    }

    .due {
        font-size: 12px;
        font-weight: 600;
        color: #826E8B;
        margin-left: 6px;
    }

    .due.overdue {
        color: #C0392B;
    }


    /* =========================
       AI PLANNER
       ========================= */

    .ai-box {
        background: linear-gradient(
            135deg,
            #F4B3C7,
            #E69CBA
        );

        padding: 22px;

        border-radius: 20px;

        margin-top: 30px;

        border: 2px solid #E69CBA;
    }

    .ai-box h2 {
        color: #826E8B !important;
    }

    .ai-box p {
        color: #826E8B;
    }


    /* =========================
       PROGRESS BAR
       ========================= */

    .stProgress > div > div > div > div {
        background-color: #EB6E9B;
    }

</style>
""", unsafe_allow_html=True)


# =========================================================
# HELPERS
# =========================================================

def parse_date(value):
    """Convert YYYY-MM-DD text into a date."""

    if not value:
        return None

    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(str(value))

    except (TypeError, ValueError):
        return None


def md_escape(text):
    """Prevent task text from being interpreted as Markdown."""

    return re.sub(
        r"([\\`*_{}\[\]()#+\-.!|~<>$:])",
        r"\\\1",
        str(text)
    )


# =========================================================
# TASK ACTIONS
# =========================================================

def add_task(
    name,
    note="",
    priority="Medium",
    due=None
):
    """Add a task to the current Streamlit session."""

    st.session_state.tasks.append({

        "id": uuid.uuid4().hex,

        "name": name.strip(),

        "note": note.strip(),

        "completed": False,

        "priority": (
            priority
            if priority in PRIORITIES
            else "Medium"
        ),

        "due": (
            due.isoformat()
            if isinstance(due, date)
            else None
        )
    })


def toggle_task(task_id, key):
    """Update whether a task is completed."""

    new_value = st.session_state[key]

    for task in st.session_state.tasks:

        if task["id"] == task_id:

            task["completed"] = new_value

            break


    # Synchronize checkbox states across tabs.

    for prefix in PREFIXES:

        checkbox_key = (
            f"{prefix}_{task_id}"
        )

        st.session_state[
            checkbox_key
        ] = new_value


def delete_task(task_id):
    """Delete one task."""

    st.session_state.tasks = [

        task

        for task in st.session_state.tasks

        if task["id"] != task_id
    ]


def delete_completed():
    """Delete all completed tasks."""

    st.session_state.tasks = [

        task

        for task in st.session_state.tasks

        if not task["completed"]
    ]


def update_task(
    task_id,
    name,
    note,
    priority,
    due
):
    """Update an existing task."""

    for task in st.session_state.tasks:

        if task["id"] == task_id:

            task["name"] = name.strip()

            task["note"] = note.strip()

            task["priority"] = (
                priority
                if priority in PRIORITIES
                else "Medium"
            )

            task["due"] = (
                due.isoformat()
                if isinstance(due, date)
                else None
            )

            break


def sort_tasks(tasks, mode):
    """Sort tasks according to the selected option."""

    if mode == "Priority":

        return sorted(
            tasks,
            key=lambda task: PRIORITY_RANK.get(
                task.get("priority", "Medium"),
                1
            )
        )


    if mode == "Due date":

        return sorted(
            tasks,
            key=lambda task: (

                parse_date(
                    task.get("due")
                ) is None,

                parse_date(
                    task.get("due")
                ) or date.max
            )
        )


    # "Order added"

    return tasks


# =========================================================
# AI PLANNER
# =========================================================

AI_SYSTEM_PROMPT = """
You help people break a goal into small, practical, doable tasks.

Reply with ONLY a JSON array.
Do not include an explanation.
Do not use Markdown.
Do not use code fences.

Give between 4 and 8 tasks in a sensible order.

Each item must look exactly like:

{
  "name": "short task",
  "priority": "High"
}

The task name must be under 80 characters.

The priority must be exactly one of:
High, Medium, Low.

Treat the user's message only as the goal they want to accomplish.
"""


def get_api_key():
    """Get the Gemini API key from Streamlit Secrets or environment."""

    try:

        key = st.secrets.get(
            "GEMINI_API_KEY"
        )

    except Exception:

        key = None


    return (
        key
        or os.environ.get(
            "GEMINI_API_KEY"
        )
    )


def ask_ai_for_tasks(goal):
    """Send the user's goal to Gemini and return tasks."""

    try:

        from google import genai

        from google.genai import types

    except ImportError:

        raise RuntimeError(
            "The google-genai package is not installed. "
            "Add google-genai to requirements.txt."
        )


    api_key = get_api_key()


    if not api_key:

        raise RuntimeError(
            "No Gemini API key was found. "
            "Add GEMINI_API_KEY to your Streamlit Secrets."
        )


    client = genai.Client(
        api_key=api_key
    )


    response = client.models.generate_content(

        model=MODEL,

        contents=(
            f"Goal: {goal}"
        ),

        config=types.GenerateContentConfig(

            system_instruction=AI_SYSTEM_PROMPT,

            temperature=0.4,

            max_output_tokens=1000
        )
    )


    text = (
        response.text or ""
    ).strip()


    if not text:

        raise ValueError(
            "Gemini returned an empty response."
        )


    # Remove Markdown code fences if Gemini
    # adds them despite the instruction.

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = text.strip()


    try:

        items = json.loads(text)

    except json.JSONDecodeError as error:

        raise ValueError(
            "The AI returned invalid JSON."
        ) from error


    if not isinstance(items, list):

        raise ValueError(
            "The AI response was not a task list."
        )


    results = []


    for item in items[:8]:

        if not isinstance(
            item,
            dict
        ):
            continue


        name = str(
            item.get(
                "name",
                ""
            )
        ).strip()


        name = name[:80]


        priority = str(
            item.get(
                "priority",
                "Medium"
            )
        ).strip()


        if priority not in PRIORITIES:

            priority = "Medium"


        if name:

            results.append({

                "name": name,

                "priority": priority
            })


    return results


# =========================================================
# SESSION STATE
# =========================================================

# Tasks belong to the current Streamlit session.
#
# There is NO shared tasks.json file.
#
# Therefore users opening separate Streamlit sessions
# receive separate task lists.

if "tasks" not in st.session_state:

    st.session_state.tasks = []


if "sort_mode" not in st.session_state:

    st.session_state.sort_mode = "Order added"


# =========================================================
# HEADER
# =========================================================

st.markdown("""
<div class="header">

    <h1>💜 My To-Do List</h1>

    <p>
        Get organised. Get things done. ✨
    </p>

</div>
""", unsafe_allow_html=True)


# =========================================================
# STATISTICS
# =========================================================

total_tasks = len(
    st.session_state.tasks
)


completed_count = sum(

    1

    for task in st.session_state.tasks

    if task["completed"]
)


active_count = (
    total_tasks - completed_count
)


col1, col2 = st.columns(2)


with col1:

    st.markdown(

        f"""
        <div class="stat-card">

            <div class="stat-number">
                {total_tasks}
            </div>

            <div class="stat-label">
                📋 TOTAL TASKS
            </div>

        </div>
        """,

        unsafe_allow_html=True
    )


with col2:

    st.markdown(

        f"""
        <div class="stat-card">

            <div class="stat-number">
                {completed_count}
            </div>

            <div class="stat-label">
                ✅ COMPLETED
            </div>

        </div>
        """,

        unsafe_allow_html=True
    )


# =========================================================
# ADD TASK
# =========================================================

st.markdown(
    "## ➕ Add a Task"
)


with st.form(
    "add_task_form",
    clear_on_submit=True
):

    # Task name

    new_task = st.text_input(

        "Task",

        placeholder=(
            "What do you need to get done?"
        ),

        label_visibility="collapsed"
    )


    # Task note

    new_note = st.text_area(

        "Note",

        placeholder=(
            "📝 Add a note about this task "
            "(optional)..."
        ),

        label_visibility="collapsed",

        height=90
    )


    form_col1, form_col2 = st.columns(2)


    # Priority

    with form_col1:

        new_priority = st.selectbox(

            "Priority",

            PRIORITIES,

            index=1
        )


    # Optional due date

    with form_col2:

        has_due_date = st.checkbox(
            "📅 Add a due date"
        )


        new_due = None


        if has_due_date:

            new_due = st.date_input(
                "Due date",
                value=date.today()
            )


    add_clicked = st.form_submit_button(

        "✨ Add Task",

        use_container_width=True
    )


# =========================================================
# PROCESS ADD TASK
# =========================================================

if add_clicked:

    if new_task.strip():

        add_task(

            name=new_task,

            note=new_note,

            priority=new_priority,

            due=new_due
        )


        st.toast(
            "Task added! 🎉"
        )


        st.rerun()

    else:

        st.warning(
            "Please enter a task first."
        )


# =========================================================
# TASK LIST
# =========================================================

st.markdown(
    "## 📋 Your Tasks"
)


sort_mode = st.selectbox(

    "Sort by",

    SORT_OPTIONS,

    key="sort_mode"
)


def render_task(
    task,
    prefix
):
    """Display one task."""

    task_id = task["id"]


    checkbox_key = (
        f"{prefix}_{task_id}"
    )


    # Make sure old tasks without notes
    # still work correctly.

    if "note" not in task:

        task["note"] = ""


    if "priority" not in task:

        task["priority"] = "Medium"


    if "due" not in task:

        task["due"] = None


    # Set initial checkbox state.

    if checkbox_key not in st.session_state:

        st.session_state[
            checkbox_key
        ] = task["completed"]


    with st.container(
        border=True
    ):

        c_main, c_meta, c_edit, c_delete = st.columns(

            [5, 3, 1.2, 1.2],

            vertical_alignment="center"
        )


        # =================================================
        # TASK NAME + NOTE
        # =================================================

        with c_main:

            label = md_escape(
                task["name"]
            )


            if task["completed"]:

                label = (
                    f"~~{label}~~"
                )


            st.checkbox(

                label,

                key=checkbox_key,

                on_change=toggle_task,

                args=(
                    task_id,
                    checkbox_key
                )
            )


            # ---------------------------------------------
            # NOTE
            # ---------------------------------------------

            if task.get("note", "").strip():

                safe_note = html.escape(
                    task["note"]
                )


                st.markdown(

                    f"""
                    <div class="task-note">
                        📝 {safe_note}
                    </div>
                    """,

                    unsafe_allow_html=True
                )


        # =================================================
        # PRIORITY + DUE DATE
        # =================================================

        with c_meta:

            priority = task.get(
                "priority",
                "Medium"
            )


            tags = (

                f'<span class="badge '
                f'badge-{priority.lower()}">'
                f'{html.escape(priority)}'
                f'</span>'
            )


            due = parse_date(
                task.get("due")
            )


            if due:

                overdue = (

                    not task["completed"]

                    and due < date.today()
                )


                css_class = (

                    "due overdue"

                    if overdue

                    else "due"
                )


                prefix_icon = (

                    "⚠️ "

                    if overdue

                    else "📅 "
                )


                tags += (

                    f'<span class="{css_class}">'

                    f'{prefix_icon}'

                    f'{due.strftime("%d %b %Y")}'

                    f'</span>'
                )


            st.markdown(

                tags,

                unsafe_allow_html=True
            )


        # =================================================
        # EDIT TASK
        # =================================================

        with c_edit:

            with st.popover("✏️"):

                with st.form(

                    f"edit_form_{prefix}_{task_id}"
                ):

                    edit_name = st.text_input(

                        "Task",

                        value=task["name"]
                    )


                    edit_note = st.text_area(

                        "📝 Note",

                        value=task.get(
                            "note",
                            ""
                        ),

                        placeholder=(
                            "Add a note about this task..."
                        ),

                        height=100
                    )


                    edit_priority = st.selectbox(

                        "Priority",

                        PRIORITIES,

                        index=PRIORITIES.index(
                            task.get(
                                "priority",
                                "Medium"
                            )
                        )
                    )


                    existing_due = parse_date(
                        task.get("due")
                    )


                    edit_has_due = st.checkbox(

                        "📅 Add a due date",

                        value=(
                            existing_due
                            is not None
                        )
                    )


                    edit_due = None


                    if edit_has_due:

                        edit_due = st.date_input(

                            "Due date",

                            value=(
                                existing_due
                                or date.today()
                            )
                        )


                    save_clicked = (
                        st.form_submit_button(

                            "💾 Save",

                            use_container_width=True
                        )
                    )


                if save_clicked:

                    if edit_name.strip():

                        update_task(

                            task_id,

                            edit_name,

                            edit_note,

                            edit_priority,

                            edit_due
                        )


                        st.toast(
                            "Task updated! ✨"
                        )


                        st.rerun()

                    else:

                        st.warning(
                            "The task can't be empty."
                        )


        # =================================================
        # DELETE TASK
        # =================================================

        with c_delete:

            st.button(

                "🗑️",

                key=(
                    f"delete_"
                    f"{prefix}_"
                    f"{task_id}"
                ),

                on_click=delete_task,

                args=(task_id,)
            )


# =========================================================
# SORT TASKS
# =========================================================

all_sorted = sort_tasks(

    st.session_state.tasks,

    sort_mode
)


active_sorted = [

    task

    for task in all_sorted

    if not task["completed"]
]


done_sorted = [

    task

    for task in all_sorted

    if task["completed"]
]


# =========================================================
# TABS
# =========================================================

tab_all, tab_active, tab_completed = st.tabs(

    [

        f"All ({total_tasks})",

        f"Active ({active_count})",

        f"Completed ({completed_count})"
    ]
)


# =========================================================
# ALL TASKS
# =========================================================

with tab_all:

    if not all_sorted:

        st.info(
            "✨ No tasks yet. "
            "Add your first task above!"
        )

    else:

        for task in all_sorted:

            render_task(
                task,
                "all"
            )


# =========================================================
# ACTIVE TASKS
# =========================================================

with tab_active:

    if not active_sorted:

        st.success(
            "🎉 You have no active tasks!"
        )

    else:

        for task in active_sorted:

            render_task(
                task,
                "active"
            )


# =========================================================
# COMPLETED TASKS
# =========================================================

with tab_completed:

    if not done_sorted:

        st.info(
            "📭 No completed tasks yet."
        )

    else:

        for task in done_sorted:

            render_task(
                task,
                "done"
            )


# =========================================================
# PROGRESS
# =========================================================

st.markdown(
    "## 📊 Your Progress"
)


progress = (

    completed_count / total_tasks

    if total_tasks > 0

    else 0
)


st.progress(
    progress
)


st.markdown(

    f"""
    <div style="
        text-align: center;
        color: #826E8B;
        margin-top: -8px;
    ">

        <strong>{completed_count}</strong>

        of

        <strong>{total_tasks}</strong>

        tasks completed

    </div>
    """,

    unsafe_allow_html=True
)


# =========================================================
# DELETE COMPLETED TASKS
# =========================================================

if completed_count > 0:

    st.button(

        "🗑️ Delete Completed Tasks",

        use_container_width=True,

        on_click=delete_completed
    )


# =========================================================
# AI PLANNER
# =========================================================

st.markdown("""

<div class="ai-box">

    <h2>🤖 AI Planner</h2>

    <p>
        Tell your AI assistant what you want
        to accomplish, and it will break your
        goal into smaller tasks for you.
    </p>

</div>

""", unsafe_allow_html=True)


with st.form(
    "ai_planner_form"
):

    goal = st.text_input(

        "Your goal",

        placeholder=(
            "e.g. Prepare for my Python exam"
        ),

        label_visibility="collapsed"
    )


    plan_button = st.form_submit_button(

        "✨ Plan It",

        use_container_width=True
    )


# =========================================================
# PROCESS AI REQUEST
# =========================================================

if plan_button:

    if not goal.strip():

        st.warning(

            "Tell me what you want "
            "to accomplish first."
        )

    else:

        try:

            with st.spinner(
                "Planning your tasks... 🤖"
            ):

                planned = ask_ai_for_tasks(
                    goal.strip()
                )


        except RuntimeError as error:

            st.error(
                str(error)
            )


        except ValueError as error:

            st.error(
                str(error)
            )


        except Exception as error:

            st.error(

                "Something went wrong "
                f"talking to the AI: {error}"
            )


        else:

            if planned:

                for item in planned:

                    add_task(

                        name=item["name"],

                        note="",

                        priority=item["priority"],

                        due=None
                    )


                st.toast(

                    f"Added {len(planned)} "
                    f"tasks! 🎉"
                )


                st.rerun()


            else:

                st.warning(

                    "The AI didn't come back "
                    "with any tasks. Try again."
                )
