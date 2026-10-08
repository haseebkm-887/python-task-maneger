# ==========================================
# 🚀 ALPHA TASKFLOW - PREMIUM TASK MANAGER
# Single-File Streamlit Application (app.py)
# ==========================================

import os
import re
import datetime
import pandas as pd
try:
    import plotly.express as px
except ImportError:
    px = None
import bcrypt

import streamlit as st

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    extract,
    func
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, scoped_session

# ==========================================
# 1. CONFIGURATION & PAGE SETUP
# ==========================================

st.set_page_config(
    page_title="ALPHA TASKFLOW — Premium Task Manager",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "alpha_taskflow.db"
DATABASE_URL = f"sqlite:///{DB_FILE}"

# ==========================================
# 2. DATABASE MODELS & INITIALIZATION
# ==========================================

Engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=Engine))
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(20), default="#3B82F6")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), default="General")
    priority = Column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH, URGENT
    status = Column(String(20), default="TODO")      # TODO, IN PROGRESS, COMPLETED
    due_date = Column(DateTime, nullable=True)
    tags = Column(String(250), nullable=True)        # Comma-separated: #python,#work
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="notifications")

Base.metadata.create_all(bind=Engine)

# ==========================================
# 3. AUTHENTICATION & DATABASE HELPERS
# ==========================================

def get_db():
    return SessionLocal()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def register_user(username, email, password):
    db = get_db()
    try:
        if db.query(User).filter((User.username == username) | (User.email == email)).first():
            return False, "Username or Email already exists."
        hashed = hash_password(password)
        new_user = User(username=username, email=email, password_hash=hashed)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create Default Project
        default_proj = Project(user_id=new_user.id, name="General Workspace", description="Default inbox for personal tasks", color="#6366F1")
        db.add(default_proj)
        db.commit()
        return True, "Registration successful! Please login."
    except Exception as e:
        db.rollback()
        return False, f"Error creating account: {str(e)}"
    finally:
        db.close()

def authenticate_user(username_or_email, password):
    db = get_db()
    try:
        user = db.query(User).filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        if user and check_password(password, user.password_hash):
            return user
        return None
    finally:
        db.close()

def create_notification(user_id, title, message):
    db = get_db()
    try:
        notif = Notification(user_id=user_id, title=title, message=message)
        db.add(notif)
        db.commit()
    finally:
        db.close()

def check_and_generate_notifications(user_id):
    """Automatically generates notifications for overdue and due today tasks."""
    db = get_db()
    try:
        today = datetime.date.today()
        tasks = db.query(Task).filter(
            Task.user_id == user_id,
            Task.status != "COMPLETED",
            Task.due_date != None
        ).all()
        
        for task in tasks:
            task_date = task.due_date.date()
            if task_date < today:
                # Check if notification exists
                exists = db.query(Notification).filter(
                    Notification.user_id == user_id,
                    Notification.title == "Task Overdue",
                    Notification.message.contains(f"'{task.title}'")
                ).first()
                if not exists:
                    create_notification(user_id, "Task Overdue", f"Your task '{task.title}' was due on {task_date}.")
            elif task_date == today:
                exists = db.query(Notification).filter(
                    Notification.user_id == user_id,
                    Notification.title == "Task Due Today",
                    Notification.message.contains(f"'{task.title}'")
                ).first()
                if not exists:
                    create_notification(user_id, "Task Due Today", f"Your task '{task.title}' is due today!")
    finally:
        db.close()

# ==========================================
# 4. SESSION MANAGEMENT & THEMES
# ==========================================

if "user" not in st.session_state:
    st.session_state["user"] = None
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "Dashboard"

# Check notifications on load if logged in
if st.session_state["user"]:
    check_and_generate_notifications(st.session_state["user"]["id"])

# ==========================================
# 5. DYNAMIC GLASSMORPHISM & CSS STYLING
# ==========================================

