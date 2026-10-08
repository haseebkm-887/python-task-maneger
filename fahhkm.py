# Save this entire file as app.py and run with: streamlit run app.py

import sqlite3
import datetime
import streamlit as st

# ==========================================
# 1. DATABASE SETUP
# ==========================================
DB_FILE = "tasks.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_tasks(search_query="", filter_status="All", filter_priority="All"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    query = "SELECT id, title, description, priority, due_date, status FROM tasks WHERE 1=1"
    params = []
    
    if search_query:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
        
    if filter_status == "Completed":
        query += " AND status = 'Completed'"
    elif filter_status == "Pending":
        query += " AND status = 'Pending'"
    elif filter_status == "Overdue":
        today_str = datetime.date.today().isoformat()
        query += " AND status = 'Pending' AND due_date < ?"
        params.append(today_str)
        
    if filter_priority != "All":
        query += " AND priority = ?"
        params.append(filter_priority)
        
    query += " ORDER BY due_date ASC, id DESC"
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows

def add_task(title, description, priority, due_date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (title, description, priority, due_date, status) VALUES (?, ?, ?, ?, ?)",
        (title, description, priority, due_date.isoformat(), "Pending")
    )
    conn.commit()
    conn.close()

def update_task(task_id, title, description, priority, due_date, status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "UPDATE tasks SET title = ?, description = ?, priority = ?, due_date = ?, status = ? WHERE id = ?",
        (title, description, priority, due_date.isoformat(), status, task_id)
    )
    conn.commit()
    conn.close()

def toggle_task_status(task_id, current_status):
    new_status = "Completed" if current_status == "Pending" else "Pending"
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def get_task_counts():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    today_str = datetime.date.today().isoformat()
    
    c.execute("SELECT COUNT(*) FROM tasks")
    total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Completed'")
    completed = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Pending'")
    pending = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Pending' AND due_date < ?", (today_str,))
    overdue = c.fetchone()[0]
    
    conn.close()
    return total, completed, pending, overdue

# Initialize DB on start
init_db()

