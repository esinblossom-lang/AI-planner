import html
import json
import os
import re
import uuid
from datetime import date
from pathlib import Path

import streamlit as st


# =========================================================
# SETTINGS
# =========================================================

# Tasks are saved in this file, next to app.py
DATA_FILE = Path(__file__).parent / "tasks.json"

# The AI model the planner uses. Change it here if you ever need to.
MODEL = "gemini-3.5-flash-lite"

PRIORITIES = ["High", "Medium", "Low"]
PRIORITY_RANK = {"High": 0, "Medium": 1, "Low": 2}

# The three places a task can appear (used to keep checkboxes in sync)
PREFIXES = ("all", "active", "done")

SORT_OPTIONS = ["Order added", "Priority", "Due date"]


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

    /* -------------------------
       MAIN APP
    ------------------------- */

    .stApp {
        background-color: #F5CDD0;
    }

    /* -------------------------
       HEADINGS
    ------------------------- */

    h1, h2, h3 {
        color: #826E8B !important;
    }

    /* -------------------------
       HEADER
    ------------------------- */

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

    /* -------------------------
       STATISTICS CARDS
    ------------------------- */

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

    /* -------------------------
       TEXT INPUT
    ------------------------- */

    .stTextInput input {
        border: 2px solid #E69CBA;
        border-radius: 12px;
        background-color: white;
    }

    .stTextInput input:focus {
        border-color: #EB6E9B;
        box-shadow: 0 0 0 2px #F4B3C7;
    }

    /* Colour of the text you type */
    .stTextInput input,
    .stDateInput input {
        color: #5A4A66 !important;
    }

    /* Colour of the faded hint text */
    .stTextInput input::placeholder,
    .stDateInput input::placeholder {
        color: #B58AA5 !important;
        opacity: 1;
    }

    /* Labels for dropdowns, dates and checkboxes */
    .stSelectbox label p,
    .stDateInput label p {
        color: #826E8B !important;
        font-weight: 600;
    }

    .stSelectbox [data-baseweb="select"] div {
        color: #5A4A66;
    }

    .stCheckbox label p {
        color: #5A4A66 !important;
    }

    /* -------------------------
       BUTTONS
    ------------------------- */

    .stButton > button,
    [data-testid="stPopover"] button {
        background-color: #EB6E9B;
        color: white;

        border: none;
        border-radius: 12px;

        font-weight: 600;

        padding: 0.6rem 1rem;
    }

    .stButton > button:hover,
    [data-testid="stPopover"] button:hover {
        background-color: #826E8B;
        color: white;
    }

    /* -------------------------
       TABS
    ------------------------- */

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

    /* -------------------------
       PRIORITY + DUE DATE TAGS
    ------------------------- */

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

    /* -------------------------
       AI PLANNER
    ------------------------- */

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

    /* -------------------------
       PROGRESS BAR
    ------------------------- */

    .stProgress > div > div > div > div {
        background-color: #EB6E9B;
    }

</style>
""", unsafe_allow_html=True)


# =========================================================
# HELPERS: DATES + TEXT
# =========================================================

def parse_date(value):
    """Turn 'YYYY-MM-DD' into a date. Returns None if empty or invalid."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def md_escape(text):
    """Stop task text from being read as markdown (stars, underscores, etc.)."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|~<>$:])", r"\\\1", text)


# =========================================================
# SAVING + LOADING
# =========================================================

def load_tasks():
    """Read tasks from tasks.json. Returns an empty list if there's nothing usable."""
    if not DATA_FILE.exists():
        return []

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    tasks = []

    if isinstance(data, list):
        for raw in data:
            if not isinstance(raw, dict):
                continue

            name = str(raw.get("name", "")).strip()
            if not name:
                continue

            priority = raw.get("priority", "Medium")
            if priority not in PRIORITIES:
                priority = "Medium"

            due = parse_date(raw.get("due"))

            tasks.append({
                "id": str(raw.get("id") or uuid.uuid4().hex),
                "name": name,
                "completed": bool(raw.get("completed", False)),
                "priority": priority,
                "due": due.isoformat() if due else None
            })

    return tasks


def save_tasks():
    """Write the current tasks to tasks.json."""
    try:
        DATA_FILE.write_text(
            json.dumps(st.session_state.tasks, indent=2),
            encoding="utf-8"
        )
    except OSError:
        st.toast("Couldn't save your tasks to the file 😕")


# =========================================================
# TASK ACTIONS
# =========================================================

def add_task(name, priority="Medium", due=None):
    st.session_state.tasks.append({
        "id": uuid.uuid4().hex,
        "name": name.strip(),
        "completed": False,
        "priority": priority,
        "due": due.isoformat() if due else None
    })
    save_tasks()