def inject_custom_css(theme_mode):
    if theme_mode == "dark":
        bg_color = "#0B0F19"
        card_bg = "rgba(17, 24, 39, 0.75)"
        text_color = "#F3F4F6"
        text_muted = "#9CA3AF"
        border_color = "rgba(255, 255, 255, 0.1)"
        input_bg = "rgba(31, 41, 55, 0.8)"
        glow = "rgba(99, 102, 241, 0.25)"
    else:
        bg_color = "#F8FAFC"
        card_bg = "rgba(255, 255, 255, 0.85)"
        text_color = "#0F172A"
        text_muted = "#64748B"
        border_color = "rgba(0, 0, 0, 0.08)"
        input_bg = "#FFFFFF"
        glow = "rgba(99, 102, 241, 0.15)"

    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: {bg_color};
            color: {text_color};
        }}

        .stApp {{
            background: {bg_color};
        }}

        /* Fade/Slide animation for main view */
        .main .block-container {{
            animation: fadeIn 0.4s ease-in-out;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Glassmorphism Dynamic Cards */
        .glass-card {{
            background: {card_bg};
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid {border_color};
            border-radius: 16px;
            padding: 18px 22px;
            margin-bottom: 16px;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
        }}

        .glass-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 28px -4px {glow};
            border-color: rgba(99, 102, 241, 0.4);
        }}

        /* Metric Cards */
        .metric-card {{
            background: {card_bg};
            backdrop-filter: blur(12px);
            border: 1px solid {border_color};
            border-radius: 16px;
            padding: 16px 20px;
            text-align: left;
            transition: transform 0.2s ease;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
        }}
        .metric-title {{
            font-size: 0.85rem;
            color: {text_muted};
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .metric-value {{
            font-size: 1.8rem;
            font-weight: 800;
            margin-top: 4px;
            color: {text_color};
        }}

        /* Task Status Badges */
        .badge {{
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            display: inline-block;
        }}
        .badge-todo {{ background: rgba(59, 130, 246, 0.15); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.3); }}
        .badge-progress {{ background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }}
        .badge-completed {{ background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }}

        /* Priority Indicators */
        .priority-LOW {{ color: #10B981; font-weight: 600; }}
        .priority-MEDIUM {{ color: #F59E0B; font-weight: 600; }}
        .priority-HIGH {{ color: #EF4444; font-weight: 700; }}
        .priority-URGENT {{ color: #EC4899; font-weight: 800; animation: pulse 2s infinite; }}

        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}

        /* Deadline Tags */
        .deadline-overdue {{ color: #EF4444; font-weight: 700; }}
        .deadline-today {{ color: #F59E0B; font-weight: 700; }}
        .deadline-upcoming {{ color: #3B82F6; font-weight: 600; }}
        .deadline-completed {{ color: #10B981; font-weight: 500; }}

        /* Tag Badges */
        .tag-badge {{
            background: rgba(99, 102, 241, 0.12);
            color: #818CF8;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            margin-right: 4px;
            border: 1px solid rgba(99, 102, 241, 0.2);
        }}

        /* Buttons & Forms Styling */
        .stButton>button {{
            border-radius: 12px;
            font-weight: 600;
            transition: all 0.2s ease;
            border: 1px solid {border_color};
        }}
        .stButton>button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px {glow};
        }}

        /* Hide Streamlit Branding */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

inject_custom_css(st.session_state["theme"])

# ==========================================
# 6. UI COMPONENTS & HELPER RENDERERS
# ==========================================

def render_empty_state(message="You're all clear!", submessage="No tasks match your criteria. Enjoy your day or create a new task."):
    st.markdown(f"""
    <div class="glass-card" style="text-align: center; padding: 48px 24px;">
        <div style="font-size: 3rem; margin-bottom: 12px;">✨</div>
        <h3 style="margin: 0; font-weight: 700;">{message}</h3>
        <p style="color: gray; margin-top: 8px; font-size: 0.95rem;">{submessage}</p>
    </div>
    """, unsafe_allow_html=True)

def render_task_card(task, projects_dict):
    today = datetime.date.today()
    
    # Priority Color Styling
    priority_class = f"priority-{task.priority}"
    
    # Status Badge
    status_class = "badge-todo"
    if task.status == "IN PROGRESS":
        status_class = "badge-progress"
    elif task.status == "COMPLETED":
        status_class = "badge-completed"
        
    # Deadline Calculation
    deadline_text = "No due date"
    deadline_class = ""
    if task.due_date:
        due_d = task.due_date.date()
        if task.status == "COMPLETED":
            deadline_text = f"Done on {task.completed_at.strftime('%b %d') if task.completed_at else 'N/A'}"
            deadline_class = "deadline-completed"
        elif due_d < today:
            deadline_text = f"🔴 Overdue ({due_d.strftime('%b %d')})"
            deadline_class = "deadline-overdue"
        elif due_d == today:
            deadline_text = f"🟡 Due Today"
            deadline_class = "deadline-today"
        elif due_d == today + datetime.timedelta(days=1):
            deadline_text = f"🔵 Tomorrow"
            deadline_class = "deadline-upcoming"
        else:
            deadline_text = f"📅 {due_d.strftime('%b %d, %Y')}"
            deadline_class = "deadline-upcoming"

    # Project Name
    project_name = projects_dict.get(task.project_id, "General")
    
    # Tags HTML
    tags_html = ""
    if task.tags:
        for tag in task.tags.split(","):
            tag_clean = tag.strip()
            if tag_clean:
                if not tag_clean.startswith("#"):
                    tag_clean = f"#{tag_clean}"
                tags_html += f'<span class="tag-badge">{tag_clean}</span>'

    card_html = f"""
    <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <span class="badge {status_class}">{task.status}</span>
                <span style="font-size: 0.8rem; margin-left: 8px;" class="{priority_class}">⚡ {task.priority}</span>
                <h4 style="margin: 8px 0 4px 0; font-weight: 700; font-size: 1.1rem;">{task.title}</h4>
            </div>
            <span class="{deadline_class}" style="font-size: 0.85rem;">{deadline_text}</span>
        </div>
        <p style="color: gray; font-size: 0.88rem; margin: 4px 0 12px 0;">{task.description if task.description else 'No description provided.'}</p>
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem;">
            <div>{tags_html}</div>
            <div style="color: gray; font-weight: 500;">📁 {project_name} | 🏷️ {task.category}</div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

# ==========================================
# 7. AUTHENTICATION MODULE (LOGIN / REGISTER)
# ==========================================

def render_auth_page():
    st.markdown("<h1 style='text-align: center; font-weight: 800; font-size: 2.8rem;'>⚡ ALPHA TASKFLOW</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray; margin-bottom: 30px;'>Next-Generation Productivity & Task Intelligence Platform</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["🔒 Sign In", "🚀 Create Account"])
        
        with tab1:
            st.subheader("Welcome Back")
            login_user = st.text_input("Username or Email", key="login_u")
            login_pass = st.text_input("Password", type="password", key="login_p")
            if st.button("Sign In", use_container_width=True, type="primary"):
                if login_user and login_pass:
                    user = authenticate_user(login_user, login_pass)
                    if user:
                        st.session_state["user"] = {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email
                        }
                        st.toast("Welcome back to Alpha Taskflow!", icon="⚡")
                        st.rerun()
                    else:
                        st.error("Invalid username/email or password.")
                else:
                    st.warning("Please fill in all fields.")

        with tab2:
            st.subheader("Join Alpha Taskflow")
            reg_user = st.text_input("Username", key="reg_u")
            reg_email = st.text_input("Email Address", key="reg_e")
            reg_pass = st.text_input("Password", type="password", key="reg_p")
            if st.button("Create Free Account", use_container_width=True):
                if reg_user and reg_email and reg_pass:
                    if len(reg_pass) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif not re.match(r"[^@]+@[^@]+\.[^@]+", reg_email):
                        st.error("Invalid email address format.")
                    else:
                        success, msg = register_user(reg_user, reg_email, reg_pass)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
                else:
                    st.warning("Please fill in all fields.")
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 8. MAIN DASHBOARD VIEW
# ==========================================

def render_dashboard(user_id):
    db = get_db()
    try:
        user_name = st.session_state["user"]["username"].capitalize()
        st.markdown(f"## Good day, {user_name} 👋")
        st.markdown("<p style='color: gray;'>Let's stay focused and achieve your goals today.</p>", unsafe_allow_html=True)
        
        # Query User Metrics
        total_tasks = db.query(Task).filter(Task.user_id == user_id).count()
        completed_tasks = db.query(Task).filter(Task.user_id == user_id, Task.status == "COMPLETED").count()
        in_progress_tasks = db.query(Task).filter(Task.user_id == user_id, Task.status == "IN PROGRESS").count()
        
        today = datetime.date.today()
        overdue_tasks = db.query(Task).filter(
            Task.user_id == user_id,
            Task.status != "COMPLETED",
            Task.due_date < today
        ).count()

        # Render Metric Cards
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f'<div class="metric-card"><div class="metric-title">Total Tasks</div><div class="metric-value">{total_tasks}</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="metric-card"><div class="metric-title">Completed</div><div class="metric-value" style="color:#34D399;">{completed_tasks}</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-card"><div class="metric-title">In Progress</div><div class="metric-value" style="color:#FBBF24;">{in_progress_tasks}</div></div>', unsafe_allow_html=True)
        with m4:
            st.markdown(f'<div class="metric-card"><div class="metric-title">Overdue</div><div class="metric-value" style="color:#F87171;">{overdue_tasks}</div></div>', unsafe_allow_html=True)

        st.markdown("---")

        # Productivity Overview & Charts
        c1, c2 = st.columns([1.8, 1])
        
        with c1:
            st.subheader("📈 Weekly Productivity Velocity")
            # Generate past 7 days chart data
            days = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
            day_labels = [d.strftime("%a") for d in days]
            counts = []
            
            for d in days:
                cnt = db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.status == "COMPLETED",
                    func.date(Task.completed_at) == d
                ).count()
                counts.append(cnt)

            df_chart = pd.DataFrame({"Day": day_labels, "Completed Tasks": counts})
            
                        if px is not None:
                fig = px.bar(
                    df_chart,
                    x="Day",
                    y="Completed Tasks",
                    text="Completed Tasks",
                    color_discrete_sequence=["#6366F1"]
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#9CA3AF"),
                    margin=dict(l=10, r=10, t=20, b=20),
                    height=260,
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
                )
                fig.update_traces(marker_round_shape="round", marker_line_width=0)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Charts are unavailable because Plotly is not installed.")


        with c2:
            st.subheader("🎯 Priority Distribution")
            p_counts = []
            p_labels = ["LOW", "MEDIUM", "HIGH", "URGENT"]
            for p in p_labels:
                cnt = db.query(Task).filter(Task.user_id == user_id, Task.priority == p, Task.status != "COMPLETED").count()
                p_counts.append(cnt)
            
            df_pie = pd.DataFrame({"Priority": p_labels, "Count": p_counts})
                        if px is None:
                st.info("Charts are unavailable because Plotly is not installed.")
            elif sum(p_counts) > 0:
                fig_pie = px.pie(

                    df_pie, 
                    values="Count", 
                    names="Priority",
                    color="Priority",
                    color_discrete_map={
                        "LOW": "#10B981",
                        "MEDIUM": "#F59E0B",
                        "HIGH": "#EF4444",
                        "URGENT": "#EC4899"
                    },
                    hole=0.5
                )
                fig_pie.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#9CA3AF"),
                    margin=dict(l=10, r=10, t=20, b=20),
                    height=260,
                    showlegend=True
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No active tasks to show priority breakdown.")

        st.markdown("---")
        st.subheader("📌 High Priority & Immediate Focus")
        
        # High Priority or Urgent Tasks List
        urgent_tasks = db.query(Task).filter(
            Task.user_id == user_id,
            Task.status != "COMPLETED",
            Task.priority.in_(["HIGH", "URGENT"])
        ).order_by(Task.due_date.asc()).limit(5).all()

        projects = db.query(Project).filter(Project.user_id == user_id).all()
        proj_dict = {p.id: p.name for p in projects}

        if urgent_tasks:
            for t in urgent_tasks:
                render_task_card(t, proj_dict)
        else:
            render_empty_state("No Critical Tasks Pending", "All high-priority goals are currently up to date.")

    finally:
        db.close()

# ==========================================
# 9. TASK MANAGEMENT & VIEWS MODULE
# ==========================================

def render_task_management(user_id):
    db = get_db()
    try:
        st.title("📋 Task Flow Manager")
        
        projects = db.query(Project).filter(Project.user_id == user_id).all()
        proj_dict = {p.id: p.name for p in projects}
        proj_options = {"All Projects": None}
        for p in projects:
            proj_options[p.name] = p.id

        # Task View Switcher Tabs
        view_tab, quick_add_tab, create_tab = st.tabs(["🔍 View Tasks", "⚡ Quick Add", "➕ Detailed Task Creation"])

        # ------------------- TAB 1: VIEW TASKS -------------------
        with view_tab:
            # Filters & Controls
            f_col1, f_col2, f_col3, f_col4 = st.columns([1.5, 1, 1, 1])
            with f_col1:
                search_query = st.text_input("🔎 Search Tasks", placeholder="Search title, tags, description...")
            with f_col2:
                status_filter = st.selectbox("Status", ["ALL", "TODO", "IN PROGRESS", "COMPLETED", "OVERDUE", "TODAY"])
            with f_col3:
                priority_filter = st.selectbox("Priority", ["ALL", "LOW", "MEDIUM", "HIGH", "URGENT"])
            with f_col4:
                project_filter = st.selectbox("Project", list(proj_options.keys()))

            # Base Query
            query = db.query(Task).filter(Task.user_id == user_id)

            # Apply Filters
            if search_query:
                sq = f"%{search_query}%"
                query = query.filter((Task.title.ilike(sq)) | (Task.description.ilike(sq)) | (Task.tags.ilike(sq)))
            
            today = datetime.date.today()
            if status_filter == "OVERDUE":
                query = query.filter(Task.status != "COMPLETED", Task.due_date < today)
            elif status_filter == "TODAY":
                query = query.filter(Task.due_date == today)
            elif status_filter != "ALL":
                query = query.filter(Task.status == status_filter)

            if priority_filter != "ALL":
                query = query.filter(Task.priority == priority_filter)

            if proj_options[project_filter] is not None:
                query = query.filter(Task.project_id == proj_options[project_filter])

            tasks = query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).all()

            st.caption(f"Showing {len(tasks)} matching task(s)")

            if not tasks:
                render_empty_state()
            else:
                for task in tasks:
                    col_card, col_act = st.columns([4, 1.2])
                    with col_card:
                        render_task_card(task, proj_dict)
                    with col_act:
                        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                        
                        # Interactive Actions
                        if task.status != "COMPLETED":
                            if st.button("✅ Complete", key=f"comp_{task.id}", use_container_width=True):
                                task.status = "COMPLETED"
                                task.completed_at = datetime.datetime.utcnow()
                                db.commit()
                                st.toast(f"Task '{task.title}' completed!", icon="🎉")
                                st.rerun()
                        else:
                            if st.button("↩️ Reopen", key=f"reopen_{task.id}", use_container_width=True):
                                task.status = "TODO"
                                task.completed_at = None
                                db.commit()
                                st.toast(f"Task '{task.title}' reopened.")
                                st.rerun()

                        # Edit Expander / Modal
                        with st.popover("✏️ Edit Task", use_container_width=True):
                            st.subheader("Edit Task")
                            new_title = st.text_input("Title", value=task.title, key=f"e_title_{task.id}")
                            new_desc = st.text_area("Description", value=task.description or "", key=f"e_desc_{task.id}")
                            new_status = st.selectbox("Status", ["TODO", "IN PROGRESS", "COMPLETED"], index=["TODO", "IN PROGRESS", "COMPLETED"].index(task.status), key=f"e_stat_{task.id}")
                            new_prio = st.selectbox("Priority", ["LOW", "MEDIUM", "HIGH", "URGENT"], index=["LOW", "MEDIUM", "HIGH", "URGENT"].index(task.priority), key=f"e_prio_{task.id}")
                            
                            cur_date = task.due_date.date() if task.due_date else datetime.date.today()
                            new_date = st.date_input("Due Date", value=cur_date, key=f"e_date_{task.id}")
                            new_tags = st.text_input("Tags (comma separated)", value=task.tags or "", key=f"e_tags_{task.id}")
                            
                            if st.button("Save Changes", key=f"save_{task.id}", type="primary"):
                                task.title = new_title
                                task.description = new_desc
                                task.status = new_status
                                task.priority = new_prio
                                task.due_date = datetime.datetime.combine(new_date, datetime.time.min)
                                task.tags = new_tags
                                task.updated_at = datetime.datetime.utcnow()
                                if new_status == "COMPLETED" and not task.completed_at:
                                    task.completed_at = datetime.datetime.utcnow()
                                db.commit()
                                st.toast("Task updated successfully!")
                                st.rerun()

                        # Delete Task with Confirmation Safety
                        with st.popover("🗑️ Delete", use_container_width=True):
                            st.write("Are you sure? This action cannot be undone.")
                            if st.button("Confirm Delete", key=f"del_{task.id}", type="primary"):
                                db.delete(task)
                                db.commit()
                                st.toast("Task deleted.")
                                st.rerun()

        # ------------------- TAB 2: QUICK ADD -------------------
        with quick_add_tab:
            st.subheader("⚡ Fast Task Entry")
            with st.form("quick_add_form", clear_on_submit=True):
                q_title = st.text_input("Task Title*", placeholder="e.g., Review Q3 Financial Plan")
                qc1, qc2 = st.columns(2)
                with qc1:
                    q_prio = st.selectbox("Priority", ["LOW", "MEDIUM", "HIGH", "URGENT"], index=1)
                with qc2:
                    q_date = st.date_input("Due Date", value=datetime.date.today())
                
                q_submit = st.form_submit_button("Create Task Immediately", type="primary", use_container_width=True)
                if q_submit:
                    if not q_title.strip():
                        st.error("Task title cannot be empty.")
                    else:
                        new_t = Task(
                            user_id=user_id,
                            title=q_title,
                            priority=q_prio,
                            due_date=datetime.datetime.combine(q_date, datetime.time.min),
                            project_id=projects[0].id if projects else None
                        )
                        db.add(new_t)
                        db.commit()
                        st.toast("Task created successfully!", icon="🚀")
                        st.rerun()

        # ------------------- TAB 3: DETAILED CREATION -------------------
        with create_tab:
            st.subheader("➕ Create Detailed Task")
            with st.form("detailed_add_form", clear_on_submit=True):
                d_title = st.text_input("Task Title*")
                d_desc = st.text_area("Description")
                
                dc1, dc2, dc3 = st.columns(3)
                with dc1:
                    d_project = st.selectbox("Project", list(proj_options.keys())[1:]) if len(proj_options) > 1 else None
                with dc2:
                    d_category = st.selectbox("Category", ["Study", "Coding", "Personal", "Work", "Design", "Fitness", "Other"])
                with dc3:
                    d_prio = st.selectbox("Priority", ["LOW", "MEDIUM", "HIGH", "URGENT"], index=1)

                dc4, dc5 = st.columns(2)
                with dc4:
                    d_date = st.date_input("Due Date", value=datetime.date.today())
                with dc5:
                    d_time = st.time_input("Due Time", value=datetime.time(17, 0))

                d_tags = st.text_input("Tags", placeholder="e.g. #urgent, #python, #project")
                d_notes = st.text_area("Notes & Reference Links")

                d_submit = st.form_submit_button("Save Full Task", type="primary", use_container_width=True)
                if d_submit:
                    if not d_title.strip():
                        st.error("Task title is required.")
                    else:
                        combined_dt = datetime.datetime.combine(d_date, d_time)
                        proj_id = proj_options[d_project] if d_project else (projects[0].id if projects else None)
                        
                        full_t = Task(
                            user_id=user_id,
                            title=d_title,
                            description=d_desc,
                            project_id=proj_id,
                            category=d_category,
                            priority=d_prio,
                            due_date=combined_dt,
                            tags=d_tags,
                            notes=d_notes
                        )
                        db.add(full_t)
                        db.commit()
                        st.toast("Detailed task added successfully!", icon="🎉")
                        st.rerun()

    finally:
        db.close()

# ==========================================
# 10. PROJECT MANAGEMENT MODULE
# ==========================================

def render_projects(user_id):
    db = get_db()
    try:
        st.title("📁 Workspace Projects")
        
        # New Project Section
        with st.expander("➕ Create New Project", expanded=False):
            with st.form("new_project_form", clear_on_submit=True):
                p_name = st.text_input("Project Name*")
                p_desc = st.text_area("Description")
                p_color = st.color_picker("Project Theme Color", "#6366F1")
                if st.form_submit_button("Create Project", type="primary"):
                    if p_name.strip():
                        new_p = Project(user_id=user_id, name=p_name, description=p_desc, color=p_color)
                        db.add(new_p)
                        db.commit()
                        st.toast("New project created!")
                        st.rerun()
                    else:
                        st.error("Project name is required.")

        projects = db.query(Project).filter(Project.user_id == user_id).all()
        
        if not projects:
            render_empty_state("No Projects", "Create a workspace project to organize your workflows.")
            return

        cols = st.columns(2)
        for idx, proj in enumerate(projects):
            total_p_tasks = db.query(Task).filter(Task.project_id == proj.id).count()
            completed_p_tasks = db.query(Task).filter(Task.project_id == proj.id, Task.status == "COMPLETED").count()
            progress = (completed_p_tasks / total_p_tasks) if total_p_tasks > 0 else 0.0

            with cols[idx % 2]:
                st.markdown(f"""
                <div class="glass-card" style="border-left: 6px solid {proj.color};">
                    <h3 style="margin:0;">{proj.name}</h3>
                    <p style="color:gray; font-size:0.88rem; margin:6px 0;">{proj.description if proj.description else 'No description'}</p>
                    <div style="margin: 12px 0;">
                        <small>Progress: {completed_p_tasks}/{total_p_tasks} Tasks ({int(progress*100)}%)</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.progress(progress)
                
    finally:
        db.close()

# ==========================================
# 11. CALENDAR VIEW MODULE
# ==========================================

def render_calendar(user_id):
    db = get_db()
    try:
        st.title("📅 Task Timeline & Calendar")
        
        tasks = db.query(Task).filter(Task.user_id == user_id, Task.due_date != None).all()
        
                if not tasks:
            render_empty_state("Calendar Clear", "No scheduled tasks with deadlines were found.")
            return
        if px is None:
            st.info("The calendar chart is unavailable because Plotly is not installed.")
            return

        # Prepare DataFrame for Timeline / Calendar Plotly representation

        events = []
        for t in tasks:
            events.append({
                "Task": t.title,
                "Start": t.due_date,
                "Finish": t.due_date + datetime.timedelta(hours=2),
                "Priority": t.priority,
                "Status": t.status
            })
        
        df_events = pd.DataFrame(events)
        
        fig = px.timeline(
            df_events, 
            x_start="Start", 
            x_end="Finish", 
            y="Task", 
            color="Priority",
            title="Scheduled Deadlines Timeline",
            color_discrete_map={
                "LOW": "#10B981",
                "MEDIUM": "#F59E0B",
                "HIGH": "#EF4444",
                "URGENT": "#EC4899"
            }
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#9CA3AF"),
            height=450
        )
        st.plotly_chart(fig, use_container_width=True)

    finally:
        db.close()

# ==========================================
# 12. ANALYTICS & PRODUCTIVITY REPORTS
# ==========================================

def render_analytics(user_id):
    db = get_db()
    try:
        st.title("📊 Productivity Intelligence & Analytics")
        
        total = db.query(Task).filter(Task.user_id == user_id).count()
        completed = db.query(Task).filter(Task.user_id == user_id, Task.status == "COMPLETED").count()
        completion_rate = (completed / total * 100) if total > 0 else 0

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Lifetime Tasks", total)
        with c2:
            st.metric("Completed Tasks", completed)
        with c3:
            st.metric("Overall Completion Rate", f"{completion_rate:.1f}%")

        st.markdown("---")

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Category Breakdown")
            cat_data = db.query(Task.category, func.count(Task.id)).filter(Task.user_id == user_id).group_by(Task.category).all()
                        if cat_data and px is not None:
                df_cat = pd.DataFrame(cat_data, columns=["Category", "Count"])

                fig_cat = px.bar(df_cat, x="Category", y="Count", color="Category", color_discrete_sequence=px.colors.qualitative.Pastel)
                                fig_cat.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#9CA3AF"))
                st.plotly_chart(fig_cat, use_container_width=True)
            elif cat_data:
                st.info("Charts are unavailable because Plotly is not installed.")

        with col2:

            st.subheader("Status Velocity")
            stat_data = db.query(Task.status, func.count(Task.id)).filter(Task.user_id == user_id).group_by(Task.status).all()
                        if stat_data and px is not None:
                df_stat = pd.DataFrame(stat_data, columns=["Status", "Count"])

                fig_stat = px.pie(df_stat, names="Status", values="Count", hole=0.4)
                                fig_stat.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#9CA3AF"))
                st.plotly_chart(fig_stat, use_container_width=True)
            elif stat_data:
                st.info("Charts are unavailable because Plotly is not installed.")

    finally:

        db.close()

# ==========================================
# 13. USER PROFILE & NOTIFICATIONS
# ==========================================

def render_profile_and_notifications(user_id):
    db = get_db()
    try:
        st.title("👤 User Profile & Notifications")
        
        t1, t2 = st.tabs(["🔔 Notifications", "👤 Account Profile"])

        with t1:
            st.subheader("System Notifications")
            notifs = db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc()).all()
            if notifs:
                if st.button("Mark All as Read"):
                    for n in notifs:
                        n.is_read = True
                    db.commit()
                    st.rerun()

                for n in notifs:
                    read_status = "opacity: 0.6;" if n.is_read else "border-left: 4px solid #6366F1;"
                    st.markdown(f"""
                    <div class="glass-card" style="{read_status}">
                        <div style="display:flex; justify-content:space-between;">
                            <strong>{n.title}</strong>
                            <small style="color:gray;">{n.created_at.strftime('%b %d, %H:%M')}</small>
                        </div>
                        <p style="margin:4px 0 0 0; color:gray; font-size:0.9rem;">{n.message}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                render_empty_state("No Notifications", "You're all caught up!")

        with t2:
            u = db.query(User).filter(User.id == user_id).first()
            st.subheader("Account Details")
            st.write(f"**Username:** {u.username}")
            st.write(f"**Email:** {u.email}")
            st.write(f"**Member Since:** {u.created_at.strftime('%B %d, %Y')}")

    finally:
        db.close()

# ==========================================
# 14. MAIN APPLICATION ROUTER & NAVIGATION
# ==========================================

def main():
    if not st.session_state["user"]:
        render_auth_page()
        return

    user_id = st.session_state["user"]["id"]

    # Sidebar Navigation & User Panel
    with st.sidebar:
        st.markdown("<h2 style='font-weight:800;'>⚡ TASKFLOW</h2>", unsafe_allow_html=True)
        st.caption(f"Logged in as **{st.session_state['user']['username']}**")
        st.markdown("---")

        # Theme Switcher
        theme_toggle = st.toggle("🌙 Dark Interface", value=(st.session_state["theme"] == "dark"))
        new_theme = "dark" if theme_toggle else "light"
        if new_theme != st.session_state["theme"]:
            st.session_state["theme"] = new_theme
            st.rerun()

        st.markdown("### Navigation")
        
        db = get_db()
        unread_count = db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read == False).count()
        db.close()

        nav_options = {
            "Dashboard": "🏠 Dashboard",
            "Tasks": "📋 Task Manager",
            "Projects": "📁 Projects",
            "Calendar": "📅 Calendar",
            "Analytics": "📊 Analytics",
            "Notifications": f"🔔 Notifications ({unread_count})" if unread_count > 0 else "🔔 Notifications"
        }

        for key, label in nav_options.items():
            if st.button(label, key=f"nav_{key}", use_container_width=True, type="primary" if st.session_state["active_tab"] == key else "secondary"):
                st.session_state["active_tab"] = key
                st.rerun()

        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state["user"] = None
            st.session_state["active_tab"] = "Dashboard"
            st.rerun()

    # Route Views
    tab = st.session_state["active_tab"]
    if tab == "Dashboard":
        render_dashboard(user_id)
    elif tab == "Tasks":
        render_task_management(user_id)
    elif tab == "Projects":
        render_projects(user_id)
    elif tab == "Calendar":
        render_calendar(user_id)
    elif tab == "Analytics":
        render_analytics(user_id)
    elif tab == "Notifications":
        render_profile_and_notifications(user_id)

if __name__ == "__main__":
    main()
