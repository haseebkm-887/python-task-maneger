# =========================
# IMPORTS
# =========================
import os
import io
import re
import datetime
import pandas as pd
import bcrypt
import streamlit as st
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text, Date, DateTime, Time,
    ForeignKey, Boolean, Table
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, scoped_session

# =========================
# CONFIGURATION
# =========================
st.set_page_config(
    page_title="ALPHA CAMPUS PORTAL",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "alpha_campus.db"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Allowed upload extensions
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'png', 'jpg', 'jpeg', 'mp4', 'txt', 'zip'}
MAX_FILE_SIZE_MB = 10

# =========================
# DATABASE & MODELS
# =========================
Base = declarative_base()

class DBUser(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False) # 'admin', 'teacher', 'student'
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    student_profile = relationship("DBStudent", uselist=False, back_populates="user", cascade="all, delete-orphan")
    teacher_profile = relationship("DBTeacher", uselist=False, back_populates="user", cascade="all, delete-orphan")

class DBClass(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False) # e.g. "CS-101", "Semester 3"
    code = Column(String(20), unique=True, nullable=False)

    students = relationship("DBStudent", back_populates="class_rel")
    subjects = relationship("DBSubject", back_populates="class_rel")
    timetables = relationship("DBTimetable", back_populates="class_rel")

class DBTeacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    employee_id = Column(String(50), unique=True, nullable=False)
    department = Column(String(100), nullable=False)

    user = relationship("DBUser", back_populates="teacher_profile")
    subjects = relationship("DBSubject", back_populates="teacher")

class DBStudent(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    student_id = Column(String(50), unique=True, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)

    user = relationship("DBUser", back_populates="student_profile")
    class_rel = relationship("DBClass", back_populates="students")
    attendances = relationship("DBAttendance", back_populates="student")
    results = relationship("DBResult", back_populates="student")
    submissions = relationship("DBSubmission", back_populates="student")

class DBSubject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)

    class_rel = relationship("DBClass", back_populates="subjects")
    teacher = relationship("DBTeacher", back_populates="subjects")
    attendances = relationship("DBAttendance", back_populates="subject")
    results = relationship("DBResult", back_populates="subject")
    assignments = relationship("DBAssignment", back_populates="subject")
    materials = relationship("DBMaterial", back_populates="subject")

class DBAttendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    date = Column(Date, nullable=False)
    is_present = Column(Boolean, default=True, nullable=False)

    student = relationship("DBStudent", back_populates="attendances")
    subject = relationship("DBSubject", back_populates="attendances")

class DBResult(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    exam_name = Column(String(100), nullable=False)
    max_marks = Column(Float, nullable=False)
    obtained_marks = Column(Float, nullable=False)

    student = relationship("DBStudent", back_populates="results")
    subject = relationship("DBSubject", back_populates="results")

class DBAssignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=False)
    file_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    subject = relationship("DBSubject", back_populates="assignments")
    submissions = relationship("DBSubmission", back_populates="assignment")

class DBSubmission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    file_path = Column(String(255), nullable=False)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)
    remarks = Column(Text, nullable=True)

    assignment = relationship("DBAssignment", back_populates="submissions")
    student = relationship("DBStudent", back_populates="submissions")

class DBMaterial(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(150), nullable=False)
    file_path = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    subject = relationship("DBSubject", back_populates="materials")