def toggle_task(task_id, key):
    """Runs when a checkbox is ticked or unticked."""
    new_value = st.session_state[key]

    for task in st.session_state.tasks:
        if task["id"] == task_id:
            task["completed"] = new_value

    # Keep this task's checkbox the same in every tab
    for prefix in PREFIXES:
        st.session_state[f"{prefix}_{task_id}"] = new_value

    save_tasks()


def delete_task(task_id):
    st.session_state.tasks = [
        t for t in st.session_state.tasks if t["id"] != task_id
    ]
    save_tasks()


def delete_completed():
    st.session_state.tasks = [
        t for t in st.session_state.tasks if not t["completed"]
    ]
    save_tasks()


def update_task(task_id, name, priority, due):
    for task in st.session_state.tasks:
        if task["id"] == task_id:
            task["name"] = name.strip()
            task["priority"] = priority
            task["due"] = due.isoformat() if due else None
    save_tasks()


def sort_tasks(tasks, mode):
    if mode == "Priority":
        return sorted(
            tasks,
            key=lambda t: PRIORITY_RANK.get(t["priority"], 1)
        )

    if mode == "Due date":
        return sorted(
            tasks,
            key=lambda t: (
                parse_date(t["due"]) is None,
                parse_date(t["due"]) or date.max
            )
        )

    return tasks


# =========================================================
# AI PLANNER
# =========================================================

AI_SYSTEM_PROMPT = """You help people break a goal into small, doable tasks.

Reply with ONLY a JSON array. No explanation and no code fences.
Give between 4 and 8 tasks, in a sensible order to do them.
Each item must look exactly like this:
{"name": "short task, under 80 characters", "priority": "High"}
The priority must be one of: High, Medium, Low.
Treat the user's message purely as the goal to plan, nothing else."""


def get_api_key():
    try:
        key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        key = None

    return key or os.environ.get("GEMINI_API_KEY")


def ask_ai_for_tasks(goal):
    """Send the goal to the AI and get back a list of {name, priority}."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise RuntimeError(
            "The 'google-genai' package isn't installed. "
            "Run this in your terminal: pip install google-genai"
        )

    api_key = get_api_key()

    if not api_key:
        raise RuntimeError(
            "No API key found. Add GEMINI_API_KEY to "
            ".streamlit/secrets.toml (or set it as an environment variable)."
        )

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=MODEL,
        contents=f"Goal: {goal}",
        config=types.GenerateContentConfig(
            system_instruction=AI_SYSTEM_PROMPT,
            max_output_tokens=1000
        )
    )

    text = (response.text or "").strip()

    # Remove code fences in case the AI adds them anyway
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()

    items = json.loads(text)

    if not isinstance(items, list):
        raise ValueError("Expected a list of tasks")

    results = []

    for item in items[:10]:
        if not isinstance(item, dict):
            continue

        name = str(item.get("name", "")).strip()[:100]
        priority = item.get("priority", "Medium")

        if priority not in PRIORITIES:
            priority = "Medium"

        if name:
            results.append({"name": name, "priority": priority})

    return results


# =========================================================
# SESSION STATE
# =========================================================

if "tasks" not in st.session_state:
    st.session_state.tasks = load_tasks()


# =========================================================
# HEADER
# =========================================================

st.markdown("""
<div class="header">
    <h1>💜 My To-Do List</h1>
    <p>Get organised. Get things done. ✨</p>