# ==========================================
# 2. STREAMLIT CONFIG & STATE
# ==========================================
st.set_page_config(
    page_title="TaskFlow - Modern Task Manager",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "theme" not in st.state_dict:
    st.session_state["theme"] = "dark"

if "editing_task_id" not in st.session_state:
    st.session_state["editing_task_id"] = None

# ==========================================
# 3. DYNAMIC STYLING (CSS)
# ==========================================
is_dark = st.session_state["theme"] == "dark"

# Theme Variables
bg_gradient = "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #311042 100%)" if is_dark else "linear-gradient(135deg, #f8fafc 0%, #e0e7ff 50%, #f3e8ff 100%)"
card_bg = "rgba(30, 41, 59, 0.7)" if is_dark else "rgba(255, 255, 255, 0.85)"
card_border = "rgba(255, 255, 255, 0.1)" if is_dark else "rgba(0, 0, 0, 0.08)"
text_color = "#f8fafc" if is_dark else "#0f172a"
text_muted = "#94a3b8" if is_dark else "#64748b"

css = f"""
<style>
    /* Global App Styling */
    .stApp {{
        background: {bg_gradient};
        color: {text_color};
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }}
    
    /* Smooth Transitions */
    * {{
        transition: background-color 0.3s ease, border-color 0.3s ease, transform 0.2s ease, box-shadow 0.3s ease;
    }}

    /* Title Gradient */
    .gradient-title {{
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }}
    
    .sub-title {{
        color: {text_muted};
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }}

    /* Stat Cards */
    .stat-card {{
        background: {card_bg};
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid {card_border};
        border-radius: 16px;
        padding: 1rem 1.2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }}
    .stat-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.25);
    }}
    .stat-label {{
        color: {text_muted};
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .stat-value {{
        font-size: 1.8rem;
        font-weight: 700;
        color: {text_color};
    }}

    /* Task Card */
    .task-card {{
        background: {card_bg};
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid {card_border};
        border-radius: 16px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        position: relative;
    }}
    .task-card:hover {{
        transform: translateY(-2px) scale(1.005);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
        border-color: rgba(168, 85, 247, 0.4);
    }}

    /* Task Elements */
    .task-title {{
        font-size: 1.15rem;
        font-weight: 600;
        color: {text_color};
        margin-bottom: 0.3rem;
    }}
    .task-title.completed {{
        text-decoration: line-through;
        color: {text_muted};
    }}
    .task-desc {{
        color: {text_muted};
        font-size: 0.9rem;
        margin-bottom: 0.8rem;
        line-height: 1.4;
    }}

    /* Badges */
    .badge {{
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }}
    .priority-High {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
    .priority-Medium {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }}
    .priority-Low {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
    
    .status-Completed {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }}
    .status-Pending {{ background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }}
    .status-Overdue {{ background: rgba(225, 29, 72, 0.25); color: #fda4af; border: 1px solid rgba(225, 29, 72, 0.4); }}

    .date-tag {{
        color: {text_muted};
        font-size: 0.8rem;
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
    }}

    /* Hide standard Streamlit header/footer padding */
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 3rem;
    }}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ==========================================
# 4. SIDEBAR - CONTROLS & ADD TASK
# ==========================================
with st.sidebar:
    st.markdown("<div class='gradient-title'>TaskFlow</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Organize your day with ease</div>", unsafe_allow_html=True)
    
    # Theme Switcher
    theme_btn_label = "☀️ Light Mode" if is_dark else "🌙 Dark Mode"
    if st.button(theme_btn_label, use_container_width=True):
        st.session_state["theme"] = "light" if is_dark else "dark"
        st.rerun()

    st.divider()

    # Add Task Section
    st.subheader("➕ Create Task")
    with st.form("add_task_form", clear_on_submit=True):
        new_title = st.text_input("Title*", placeholder="e.g., Complete project report")
        new_desc = st.text_area("Description", placeholder="Details or notes...", height=80)
        
        col_p, col_d = st.columns(2)
        with col_p:
            new_priority = st.selectbox("Priority", ["Low", "Medium", "High"], index=1)
        with col_d:
            new_due_date = st.date_input("Due Date", datetime.date.today())
            
        submitted = st.form_submit_button("Add Task", use_container_width=True)
        if submitted:
            if new_title.strip():
                add_task(new_title.strip(), new_desc.strip(), new_priority, new_due_date)
                st.toast("Task added successfully!", icon="✅")
                st.rerun()
            else:
                st.error("Title is required.")

# ==========================================
# 5. DASHBOARD STATS
# ==========================================
total, completed, pending, overdue = get_task_counts()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Total Tasks</div>
            <div class="stat-value">{total}</div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Completed</div>
            <div class="stat-value" style="color: #60a5fa;">{completed}</div>
        </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Pending</div>
            <div class="stat-value" style="color: #c084fc;">{pending}</div>
        </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Overdue</div>
            <div class="stat-value" style="color: #f87171;">{overdue}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 6. FILTERS & SEARCH BAR
# ==========================================
f_col1, f_col2, f_col3 = st.columns([2, 1, 1])

with f_col1:
    search_q = st.text_input("🔍 Search", placeholder="Search by title or description...", label_visibility="collapsed")

with f_col2:
    status_filter = st.selectbox(
        "Status Filter",
        ["All", "Pending", "Completed", "Overdue"],
        label_visibility="collapsed"
    )

with f_col3:
    priority_filter = st.selectbox(
        "Priority Filter",
        ["All", "High", "Medium", "Low"],
        label_visibility="collapsed"
    )

# Fetch Tasks
tasks = get_tasks(search_q, status_filter, priority_filter)

# ==========================================
# 7. TASK LIST & EDIT DIALOG
# ==========================================
st.markdown("### Tasks")

if not tasks:
    st.info("No tasks found matching your filter criteria.")
else:
    today_str = datetime.date.today().isoformat()
    
    for task in tasks:
        t_id, t_title, t_desc, t_priority, t_due, t_status = task
        
        # Determine display status badge
        is_overdue = (t_status == "Pending" and t_due < today_str)
        status_badge_class = "status-Overdue" if is_overdue else f"status-{t_status}"
        status_label = "Overdue" if is_overdue else t_status

        # Task Card Container
        with st.container():
            col_content, col_actions = st.columns([4, 1.2])
            
            with col_content:
                title_class = "task-title completed" if t_status == "Completed" else "task-title"
                st.markdown(f"""
                    <div class="{title_class}">{t_title}</div>
                    <div class="task-desc">{t_desc if t_desc else "<i>No description provided.</i>"}</div>
                    <div>
                        <span class="badge priority-{t_priority}">{t_priority} Priority</span>
                        <span class="badge {status_badge_class}">{status_label}</span>
                        <span class="date-tag">📅 Due: {t_due}</span>
                    </div>
                """, unsafe_allow_html=True)

            with col_actions:
                # Action Buttons
                btn_c1, btn_c2, btn_c3 = st.columns(3)
                
                # Toggle Status Button
                check_icon = "↩️" if t_status == "Completed" else "✅"
                if btn_c1.button(check_icon, key=f"toggle_{t_id}", help="Toggle Complete/Pending"):
                    toggle_task_status(t_id, t_status)
                    st.rerun()

                # Edit Button
                if btn_c2.button("✏️", key=f"edit_btn_{t_id}", help="Edit Task"):
                    st.session_state["editing_task_id"] = t_id
                    st.rerun()

                # Delete Button
                if btn_c3.button("🗑️", key=f"del_{t_id}", help="Delete Task"):
                    delete_task(t_id)
                    st.toast("Task deleted!", icon="🗑️")
                    st.rerun()

            st.markdown("<hr style='margin: 1rem 0; opacity: 0.1;'>", unsafe_allow_html=True)

# ==========================================
# 8. EDIT TASK MODAL/FORM (INLINE EXPANDER)
# ==========================================
if st.session_state["editing_task_id"] is not None:
    edit_id = st.session_state["editing_task_id"]
    
    # Get current task details
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, title, description, priority, due_date, status FROM tasks WHERE id = ?", (edit_id,))
    target_task = c.fetchone()
    conn.close()

    if target_task:
        st.markdown("---")
        st.subheader(f"✏️ Edit Task #{edit_id}")
        
        with st.form("edit_task_form"):
            e_title = st.text_input("Title", value=target_task[1])
            e_desc = st.text_area("Description", value=target_task[2])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                p_options = ["Low", "Medium", "High"]
                e_priority = st.selectbox("Priority", p_options, index=p_options.index(target_task[3]))
            with col2:
                e_due_date = st.date_input("Due Date", datetime.date.fromisoformat(target_task[4]))
            with col3:
                s_options = ["Pending", "Completed"]
                e_status = st.selectbox("Status", s_options, index=s_options.index(target_task[5]))

            btn_save, btn_cancel = st.columns(2)
            
            with btn_save:
                if st.form_submit_button("Save Changes", use_container_width=True):
                    if e_title.strip():
                        update_task(edit_id, e_title.strip(), e_desc.strip(), e_priority, e_due_date, e_status)
                        st.session_state["editing_task_id"] = None
                        st.toast("Task updated successfully!", icon="✅")
                        st.rerun()
                    else:
                        st.error("Title cannot be empty.")
                        
            with btn_cancel:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state["editing_task_id"] = None
                    st.rerun()