class DBAnnouncement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True)
    title = Column(String(150), nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(String(20), default="NORMAL") # URGENT, IMPORTANT, NORMAL
    author_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class DBNotification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class DBEvent(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    event_date = Column(Date, nullable=False)
    event_time = Column(String(50), nullable=True)
    location = Column(String(100), nullable=True)
    organizer = Column(String(100), nullable=True)

class DBTimetable(Base):
    __tablename__ = "timetable"
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    day = Column(String(20), nullable=False) # Monday - Saturday
    period = Column(String(50), nullable=False) # e.g. "09:00 AM - 10:00 AM"
    subject_name = Column(String(100), nullable=False)
    teacher_name = Column(String(100), nullable=False)
    room = Column(String(50), nullable=False)

    class_rel = relationship("DBClass", back_populates="timetables")

# Setup Database Connection
@st.cache_resource
def get_db_engine():
    engine = create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine

engine = get_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    return SessionLocal()

# =========================
# AUTHENTICATION HELPERS
# =========================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def seed_demo_data():
    db = get_db()
    try:
        if db.query(DBUser).count() == 0:
            # Seed Admin
            admin_user = DBUser(
                username="admin",
                email="admin@alpha.edu",
                password_hash=hash_password("admin123"),
                role="admin",
                full_name="System Administrator",
                phone="+1-800-ALPHA"
            )
            db.add(admin_user)

            # Seed Class
            cs_class = DBClass(name="Computer Science - Year 1", code="CS-Y1")
            db.add(cs_class)
            db.commit()

            # Seed Teacher User
            teacher_user = DBUser(
                username="teacher",
                email="teacher@alpha.edu",
                password_hash=hash_password("teacher123"),
                role="teacher",
                full_name="Dr. Alan Turing",
                phone="+1-555-0101"
            )
            db.add(teacher_user)
            db.commit()

            teacher_profile = DBTeacher(
                user_id=teacher_user.id,
                employee_id="EMP-1001",
                department="Computer Science"
            )
            db.add(teacher_profile)
            db.commit()

            # Seed Student User
            student_user = DBUser(
                username="student",
                email="student@alpha.edu",
                password_hash=hash_password("student123"),
                role="student",
                full_name="Ada Lovelace",
                phone="+1-555-0102"
            )
            db.add(student_user)
            db.commit()

            student_profile = DBStudent(
                user_id=student_user.id,
                student_id="STU-2024-01",
                class_id=cs_class.id
            )
            db.add(student_profile)
            db.commit()

            # Seed Subject
            subject = DBSubject(
                name="Data Structures & Algorithms",
                code="CS101",
                class_id=cs_class.id,
                teacher_id=teacher_profile.id
            )
            db.add(subject)
            db.commit()

            # Seed Sample Announcement
            ann = DBAnnouncement(
                title="Welcome to Alpha Campus Portal",
                content="Explore your dashboard, check schedules, submission timelines, and study materials.",
                priority="IMPORTANT",
                author_name="Administrator"
            )
            db.add(ann)

            # Seed Sample Event
            evt = DBEvent(
                title="Annual Tech Symposium 2026",
                description="Join top industry experts for a 2-day conference on AI & Computing.",
                event_date=datetime.date.today() + datetime.timedelta(days=15),
                event_time="10:00 AM EST",
                location="Main Auditorium",
                organizer="Alpha Tech Club"
            )
            db.add(evt)

            # Seed Timetable
            tt = DBTimetable(
                class_id=cs_class.id,
                day="Monday",
                period="09:00 AM - 10:30 AM",
                subject_name="Data Structures & Algorithms",
                teacher_name="Dr. Alan Turing",
                room="Hall A"
            )
            db.add(tt)

            # Seed Sample Notification
            notif = DBNotification(
                user_id=student_user.id,
                message="Welcome to Alpha Campus! Check your timetable and upcoming assignments."
            )
            db.add(notif)

            db.commit()
    finally:
        db.close()

seed_demo_data()

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "role" not in st.session_state:
    st.session_state.role = None
if "username" not in st.session_state:
    st.session_state.username = None
if "full_name" not in st.session_state:
    st.session_state.full_name = None

# =========================
# CUSTOM CSS (FUTURISTIC NEON/NAVY SAAS)
# =========================
def inject_custom_css():
    st.markdown("""
    <style>
    /* Main Background & Fonts */
    .stApp {
        background: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #0d1322 100%);
        color: #f3f4f6;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0d121f !important;
        border-right: 1px solid #1f293d;
    }
    
    /* Glassmorphism Cards */
    .glass-card {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 18px;
        text-align: left;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 5px 0;
    }
    .metric-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #94a3b8;
        font-weight: 600;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #64748b;
    }

    /* Badges */
    .badge {
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-urgent { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid #ef4444; }
    .badge-important { background: rgba(245, 158, 11, 0.2); color: #fcd34d; border: 1px solid #f59e0b; }
    .badge-normal { background: rgba(59, 130, 246, 0.2); color: #93c5fd; border: 1px solid #3b82f6; }

    /* Custom Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #4338ca 0%, #6d28d9 100%);
        box-shadow: 0 0 15px rgba(124, 58, 237, 0.5);
    }

    /* Input Field Customization */
    input, select, textarea {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border-radius: 8px !important;
        border: 1px solid #334155 !important;
    }
    
    /* Headers & Dividers */
    h1, h2, h3, h4 {
        color: #f8fafc;
        font-weight: 700;
    }
    hr {
        border-color: #1e293b;
    }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# =========================
# HELPER UI COMPONENTS
# =========================
def render_metric_card(title, value, subtitle="", icon="📊"):
    st.markdown(f"""
    <div class="metric-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span class="metric-title">{title}</span>
            <span style="font-size: 1.5rem;">{icon}</span>
        </div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def render_announcement_card(ann):
    badge_class = "badge-normal"
    if ann.priority == "URGENT":
        badge_class = "badge-urgent"
    elif ann.priority == "IMPORTANT":
        badge_class = "badge-important"

    st.markdown(f"""
    <div class="glass-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
            <h4 style="margin:0; color:#f3f4f6;">{ann.title}</h4>
            <span class="badge {badge_class}">{ann.priority}</span>
        </div>
        <p style="color:#cbd5e1; font-size:0.95rem; margin-bottom: 12px;">{ann.content}</p>
        <div style="font-size:0.8rem; color:#64748b; display:flex; justify-content:space-between;">
            <span>✍️ {ann.author_name}</span>
            <span>📅 {ann.created_at.strftime('%Y-%m-%d %H:%M')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Helper function for safe file saving
def save_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return None
    ext = uploaded_file.name.split('.')[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        st.error(f"Invalid file format. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}")
        return None
    
    file_path = os.path.join(UPLOAD_DIR, f"{int(datetime.datetime.now().timestamp())}_{uploaded_file.name}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

# =========================
# AUTHENTICATION SCREEN
# =========================
def show_login_page():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="font-size: 3rem; background: linear-gradient(90deg, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🚀 ALPHA CAMPUS</h1>
            <p style="color: #94a3b8;">Next-Generation Academic Management Portal</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            st.subheader("Sign In")
            username_input = st.text_input("Username or Email")
            password_input = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login to Campus", use_container_width=True)

            if submit:
                if not username_input or not password_input:
                    st.error("Please enter both username and password.")
                else:
                    db = get_db()
                    try:
                        user = db.query(DBUser).filter(
                            (DBUser.username == username_input) | (DBUser.email == username_input)
                        ).first()

                        if user and verify_password(password_input, user.password_hash):
                            st.session_state.authenticated = True
                            st.session_state.user_id = user.id
                            st.session_state.role = user.role
                            st.session_state.username = user.username
                            st.session_state.full_name = user.full_name
                            st.toast(f"Welcome back, {user.full_name}!", icon="👋")
                            st.rerun()
                        else:
                            st.error("Invalid credentials. Please try again.")
                    finally:
                        db.close()

        # Demo Mode Info Box
        st.markdown("""
        <div style="margin-top:20px; background: rgba(30, 41, 59, 0.5); padding: 15px; border-radius: 10px; border: 1px solid #334155;">
            <p style="margin:0; font-weight:600; color:#38bdf8;">🔑 Demo Credentials:</p>
            <ul style="margin:5px 0 0 0; padding-left:20px; font-size:0.85rem; color:#94a3b8;">
                <li><b>Admin:</b> admin / admin123</li>
                <li><b>Teacher:</b> teacher / teacher123</li>
                <li><b>Student:</b> student / student123</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# =========================
# ADMIN DASHBOARD & MODULES
# =========================
def show_admin_dashboard():
    db = get_db()
    try:
        st.title("🛡️ Admin Portal")
        
        # Top Stats
        s_count = db.query(DBStudent).count()
        t_count = db.query(DBTeacher).count()
        c_count = db.query(DBClass).count()
        sub_count = db.query(DBSubject).count()

        col1, col2, col3, col4 = st.columns(4)
        with col1: render_metric_card("Total Students", s_count, "Enrolled", "🎓")
        with col2: render_metric_card("Total Teachers", t_count, "Faculty Members", "👨‍🏫")
        with col3: render_metric_card("Active Classes", c_count, "Batches", "🏫")
        with col4: render_metric_card("Total Subjects", sub_count, "Courses Offered", "📚")

        st.markdown("<hr>", unsafe_allow_html=True)

        tabs = st.tabs(["📊 Analytics", "👥 Manage Users", "🏫 Classes & Subjects", "📢 Announcements", "📅 Events", "🗓️ Timetable"])

        # Analytics Tab
        with tabs[0]:
            st.subheader("System Overview & Analytics")
            c1, c2 = st.columns(2)

            with c1:
                # Student Distribution per class
                classes = db.query(DBClass).all()
                class_data = []
                for c in classes:
                    cnt = db.query(DBStudent).filter(DBStudent.class_id == c.id).count()
                    class_data.append({"Class": c.name, "Students": cnt})
                df_class = pd.DataFrame(class_data)
                if not df_class.empty and df_class["Students"].sum() > 0:
                    fig = px.pie(df_class, names="Class", values="Students", title="Student Distribution by Class",
                                 color_discrete_sequence=px.colors.sequential.Plasma)
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f3f4f6")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No student distribution data available.")

            with c2:
                # Attendance Stats Overview
                att_records = db.query(DBAttendance).all()
                if att_records:
                    present = sum(1 for a in att_records if a.is_present)
                    absent = len(att_records) - present
                    fig_att = px.bar(x=["Present", "Absent"], y=[present, absent], labels={'x':'Status', 'y':'Count'},
                                     title="Overall Attendance Record Log", color=["Present", "Absent"],
                                     color_discrete_map={"Present":"#10b981", "Absent":"#ef4444"})
                    fig_att.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f3f4f6")
                    st.plotly_chart(fig_att, use_container_width=True)
                else:
                    st.info("No attendance records logged yet.")

        # Manage Users Tab
        with tabs[1]:
            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Manage Students", "Manage Teachers", "Create User"])
            
            with sub_tab1:
                st.subheader("Students Directory")
                students = db.query(DBStudent).all()
                stu_data = []
                for s in students:
                    stu_data.append({
                        "ID": s.id,
                        "Student Code": s.student_id,
                        "Full Name": s.user.full_name if s.user else "N/A",
                        "Email": s.user.email if s.user else "N/A",
                        "Class": s.class_rel.name if s.class_rel else "Unassigned"
                    })
                df_stu = pd.DataFrame(stu_data)
                st.dataframe(df_stu, use_container_width=True)

                st.markdown("#### Delete Student")
                del_id = st.number_input("Enter Student ID to Delete", min_value=1, step=1, key="del_stu")
                if st.button("Delete Student", key="btn_del_stu"):
                    s_to_del = db.query(DBStudent).filter(DBStudent.id == del_id).first()
                    if s_to_del:
                        user_to_del = s_to_del.user
                        db.delete(s_to_del)
                        if user_to_del:
                            db.delete(user_to_del)
                        db.commit()
                        st.success("Student removed successfully.")
                        st.rerun()
                    else:
                        st.error("Student ID not found.")

            with sub_tab2:
                st.subheader("Teachers Directory")
                teachers = db.query(DBTeacher).all()
                teach_data = []
                for t in teachers:
                    teach_data.append({
                        "ID": t.id,
                        "Employee Code": t.employee_id,
                        "Full Name": t.user.full_name if t.user else "N/A",
                        "Email": t.user.email if t.user else "N/A",
                        "Department": t.department
                    })
                df_teach = pd.DataFrame(teach_data)
                st.dataframe(df_teach, use_container_width=True)

            with sub_tab3:
                st.subheader("Add New User Account")
                with st.form("add_user_form"):
                    u_name = st.text_input("Username")
                    u_email = st.text_input("Email")
                    u_pass = st.text_input("Password", type="password")
                    u_fname = st.text_input("Full Name")
                    u_phone = st.text_input("Phone Number")
                    u_role = st.selectbox("Role", ["student", "teacher", "admin"])

                    # Dynamic extra fields
                    all_classes = db.query(DBClass).all()
                    class_opts = {c.name: c.id for c in all_classes}
                    sel_class = st.selectbox("Assign Class (If Student)", list(class_opts.keys())) if class_opts else None
                    u_dept = st.text_input("Department (If Teacher)", value="Computer Science")
                    
                    submitted = st.form_submit_button("Create Account")
                    if submitted:
                        if not u_name or not u_email or not u_pass or not u_fname:
                            st.error("Please fill in all mandatory fields.")
                        else:
                            try:
                                new_u = DBUser(
                                    username=u_name,
                                    email=u_email,
                                    password_hash=hash_password(u_pass),
                                    role=u_role,
                                    full_name=u_fname,
                                    phone=u_phone
                                )
                                db.add(new_u)
                                db.commit()

                                if u_role == "student":
                                    c_id = class_opts.get(sel_class) if sel_class else None
                                    new_s = DBStudent(user_id=new_u.id, student_id=f"STU-{new_u.id:04d}", class_id=c_id)
                                    db.add(new_s)
                                elif u_role == "teacher":
                                    new_t = DBTeacher(user_id=new_u.id, employee_id=f"EMP-{new_u.id:04d}", department=u_dept)
                                    db.add(new_t)
                                
                                db.commit()
                                st.success(f"User '{u_name}' created successfully as {u_role}!")
                                st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"Error creating user: {e}")

        # Classes & Subjects Tab
        with tabs[2]:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Classes Management")
                classes = db.query(DBClass).all()
                st.dataframe(pd.DataFrame([{"ID": c.id, "Class Name": c.name, "Code": c.code} for c in classes]), use_container_width=True)
                
                with st.form("add_class_form"):
                    st.markdown("##### Create Class")
                    c_name = st.text_input("Class Name")
                    c_code = st.text_input("Class Code")
                    if st.form_submit_button("Add Class"):
                        if c_name and c_code:
                            db.add(DBClass(name=c_name, code=c_code))
                            db.commit()
                            st.success("Class added!")
                            st.rerun()

            with c2:
                st.subheader("Subjects Management")
                subjects = db.query(DBSubject).all()
                st.dataframe(pd.DataFrame([{
                    "ID": s.id, "Subject": s.name, "Code": s.code,
                    "Class": s.class_rel.name if s.class_rel else "N/A",
                    "Teacher": s.teacher.user.full_name if s.teacher and s.teacher.user else "Unassigned"
                } for s in subjects]), use_container_width=True)

                with st.form("add_sub_form"):
                    st.markdown("##### Create Subject")
                    sub_name = st.text_input("Subject Name")
                    sub_code = st.text_input("Subject Code")
                    all_c = db.query(DBClass).all()
                    all_t = db.query(DBTeacher).all()
                    sel_c = st.selectbox("Class", [c.name for c in all_c]) if all_c else None
                    sel_t = st.selectbox("Teacher", [t.user.full_name for t in all_t if t.user]) if all_t else None

                    if st.form_submit_button("Add Subject"):
                        if sub_name and sub_code and sel_c:
                            c_obj = db.query(DBClass).filter(DBClass.name == sel_c).first()
                            t_obj = None
                            if sel_t:
                                t_user = db.query(DBUser).filter(DBUser.full_name == sel_t).first()
                                if t_user: t_obj = t_user.teacher_profile
                            
                            db.add(DBSubject(
                                name=sub_name, code=sub_code,
                                class_id=c_obj.id, teacher_id=t_obj.id if t_obj else None
                            ))
                            db.commit()
                            st.success("Subject created successfully!")
                            st.rerun()

        # Announcements Tab
        with tabs[3]:
            st.subheader("Broadcast System Announcement")
            with st.form("new_ann_form"):
                a_title = st.text_input("Title")
                a_content = st.text_area("Content")
                a_prio = st.selectbox("Priority", ["NORMAL", "IMPORTANT", "URGENT"])
                if st.form_submit_button("Publish Announcement"):
                    if a_title and a_content:
                        db.add(DBAnnouncement(
                            title=a_title, content=a_content, priority=a_prio,
                            author_name=st.session_state.full_name
                        ))
                        db.commit()
                        st.success("Announcement broadcasted!")
                        st.rerun()

            st.markdown("#### Recent Broadcasts")
            anns = db.query(DBAnnouncement).order_by(DBAnnouncement.created_at.desc()).all()
            for a in anns:
                render_announcement_card(a)

        # Events Tab
        with tabs[4]:
            st.subheader("Create Campus Event")
            with st.form("event_form"):
                e_title = st.text_input("Event Title")
                e_desc = st.text_area("Description")
                e_date = st.date_input("Event Date", datetime.date.today())
                e_time = st.text_input("Time (e.g. 10:00 AM)")
                e_loc = st.text_input("Location")
                e_org = st.text_input("Organizer")
                if st.form_submit_button("Post Event"):
                    if e_title:
                        db.add(DBEvent(
                            title=e_title, description=e_desc, event_date=e_date,
                            event_time=e_time, location=e_loc, organizer=e_org
                        ))
                        db.commit()
                        st.success("Event created!")
                        st.rerun()

        # Timetable Tab
        with tabs[5]:
            st.subheader("Add Timetable Entry")
            with st.form("tt_form"):
                all_c = db.query(DBClass).all()
                c_opts = {c.name: c.id for c in all_c}
                sel_c = st.selectbox("Select Class", list(c_opts.keys())) if c_opts else None
                day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
                period = st.text_input("Period Slot (e.g. 09:00 AM - 10:00 AM)")
                s_name = st.text_input("Subject Name")
                t_name = st.text_input("Teacher Name")
                room = st.text_input("Room No / Hall")
                if st.form_submit_button("Save Timetable Slot"):
                    if sel_c and period and s_name:
                        db.add(DBTimetable(
                            class_id=c_opts[sel_c], day=day, period=period,
                            subject_name=s_name, teacher_name=t_name, room=room
                        ))
                        db.commit()
                        st.success("Timetable slot created!")
                        st.rerun()

    finally:
        db.close()

# =========================
# TEACHER DASHBOARD & MODULES
# =========================
def show_teacher_dashboard():
    db = get_db()
    try:
        user_id = st.session_state.user_id
        teacher = db.query(DBTeacher).filter(DBTeacher.user_id == user_id).first()

        if not teacher:
            st.error("Teacher profile context not found.")
            return

        st.title(f"👨‍🏫 Teacher Dashboard — Welcome, {st.session_state.full_name}")

        subjects = db.query(DBSubject).filter(DBSubject.teacher_id == teacher.id).all()
        sub_count = len(subjects)
        
        col1, col2, col3 = st.columns(3)
        with col1: render_metric_card("Assigned Subjects", sub_count, "Active Courses", "📖")
        with col2: render_metric_card("Department", teacher.department, "Faculty", "🏢")
        with col3: render_metric_card("Employee ID", teacher.employee_id, "Official Badge", "🆔")

        st.markdown("<hr>", unsafe_allow_html=True)

        tabs = st.tabs(["✅ Attendance Marking", "📝 Results & Grades", "📚 Assignments", "📁 Materials", "📢 Announcements"])

        # Attendance Marking Tab
        with tabs[0]:
            st.subheader("Mark Student Attendance")
            if not subjects:
                st.warning("You have not been assigned any subjects yet.")
            else:
                sub_opts = {f"{s.name} ({s.class_rel.name})": s for s in subjects}
                sel_sub_label = st.selectbox("Select Subject & Class", list(sub_opts.keys()))
                sel_sub = sub_opts[sel_sub_label]

                att_date = st.date_input("Attendance Date", datetime.date.today())

                students = db.query(DBStudent).filter(DBStudent.class_id == sel_sub.class_id).all()
                if not students:
                    st.info("No students enrolled in this class.")
                else:
                    with st.form("attendance_form"):
                        st.markdown(f"**Mark Attendance for {sel_sub.name} on {att_date}**")
                        att_status = {}
                        for stu in students:
                            stu_name = stu.user.full_name if stu.user else stu.student_id
                            att_status[stu.id] = st.checkbox(f"{stu_name} ({stu.student_id})", value=True)
                        
                        if st.form_submit_button("Save Attendance"):
                            for stu_id, is_pres in att_status.items():
                                # Check existing record
                                existing = db.query(DBAttendance).filter(
                                    DBAttendance.student_id == stu_id,
                                    DBAttendance.subject_id == sel_sub.id,
                                    DBAttendance.date == att_date
                                ).first()
                                if existing:
                                    existing.is_present = is_pres
                                else:
                                    db.add(DBAttendance(
                                        student_id=stu_id,
                                        subject_id=sel_sub.id,
                                        date=att_date,
                                        is_present=is_pres
                                    ))
                            db.commit()
                            st.success("Attendance saved successfully!")

        # Results & Grades Tab
        with tabs[1]:
            st.subheader("Enter Exam Results")
            if subjects:
                sub_opts = {f"{s.name} ({s.class_rel.name})": s for s in subjects}
                sel_sub_label = st.selectbox("Subject Context", list(sub_opts.keys()), key="res_sub")
                sel_sub = sub_opts[sel_sub_label]

                exam_name = st.text_input("Exam Name (e.g., Midterm Exam, Final Assessment)")
                max_m = st.number_input("Maximum Marks", value=100.0)

                students = db.query(DBStudent).filter(DBStudent.class_id == sel_sub.class_id).all()
                if students and exam_name:
                    with st.form("results_form"):
                        marks_dict = {}
                        for stu in students:
                            stu_name = stu.user.full_name if stu.user else stu.student_id
                            marks_dict[stu.id] = st.number_input(f"Obtained Marks: {stu_name}", min_value=0.0, max_value=float(max_m), value=0.0)
                        
                        if st.form_submit_button("Record Results"):
                            for stu_id, obt in marks_dict.items():
                                db.add(DBResult(
                                    student_id=stu_id,
                                    subject_id=sel_sub.id,
                                    exam_name=exam_name,
                                    max_marks=max_m,
                                    obtained_marks=obt
                                ))
                            db.commit()
                            st.success("Exam results submitted successfully!")

        # Assignments Tab
        with tabs[2]:
            st.subheader("Create New Assignment")
            if subjects:
                sub_opts = {s.name: s.id for s in subjects}
                sel_s_id = st.selectbox("Subject", list(sub_opts.keys()), key="ass_sub")
                a_title = st.text_input("Assignment Title")
                a_desc = st.text_area("Instructions / Details")
                a_deadline = st.date_input("Deadline", datetime.date.today() + datetime.timedelta(days=7))
                a_file = st.file_uploader("Attach Document/Instructions (Optional)", key="ass_file")

                if st.button("Publish Assignment"):
                    if a_title:
                        file_p = save_uploaded_file(a_file) if a_file else None
                        db.add(DBAssignment(
                            subject_id=sub_opts[sel_s_id],
                            title=a_title,
                            description=a_desc,
                            deadline=datetime.datetime.combine(a_deadline, datetime.time(23, 59)),
                            file_path=file_p
                        ))
                        db.commit()
                        st.success("Assignment created!")
                        st.rerun()

        # Materials Tab
        with tabs[3]:
            st.subheader("Upload Study Material")
            if subjects:
                sub_opts = {s.name: s.id for s in subjects}
                sel_s_id = st.selectbox("Subject", list(sub_opts.keys()), key="mat_sub")
                m_title = st.text_input("Resource Title")
                m_file = st.file_uploader("Upload File (PDF, DOCX, PPTX, etc.)", key="mat_file")

                if st.button("Upload Material"):
                    if m_title and m_file:
                        file_p = save_uploaded_file(m_file)
                        if file_p:
                            db.add(DBMaterial(
                                subject_id=sub_opts[sel_s_id],
                                title=m_title,
                                file_path=file_p
                            ))
                            db.commit()
                            st.success("Study material uploaded!")
                            st.rerun()

        # Announcements Tab
        with tabs[4]:
            st.subheader("Post Class Announcement")
            with st.form("t_ann_form"):
                a_title = st.text_input("Title")
                a_content = st.text_area("Message")
                a_prio = st.selectbox("Priority", ["NORMAL", "IMPORTANT", "URGENT"])
                if st.form_submit_button("Publish Announcement"):
                    if a_title and a_content:
                        db.add(DBAnnouncement(
                            title=a_title, content=a_content, priority=a_prio,
                            author_name=st.session_state.full_name
                        ))
                        db.commit()
                        st.success("Announcement published!")
                        st.rerun()

    finally:
        db.close()

# =========================
# STUDENT DASHBOARD & MODULES
# =========================
def show_student_dashboard():
    db = get_db()
    try:
        user_id = st.session_state.user_id
        student = db.query(DBStudent).filter(DBStudent.user_id == user_id).first()

        if not student:
            st.error("Student profile context not found.")
            return

        st.title(f"🎓 Welcome, {st.session_state.full_name}")

        # Metrics calculations
        att_records = db.query(DBAttendance).filter(DBAttendance.student_id == student.id).all()
        att_pct = "N/A"
        if att_records:
            present_cnt = sum(1 for a in att_records if a.is_present)
            att_pct = f"{(present_cnt / len(att_records)) * 100:.1f}%"

        results = db.query(DBResult).filter(DBResult.student_id == student.id).all()
        avg_grade = "N/A"
        if results:
            tot_pct = sum((r.obtained_marks / r.max_marks) * 100 for r in results if r.max_marks > 0)
            avg_grade = f"{(tot_pct / len(results)):.1f}%"

        class_name = student.class_rel.name if student.class_rel else "Unassigned"

        col1, col2, col3, col4 = st.columns(4)
        with col1: render_metric_card("Class / Batch", class_name, "Registered Class", "🏫")
        with col2: render_metric_card("Attendance Rate", att_pct, "Overall Attendance", "📈")
        with col3: render_metric_card("Average Grade", avg_grade, "Academic Performance", "🏅")
        with col4: render_metric_card("Student ID", student.student_id, "Official Roll No", "🆔")

        st.markdown("<hr>", unsafe_allow_html=True)

        tabs = st.tabs(["📊 Attendance Details", "📑 Academic Results", "📝 Assignments", "📚 Study Materials", "🗓️ Class Timetable", "📅 Events"])

        # Attendance Details
        with tabs[0]:
            st.subheader("Attendance History")
            if not att_records:
                st.info("No attendance records logged yet.")
            else:
                data = [{
                    "Date": a.date,
                    "Subject": a.subject.name if a.subject else "N/A",
                    "Status": "Present ✅" if a.is_present else "Absent ❌"
                } for a in att_records]
                st.dataframe(pd.DataFrame(data), use_container_width=True)

        # Academic Results
        with tabs[1]:
            st.subheader("My Examination Results")
            if not results:
                st.info("No exam results published yet.")
            else:
                res_data = []
                for r in results:
                    pct = (r.obtained_marks / r.max_marks) * 100
                    grade = "A+" if pct >= 90 else "A" if pct >= 80 else "B" if pct >= 70 else "C" if pct >= 60 else "F"
                    res_data.append({
                        "Exam": r.exam_name,
                        "Subject": r.subject.name if r.subject else "N/A",
                        "Obtained": r.obtained_marks,
                        "Max Marks": r.max_marks,
                        "Percentage": f"{pct:.1f}%",
                        "Grade": grade
                    })
                df_res = pd.DataFrame(res_data)
                st.dataframe(df_res, use_container_width=True)

                fig = px.bar(df_res, x="Exam", y="Obtained", color="Subject", title="Exam Performance Breakdown")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f3f4f6")
                st.plotly_chart(fig, use_container_width=True)

        # Assignments
        with tabs[2]:
            st.subheader("Pending & Active Assignments")
            if student.class_id:
                subjects = db.query(DBSubject).filter(DBSubject.class_id == student.class_id).all()
                sub_ids = [s.id for s in subjects]
                assignments = db.query(DBAssignment).filter(DBAssignment.subject_id.in_(sub_ids)).all()

                if not assignments:
                    st.info("No assignments assigned.")
                else:
                    for ass in assignments:
                        subm = db.query(DBSubmission).filter(
                            DBSubmission.assignment_id == ass.id,
                            DBSubmission.student_id == student.id
                        ).first()

                        st.markdown(f"""
                        <div class="glass-card">
                            <h4>{ass.title} ({ass.subject.name})</h4>
                            <p>{ass.description}</p>
                            <p style="font-size:0.85rem; color:#f59e0b;">⏳ Deadline: {ass.deadline.strftime('%Y-%m-%d %H:%M')}</p>
                            <p><b>Status:</b> {'Submitted ✅' if subm else 'Pending ⌛'}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        if ass.file_path and os.path.exists(ass.file_path):
                            with open(ass.file_path, "rb") as f:
                                st.download_button("Download Attachment", f, file_name=os.path.basename(ass.file_path), key=f"dl_ass_{ass.id}")

                        if not subm:
                            up_file = st.file_uploader(f"Submit Assignment for {ass.title}", key=f"up_{ass.id}")
                            if st.button("Submit Work", key=f"sub_btn_{ass.id}"):
                                if up_file:
                                    f_p = save_uploaded_file(up_file)
                                    if f_p:
                                        db.add(DBSubmission(
                                            assignment_id=ass.id,
                                            student_id=student.id,
                                            file_path=f_p
                                        ))
                                        db.commit()
                                        st.success("Assignment submitted successfully!")
                                        st.rerun()

        # Study Materials
        with tabs[3]:
            st.subheader("Available Course Materials")
            if student.class_id:
                subjects = db.query(DBSubject).filter(DBSubject.class_id == student.class_id).all()
                sub_ids = [s.id for s in subjects]
                materials = db.query(DBMaterial).filter(DBMaterial.subject_id.in_(sub_ids)).all()

                if not materials:
                    st.info("No course materials published yet.")
                else:
                    for mat in materials:
                        st.markdown(f"📄 **{mat.title}** ({mat.subject.name})")
                        if os.path.exists(mat.file_path):
                            with open(mat.file_path, "rb") as f:
                                st.download_button("Download File", f, file_name=os.path.basename(mat.file_path), key=f"dl_mat_{mat.id}")

        # Timetable
        with tabs[4]:
            st.subheader("Class Schedule")
            if student.class_id:
                tt_entries = db.query(DBTimetable).filter(DBTimetable.class_id == student.class_id).all()
                if not tt_entries:
                    st.info("Timetable not yet configured for your class.")
                else:
                    df_tt = pd.DataFrame([{
                        "Day": t.day,
                        "Period": t.period,
                        "Subject": t.subject_name,
                        "Teacher": t.teacher_name,
                        "Room": t.room
                    } for t in tt_entries])
                    st.dataframe(df_tt, use_container_width=True)

        # Events
        with tabs[5]:
            st.subheader("Campus Events")
            events = db.query(DBEvent).order_by(DBEvent.event_date.asc()).all()
            for e in events:
                st.markdown(f"""
                <div class="glass-card">
                    <h4>{e.title}</h4>
                    <p>{e.description}</p>
                    <p style="font-size:0.85rem; color:#a78bfa;">📅 Date: {e.event_date} | ⏰ Time: {e.event_time} | 📍 Location: {e.location}</p>
                    <p style="font-size:0.8rem; color:#64748b;">Organizer: {e.organizer}</p>
                </div>
                """, unsafe_allow_html=True)

    finally:
        db.close()

# =========================
# COMMON MODULES (SEARCH, PROFILE, NOTIFICATIONS)
# =========================
def show_search_page():
    st.title("🔍 Global Campus Search")
    query = st.text_input("Enter keywords to search students, teachers, announcements, or events:")
    
    if query:
        db = get_db()
        try:
            st.markdown("### Search Results")

            # Search Announcements
            anns = db.query(DBAnnouncement).filter(
                (DBAnnouncement.title.contains(query)) | (DBAnnouncement.content.contains(query))
            ).all()
            if anns:
                st.markdown("#### Announcements")
                for a in anns:
                    render_announcement_card(a)

            # Search Events
            evts = db.query(DBEvent).filter(
                (DBEvent.title.contains(query)) | (DBEvent.description.contains(query))
            ).all()
            if evts:
                st.markdown("#### Events")
                for e in evts:
                    st.info(f"📅 **{e.title}** ({e.event_date}) - {e.description}")

            # Search Users (Admin/Teacher view)
            if st.session_state.role in ['admin', 'teacher']:
                users = db.query(DBUser).filter(
                    (DBUser.full_name.contains(query)) | (DBUser.username.contains(query)) | (DBUser.email.contains(query))
                ).all()
                if users:
                    st.markdown("#### Users / Accounts")
                    st.dataframe(pd.DataFrame([{
                        "Name": u.full_name, "Role": u.role, "Email": u.email, "Username": u.username
                    } for u in users]), use_container_width=True)

        finally:
            db.close()

def show_profile_page():
    st.title("👤 Profile & Settings")
    db = get_db()
    try:
        user = db.query(DBUser).filter(DBUser.id == st.session_state.user_id).first()
        if user:
            st.markdown(f"""
            <div class="glass-card">
                <h3>{user.full_name}</h3>
                <p><b>Role:</b> {user.role.capitalize()}</p>
                <p><b>Username:</b> {user.username}</p>
                <p><b>Email:</b> {user.email}</p>
                <p><b>Phone:</b> {user.phone if user.phone else 'Not provided'}</p>
            </div>
            """, unsafe_allow_html=True)

            with st.form("profile_update_form"):
                st.subheader("Update Information")
                new_fname = st.text_input("Full Name", value=user.full_name)
                new_phone = st.text_input("Phone Number", value=user.phone if user.phone else "")
                new_pass = st.text_input("New Password (leave blank to keep current)", type="password")

                if st.form_submit_button("Update Profile"):
                    user.full_name = new_fname
                    user.phone = new_phone
                    if new_pass:
                        user.password_hash = hash_password(new_pass)
                    db.commit()
                    st.session_state.full_name = new_fname
                    st.success("Profile updated successfully!")
                    st.rerun()
    finally:
        db.close()

def show_notifications_page():
    st.title("🔔 Notifications Center")
    db = get_db()
    try:
        user_id = st.session_state.user_id
        notifs = db.query(DBNotification).filter(DBNotification.user_id == user_id).order_by(DBNotification.created_at.desc()).all()

        if st.button("Mark All as Read"):
            for n in notifs:
                n.is_read = True
            db.commit()
            st.rerun()

        if not notifs:
            st.info("No notifications at this time.")
        else:
            for n in notifs:
                status = "Read" if n.is_read else "🆕 New"
                st.markdown(f"""
                <div class="glass-card">
                    <div style="display:flex; justify-mode:space-between; align-items:center;">
                        <span style="font-weight:600;">{n.message}</span>
                        <span style="font-size:0.8rem; color:#64748b;">{status}</span>
                    </div>
                    <div style="font-size:0.75rem; color:#64748b; margin-top:5px;">{n.created_at.strftime('%Y-%m-%d %H:%M')}</div>
                </div>
                """, unsafe_allow_html=True)
    finally:
        db.close()

# =========================
# MAIN NAVIGATION & APPLICATION
# =========================
def main():
    if not st.session_state.authenticated:
        show_login_page()
    else:
        # Sidebar Navigation
        with st.sidebar:
            st.markdown("""
            <div style="text-align: center; padding: 10px 0;">
                <h2 style="color: #60a5fa; margin: 0;">🚀 ALPHA CAMPUS</h2>
                <p style="font-size: 0.8rem; color: #94a3b8;">Portal System</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<hr>", unsafe_allow_html=True)

            # Display Logged-in User Info
            st.markdown(f"👤 **{st.session_state.full_name}**")
            st.markdown(f"🏷️ *Role: {st.session_state.role.capitalize()}*")
            st.markdown("<hr>", unsafe_allow_html=True)

            # Navigation Menu Options
            menu_options = ["Dashboard", "Global Search", "Notifications", "My Profile"]
            nav_choice = st.radio("Navigation", menu_options)

            st.markdown("<hr>", unsafe_allow_html=True)
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user_id = None
                st.session_state.role = None
                st.session_state.username = None
                st.session_state.full_name = None
                st.rerun()

        # Render Core Screens based on selection
        if nav_choice == "Dashboard":
            if st.session_state.role == "admin":
                show_admin_dashboard()
            elif st.session_state.role == "teacher":
                show_teacher_dashboard()
            elif st.session_state.role == "student":
                show_student_dashboard()
        elif nav_choice == "Global Search":
            show_search_page()
        elif nav_choice == "Notifications":
            show_notifications_page()
        elif nav_choice == "My Profile":
            show_profile_page()

if __name__ == "__main__":
    main()