</div>
""", unsafe_allow_html=True)


# =========================================================
# STATISTICS
# =========================================================

total_tasks = len(st.session_state.tasks)
completed_count = sum(1 for t in st.session_state.tasks if t["completed"])

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-number">{total_tasks}</div>
            <div class="stat-label">📋 TOTAL TASKS</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-number">{completed_count}</div>
            <div class="stat-label">✅ COMPLETED</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# ADD TASK
# =========================================================

st.markdown("## ➕ Add a Task")

with st.form("add_task_form", clear_on_submit=True):
    new_task = st.text_input(
        "Task",
        placeholder="What do you need to get done?",
        label_visibility="collapsed"
    )

    form_col1, form_col2 = st.columns(2)

    with form_col1:
        new_priority = st.selectbox(
            "Priority",
            PRIORITIES,
            index=1
        )

    with form_col2:
        new_due = st.date_input(
            "Due date (optional)",
            value=None
        )

    add_clicked = st.form_submit_button(
        "✨ Add Task",
        use_container_width=True
    )

if add_clicked:
    if new_task.strip():
        add_task(new_task, new_priority, new_due)
        st.toast("Task added! 🎉")
        st.rerun()
    else:
        st.warning("Please enter a task first.")


# =========================================================
# TASK LIST
# =========================================================

st.markdown("## 📋 Your Tasks")

sort_mode = st.selectbox("Sort by", SORT_OPTIONS, key="sort_mode")


def render_task(task, prefix):
    """Draw one task row: checkbox, tags, edit button, delete button."""
    task_id = task["id"]
    checkbox_key = f"{prefix}_{task_id}"

    # Set the checkbox's starting state once
    if checkbox_key not in st.session_state:
        st.session_state[checkbox_key] = task["completed"]

    with st.container(border=True):

        c_main, c_meta, c_edit, c_delete = st.columns(
            [5, 3, 1.2, 1.2],
            vertical_alignment="center"
        )

        # ---- checkbox + name ----
        with c_main:
            label = md_escape(task["name"])

            if task["completed"]:
                label = f"~~{label}~~"

            st.checkbox(
                label,
                key=checkbox_key,
                on_change=toggle_task,
                args=(task_id, checkbox_key)
            )

        # ---- priority + due date tags ----
        with c_meta:
            priority = task["priority"]
            tags = (
                f'<span class="badge badge-{priority.lower()}">'
                f'{html.escape(priority)}</span>'
            )

            due = parse_date(task["due"])

            if due:
                overdue = (not task["completed"]) and due < date.today()
                css_class = "due overdue" if overdue else "due"
                prefix_icon = "⚠️ " if overdue else "📅 "
                tags += (
                    f'<span class="{css_class}">'
                    f'{prefix_icon}{due.strftime("%d %b %Y")}</span>'
                )

            st.markdown(tags, unsafe_allow_html=True)

        # ---- edit ----
        with c_edit:
            with st.popover("✏️"):
                with st.form(f"edit_form_{prefix}_{task_id}"):
                    edit_name = st.text_input(
                        "Task",
                        value=task["name"],
                        key=f"edit_name_{prefix}_{task_id}"
                    )

                    edit_priority = st.selectbox(
                        "Priority",
                        PRIORITIES,
                        index=PRIORITIES.index(task["priority"]),
                        key=f"edit_priority_{prefix}_{task_id}"
                    )

                    edit_due = st.date_input(
                        "Due date (optional)",
                        value=parse_date(task["due"]),
                        key=f"edit_due_{prefix}_{task_id}"
                    )

                    save_clicked = st.form_submit_button(
                        "💾 Save",
                        use_container_width=True
                    )

                if save_clicked:
                    if edit_name.strip():
                        update_task(
                            task_id,
                            edit_name,
                            edit_priority,
                            edit_due
                        )
                        st.rerun()
                    else:
                        st.warning("The task can't be empty.")

        # ---- delete ----
        with c_delete:
            st.button(
                "🗑️",
                key=f"delete_{prefix}_{task_id}",
                on_click=delete_task,
                args=(task_id,)
            )


tab_all, tab_active, tab_completed = st.tabs([
    f"All ({total_tasks})",
    f"Active ({total_tasks - completed_count})",
    f"Completed ({completed_count})"
])

all_sorted = sort_tasks(st.session_state.tasks, sort_mode)
active_sorted = [t for t in all_sorted if not t["completed"]]
done_sorted = [t for t in all_sorted if t["completed"]]


# ---------- ALL TASKS ----------
with tab_all:
    if not all_sorted:
        st.info("✨ No tasks yet. Add your first task above!")
    else:
        for task in all_sorted:
            render_task(task, "all")


# ---------- ACTIVE TASKS ----------
with tab_active:
    if not active_sorted:
        st.success("🎉 You have no active tasks!")
    else:
        for task in active_sorted:
            render_task(task, "active")


# ---------- COMPLETED TASKS ----------
with tab_completed:
    if not done_sorted:
        st.info("📭 No completed tasks yet.")
    else:
        for task in done_sorted:
            render_task(task, "done")


# =========================================================
# PROGRESS
# =========================================================

st.markdown("## 📊 Your Progress")

progress = completed_count / total_tasks if total_tasks > 0 else 0
st.progress(progress)

st.markdown(
    f"""
    <div style="text-align: center; color: #826E8B; margin-top: -8px;">
        <strong>{completed_count}</strong> of <strong>{total_tasks}</strong>
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
        Tell your AI assistant what you want to accomplish,
        and it will help break your goal into smaller tasks.
    </p>
</div>
""", unsafe_allow_html=True)

with st.form("ai_planner_form"):
    goal = st.text_input(
        "Your goal",
        placeholder="e.g. Prepare for my Python exam",
        label_visibility="collapsed"
    )

    plan_button = st.form_submit_button(
        "✨ Plan It",
        use_container_width=True
    )

if plan_button:
    if goal.strip():
        try:
            with st.spinner("Planning your tasks... 🤖"):
                planned = ask_ai_for_tasks(goal.strip())

        except RuntimeError as error:
            st.error(str(error))

        except ValueError:
            st.error(
                "The AI's reply wasn't in the format I expected. "
                "Please try again."
            )

        except Exception as error:
            st.error(f"Something went wrong talking to the AI: {error}")

        else:
            if planned:
                for item in planned:
                    add_task(item["name"], item["priority"])

                st.toast(f"Added {len(planned)} tasks! 🎉")
                st.rerun()
            else:
                st.warning("The AI didn't come back with any tasks. Try again.")

    else:
        st.warning("Tell me what you want to accomplish first.")
