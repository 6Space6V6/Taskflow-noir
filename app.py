from flask import Flask, render_template, request, jsonify, session, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from collections import defaultdict
from sqlalchemy import func, case, text
from sqlalchemy.orm import joinedload
import os
import random
import json
import csv
import io
import calendar

app = Flask(__name__)

# إعداد قاعدة البيانات
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'todo_noir.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'taskflow-noir-secret-key-2026'
db = SQLAlchemy(app)

# --- النماذج (Models) ---

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text, nullable=True, default='')
    category = db.Column(db.String(50), default="General")
    priority = db.Column(db.String(20), default="Normal")
    due_date = db.Column(db.Date, nullable=True)
    is_archived = db.Column(db.Boolean, default=False)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    order_index = db.Column(db.Integer, default=0)
    tags = db.Column(db.String(300), nullable=True, default='')
    subtasks = db.relationship('SubTask', backref='parent_project', cascade="all, delete-orphan", lazy=True, order_by="SubTask.order_index")

    @property
    def progress(self):
        all_subs = [s for s in self.subtasks if not s.is_side_project]
        if not all_subs:
            return 0
        completed = len([s for s in all_subs if s.is_completed])
        return int((completed / len(all_subs)) * 100)
    
    @property
    def is_overdue(self):
        if self.due_date and not self.is_archived:
            return self.due_date < date.today()
        return False
    
    @property
    def days_remaining(self):
        if self.due_date and not self.is_archived:
            delta = self.due_date - date.today()
            return delta.days
        return None
    
    @property
    def tags_list(self):
        if not self.tags or self.tags.strip() == '':
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

class SubTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    order_index = db.Column(db.Integer, default=0)
    parent_id = db.Column(db.Integer, db.ForeignKey('sub_task.id', ondelete='CASCADE'), nullable=True)
    is_side_project = db.Column(db.Boolean, default=False, nullable=False)
    children = db.relationship('SubTask', backref=db.backref('parent', remote_side=[id]), cascade="all, delete-orphan")

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=True)

class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class TaskTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default="General")
    priority = db.Column(db.String(20), default="Normal")
    tags = db.Column(db.String(300), nullable=True, default='')
    notes = db.Column(db.Text, nullable=True, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    template_subtasks = db.relationship('TemplateSubTask', backref='parent_template', cascade="all, delete-orphan", lazy=True)

class TemplateSubTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('task_template.id'), nullable=False)

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)

class DailyActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    tasks_completed = db.Column(db.Integer, default=0)

class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(50), default='fas fa-dumbbell')
    color = db.Column(db.String(20), default='#ffffff')
    notes = db.Column(db.Text, nullable=True)
    group_name = db.Column(db.String(50), default='General')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    best_streak = db.Column(db.Integer, default=0)
    order_index = db.Column(db.Integer, default=0)
    entries = db.relationship('HabitEntry', backref='habit', cascade="all, delete-orphan", lazy=True)

class HabitEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    __table_args__ = (db.UniqueConstraint('habit_id', 'date', name='_habit_date_uc'),)

class InboxItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    subtasks_json = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    planned_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_converted = db.Column(db.Boolean, default=False)

class AIPrompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    prompt_text = db.Column(db.Text, nullable=False)
    example_input = db.Column(db.Text, nullable=True)
    example_output = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), default="General")
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# إنشاء الجداول
with app.app_context():
    db.create_all()
    
    # Robust Migrations for Habit table
    inspector = db.inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('habit')]
    
    if 'notes' not in columns:
        db.session.execute(text('ALTER TABLE habit ADD COLUMN notes TEXT;'))
    if 'group_name' not in columns:
        db.session.execute(text("ALTER TABLE habit ADD COLUMN group_name VARCHAR(50) DEFAULT 'General';"))
    if 'order_index' not in columns:
        db.session.execute(text("ALTER TABLE habit ADD COLUMN order_index INTEGER DEFAULT 0;"))
        
    db.session.commit()
    
    # Robust Migrations for SubTask table
    columns_subtask = [c['name'] for c in inspector.get_columns('sub_task')]
    if 'parent_id' not in columns_subtask:
        try:
            db.session.execute(text('ALTER TABLE sub_task ADD COLUMN parent_id INTEGER REFERENCES sub_task(id) ON DELETE CASCADE;'))
            db.session.commit()
        except Exception as e:
            print(f"Migration error parent_id: {e}")
            db.session.rollback()
    if 'is_side_project' not in columns_subtask:
        try:
            db.session.execute(text('ALTER TABLE sub_task ADD COLUMN is_side_project BOOLEAN DEFAULT 0;'))
            db.session.commit()
        except Exception as e:
            print(f"Migration error is_side_project: {e}")
            db.session.rollback()

    # Robust Migrations for InboxItem table
    try:
        columns_inbox = [c['name'] for c in inspector.get_columns('inbox_item')]
        if 'planned_date' not in columns_inbox:
            db.session.execute(text('ALTER TABLE inbox_item ADD COLUMN planned_date DATE;'))
            db.session.commit()
    except Exception as e:
        print(f"Migration error inbox_item planned_date: {e}")
        db.session.rollback()
    
    # إعدادات افتراضية
    default_settings = {
        'auto_archive': 'false',
        'notifications': 'true',
        'default_view': 'all',
        'theme_color': '#ffffff',
        'font_size': 'medium',
        'sort_order': 'priority'
    }
    for key, value in default_settings.items():
        if not Settings.query.filter_by(key=key).first():
            db.session.add(Settings(key=key, value=value))
    
    # اقتباسات افتراضية
    if Quote.query.count() == 0:
        default_quotes = [
            "Focus on the task, ignore the noise.",
            "Execute with precision.",
            "Silence is the best response to chaos.",
            "Discipline is the bridge between goals and accomplishment.",
            "Small steps every day lead to big results.",
            "Done is better than perfect."
        ]
        for q in default_quotes:
            db.session.add(Quote(text=q))
    
    # قوالب افتراضية
    if TaskTemplate.query.count() == 0:
        t1 = TaskTemplate(name="Team Meeting", category="Work", priority="High", 
                         tags="meeting, work, team",
                         notes="Prepare agenda\nTake notes\nFollow up on action items")
        db.session.add(t1)
        db.session.flush()
        db.session.add(TemplateSubTask(title="Prepare agenda", template_id=t1.id))
        db.session.add(TemplateSubTask(title="Send meeting invite", template_id=t1.id))
        db.session.add(TemplateSubTask(title="Take meeting notes", template_id=t1.id))
        
        t2 = TaskTemplate(name="Grocery Shopping", category="Personal", priority="Normal",
                         tags="shopping, personal",
                         notes="Check pantry first\nStick to the list")
        db.session.add(t2)
        db.session.flush()
        db.session.add(TemplateSubTask(title="Make shopping list", template_id=t2.id))
        db.session.add(TemplateSubTask(title="Check fridge", template_id=t2.id))
        db.session.add(TemplateSubTask(title="Go to supermarket", template_id=t2.id))

    # قوالب الذكاء الاصطناعي الافتراضية
    if AIPrompt.query.count() == 0:
        default_prompts = [
            {
                'name': '📥 JSON Import',
                'description': 'Convert any text to TaskFlow JSON format for import',
                'category': 'Import',
                'prompt_text': '''You are an AI assistant. Convert the text below to a JSON array of tasks.

Each task object can have:
- "title" (string, required)
- "subtasks" (array of strings, optional)
- "notes" (string, optional)

Output ONLY valid JSON. No explanations, no markdown formatting.

Text to convert:
"""
{{user_text}}
"""'''
            },
            {
                'name': '📝 Meeting Notes to Tasks',
                'description': 'Extract action items from meeting notes',
                'category': 'Extract',
                'prompt_text': '''Extract all action items from these meeting notes.

Output as JSON array. Each item has "title" and "assigned_to" (if mentioned in the notes).

Meeting notes:
"""
{{user_text}}
"""'''
            },
            {
                'name': '🧠 Brain Dump Organizer',
                'description': 'Organize scattered thoughts into structured tasks',
                'category': 'Organize',
                'prompt_text': '''Organize this brain dump into a structured task list.

Group related items as subtasks under main tasks. Output as JSON array where each task has "title" and optional "subtasks" array.

Brain dump:
"""
{{user_text}}
"""'''
            },
            {
                'name': '🔨 Subtask Generator',
                'description': 'Break down a big task into small actionable subtasks',
                'category': 'Generate',
                'prompt_text': '''Break down this task into 5-10 small, actionable subtasks.

Output as JSON array of strings.

Task:
"""
{{user_text}}
"""'''
            }
        ]
        for p in default_prompts:
            db.session.add(AIPrompt(
                name=p['name'],
                description=p['description'],
                prompt_text=p['prompt_text'],
                category=p['category'],
                order_index=default_prompts.index(p)
            ))

    db.session.commit()

# --- Context Processor ---

@app.context_processor
def inject_globals():
    active_quotes = Quote.query.filter_by(is_active=True).all()
    daily_quote = random.choice(active_quotes).text if active_quotes else "Stay focused."
    
    settings = {s.key: s.value for s in Settings.query.all()}
    achievements = {a.key: a.unlocked_at for a in Achievement.query.all()}
    streak = calculate_streak()
    templates = TaskTemplate.query.all()
    
    # Habit counts for Today
    today = date.today()
    total_habits = Habit.query.count()
    completed_habits = HabitEntry.query.filter_by(date=today, completed=True).count()
    
    return dict(
        today_date=today,
        daily_quote=daily_quote,
        settings=settings,
        achievements=achievements,
        streak=streak,
        templates=templates,
        habits_today_done=completed_habits,
        habits_today_total=total_habits,
        str=str,
        timedelta=timedelta,
        len=len,
        range=range,
        int=int
    )

# --- Helper Functions ---

def get_setting(key, default=None):
    setting = Settings.query.filter_by(key=key).first()
    return setting.value if setting else default

def check_auto_archive(project):
    auto_archive = get_setting('auto_archive', 'false')
    if auto_archive == 'true':
        if project.subtasks and all(s.is_completed for s in project.subtasks):
            project.is_archived = True
            project.is_completed = True
            project.completed_at = datetime.utcnow()
            db.session.commit()
            return True
    return False

def calculate_streak():
    today = date.today()
    streak = 0
    current = today
    
    while True:
        activity = DailyActivity.query.filter_by(date=current).first()
        if activity and activity.tasks_completed > 0:
            streak += 1
            current -= timedelta(days=1)
        else:
            if current == today:
                break
            else:
                break
    
    return streak

def record_activity():
    today = date.today()
    activity = DailyActivity.query.filter_by(date=today).first()
    if activity:
        activity.tasks_completed += 1
    else:
        db.session.add(DailyActivity(date=today, tasks_completed=1))
    
    check_achievements()

def check_achievements():
    total_completed = Project.query.filter_by(is_archived=True).count()
    total_created = Project.query.count()
    streak = calculate_streak()
    
    achievements_to_check = {
        'first_task': total_created >= 1,
        'five_tasks': total_created >= 5,
        'ten_tasks': total_completed >= 10,
        'twenty_tasks': total_completed >= 20,
        'streak_3': streak >= 3,
        'streak_7': streak >= 7,
        'streak_30': streak >= 30,
    }
    
    for key, unlocked in achievements_to_check.items():
        if unlocked and not Achievement.query.filter_by(key=key).first():
            db.session.add(Achievement(key=key))

def get_all_tags():
    # Efficient distinct tag extraction
    tag_rows = db.session.query(Project.tags).filter(Project.tags != None, Project.tags != '').all()
    tags_set = set()
    for row in tag_rows:
        for tag in row[0].split(','):
            t = tag.strip()
            if t:
                tags_set.add(t)
    return sorted(list(tags_set))

# --- المسارات (Routes) ---

@app.route('/')
def index():
    sort_order = get_setting('sort_order', 'manual') # Default to manual for better UX
    
    if sort_order == 'priority':
        projects = Project.query.filter_by(is_archived=False).options(joinedload(Project.subtasks)).order_by(
            case(
                (Project.priority == 'Urgent', 0),
                (Project.priority == 'High', 1),
                else_=2
            ),
            Project.due_date.asc()
        ).all()
    elif sort_order == 'manual':
        projects = Project.query.filter_by(is_archived=False).options(joinedload(Project.subtasks)).order_by(Project.order_index.asc()).all()
    else:
        projects = Project.query.filter_by(is_archived=False).options(joinedload(Project.subtasks)).order_by(Project.created_at.desc()).all()
    
    default_view = get_setting('default_view', 'all')
    templates = TaskTemplate.query.all()
    available_tags = get_all_tags()
    
    return render_template('index.html', 
                         projects=projects, 
                         default_view=default_view,
                         templates=templates,
                         available_tags=available_tags)

@app.route('/get_task_row/<int:id>')
def get_task_row(id):
    project = Project.query.get_or_404(id)
    return render_template('partials/task_row.html', project=project)

@app.route('/get_dashboard_stats')
def get_dashboard_stats():
    today = date.today()
    total_habits = Habit.query.count()
    completed_habits = HabitEntry.query.filter_by(date=today, completed=True).count()
    
    projects = Project.query.filter_by(is_archived=False).all()
    total_progress = 0
    if projects:
        total_progress = sum(p.progress for p in projects) // len(projects)
        
    return jsonify({
        "success": True,
        "overall_progress": total_progress,
        "habits_today_done": completed_habits,
        "habits_today_total": total_habits
    })

@app.route('/archive')
def archive_view():
    # Use joinedload for subtasks to avoid N+1 queries
    archived_projects = Project.query.filter_by(is_archived=True)\
        .options(joinedload(Project.subtasks))\
        .order_by(Project.completed_at.desc()).all()
    
    # Group by date
    folders_map = defaultdict(list)
    for p in archived_projects:
        if p.completed_at:
            # Group by date part only
            date_key = p.completed_at.date().isoformat()
            folders_map[date_key].append(p)
        else:
            folders_map['0000-00-00'].append(p) # Use dummy date for sorting Unknowns last
    
    # Format for display
    formatted_folders = []
    for date_key in sorted(folders_map.keys(), reverse=True):
        projects_list = folders_map[date_key]
        if date_key == '0000-00-00':
            display_name = 'Unknown Date'
            display_date = 'No completion date recorded'
        else:
            try:
                dt = datetime.fromisoformat(date_key)
                display_name = dt.strftime('%A, %d %B %Y')
                display_date = dt.strftime('%d %B %Y')
            except:
                display_name = date_key
                display_date = date_key
        
        formatted_folders.append({
            'name': display_name,
            'date_sub': display_date,
            'projects': projects_list,
            'count': len(projects_list)
        })
    
    return render_template('archive.html', folders=formatted_folders, total_archived=len(archived_projects))

@app.route('/reports')
def reports_view():
    today = date.today()
    view = request.args.get('view', 'daily')
    
    # --- Daily Stats ---
    daily_created = Project.query.filter(func.date(Project.created_at) == today).count()
    daily_completed = Project.query.filter(
        Project.is_archived == True,
        func.date(Project.completed_at) == today
    ).count()
    daily_active = Project.query.filter_by(is_archived=False).count()
    daily_overdue = Project.query.filter(
        Project.is_archived == False,
        Project.due_date != None,
        Project.due_date < today
    ).count()
    
    # --- Weekly Stats ---
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Efficient grouped queries
    weekly_completed = db.session.query(func.date(Project.completed_at), func.count(Project.id))\
        .filter(Project.is_archived == True, Project.completed_at >= week_start, Project.completed_at < week_end + timedelta(days=1))\
        .group_by(func.date(Project.completed_at)).all()
    comp_map = {str(d): c for d, c in weekly_completed}
    
    weekly_created = db.session.query(func.date(Project.created_at), func.count(Project.id))\
        .filter(Project.created_at >= week_start, Project.created_at < week_end + timedelta(days=1))\
        .group_by(func.date(Project.created_at)).all()
    cre_map = {str(d): c for d, c in weekly_created}
    
    daily_stats = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        daily_stats.append({
            'day': day.strftime('%A'),
            'date': day.strftime('%d/%m'),
            'created': cre_map.get(day_str, 0),
            'completed': comp_map.get(day_str, 0)
        })
    
    best_day = max(daily_stats, key=lambda x: x['completed']) if daily_stats else None
    total_week_completed = sum(d['completed'] for d in daily_stats)
    total_week_created = sum(d['created'] for d in daily_stats)
    
    week_completed_projects = Project.query.filter(
        Project.is_archived == True,
        Project.completed_at >= week_start,
        Project.completed_at < week_end + timedelta(days=1)
    ).all()
    
    # --- Monthly Stats ---
    month_start = today.replace(day=1)
    month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    
    # Fetch all monthly completed projects in one go
    monthly_completed_all = Project.query.filter(
        Project.is_archived == True,
        Project.completed_at >= month_start,
        Project.completed_at < month_end + timedelta(days=1)
    ).all()
    
    month_weeks = []
    current_week = month_start
    week_num = 1
    while current_week <= month_end:
        week_end_date = min(current_week + timedelta(days=6), month_end)
        # Filter in memory
        completed_count = len([p for p in monthly_completed_all if current_week <= p.completed_at.date() <= week_end_date])
        month_weeks.append({
            'label': f'Week {week_num}',
            'start': current_week.strftime('%d/%m'),
            'end': week_end_date.strftime('%d/%m'),
            'completed': completed_count
        })
        current_week += timedelta(days=7)
        week_num += 1
    
    total_month_completed = len(monthly_completed_all)
    total_month_created = Project.query.filter(
        Project.created_at >= month_start,
        Project.created_at < month_end + timedelta(days=1)
    ).count()
    
    # --- Yearly Stats ---
    year_start = today.replace(month=1, day=1)
    
    # Group by month for efficiency
    yearly_stats = db.session.query(func.strftime('%m', Project.completed_at), func.count(Project.id))\
        .filter(Project.is_archived == True, func.strftime('%Y', Project.completed_at) == str(today.year))\
        .group_by(func.strftime('%m', Project.completed_at)).all()
    yearly_map = {m: c for m, c in yearly_stats}
    
    yearly_months = []
    for m in range(1, 13):
        m_str = f"{m:02d}"
        month_date = date(today.year, m, 1)
        yearly_months.append({
            'label': month_date.strftime('%b'),
            'completed': yearly_map.get(m_str, 0)
        })
    
    total_year_completed = sum(m['completed'] for m in yearly_months)
    total_year_created = Project.query.filter(func.strftime('%Y', Project.created_at) == str(today.year)).count()
    
    return render_template('reports.html',
                         view=view,
                         today=today,
                         daily_created=daily_created,
                         daily_completed=daily_completed,
                         daily_active=daily_active,
                         daily_overdue=daily_overdue,
                         week_start=week_start,
                         week_end=week_end,
                         daily_stats=daily_stats,
                         best_day=best_day,
                         total_week_completed=total_week_completed,
                         total_week_created=total_week_created,
                         week_completed=week_completed_projects,
                         month_start=month_start,
                         month_end=month_end,
                         month_weeks=month_weeks,
                         total_month_completed=total_month_completed,
                         total_month_created=total_month_created,
                         year_start=year_start,
                         yearly_months=yearly_months,
                         total_year_completed=total_year_completed,
                         total_year_created=total_year_created)

@app.route('/templates')
def templates_view():
    templates = TaskTemplate.query.order_by(TaskTemplate.created_at.desc()).all()
    return render_template('template_manager.html', templates=templates)

@app.route('/settings')
def settings_view():
    all_settings = {s.key: s.value for s in Settings.query.all()}
    quotes = Quote.query.all()
    return render_template('settings.html', settings=all_settings, quotes=quotes)

@app.route('/ai-prompts')
def ai_prompts_view():
    prompts = AIPrompt.query.order_by(AIPrompt.order_index.asc()).all()
    return render_template('ai_prompts.html', prompts=prompts)

@app.route('/api/prompts', methods=['GET'])
def get_prompts():
    prompts = AIPrompt.query.order_by(AIPrompt.order_index.asc()).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'prompt_text': p.prompt_text,
        'example_input': p.example_input,
        'example_output': p.example_output,
        'category': p.category,
        'order_index': p.order_index
    } for p in prompts])

@app.route('/api/prompts/add', methods=['POST'])
def add_prompt():
    data = request.json
    max_order = db.session.query(func.max(AIPrompt.order_index)).scalar() or 0
    prompt = AIPrompt(
        name=data['name'],
        description=data.get('description', ''),
        prompt_text=data['prompt_text'],
        example_input=data.get('example_input', ''),
        example_output=data.get('example_output', ''),
        category=data.get('category', 'General'),
        order_index=max_order + 1
    )
    db.session.add(prompt)
    db.session.commit()
    return jsonify({'success': True, 'id': prompt.id})

@app.route('/api/prompts/update/<int:id>', methods=['POST'])
def update_prompt(id):
    prompt = AIPrompt.query.get_or_404(id)
    data = request.json
    prompt.name = data.get('name', prompt.name)
    prompt.description = data.get('description', prompt.description)
    prompt.prompt_text = data.get('prompt_text', prompt.prompt_text)
    prompt.example_input = data.get('example_input', prompt.example_input)
    prompt.example_output = data.get('example_output', prompt.example_output)
    prompt.category = data.get('category', prompt.category)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/prompts/delete/<int:id>', methods=['POST'])
def delete_prompt(id):
    prompt = AIPrompt.query.get_or_404(id)
    db.session.delete(prompt)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/prompts/reorder', methods=['POST'])
def reorder_prompts():
    data = request.json
    ids = data.get('ids', [])
    for index, prompt_id in enumerate(ids):
        prompt = AIPrompt.query.get(prompt_id)
        if prompt:
            prompt.order_index = index
    db.session.commit()
    return jsonify({'success': True})

# --- API Routes ---

@app.route('/add_project', methods=['POST'])
def add_project():
    data = request.json or {}
    title = data.get('title', '').strip()
    
    if not title:
        return jsonify({"success": False, "message": "Title is required"}), 400
    
    due_date = None
    if data.get('due_date'):
        try:
            due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
        except:
            pass
    
    notes = data.get('notes', '')
    tags = data.get('tags', '')
    
    max_order = db.session.query(func.max(Project.order_index)).scalar() or 0
    
    new_project = Project(
        title=title,
        category=data.get('category', 'General'),
        priority=data.get('priority', 'Normal'),
        due_date=due_date,
        notes=notes,
        tags=tags,
        order_index=max_order + 1
    )
    db.session.add(new_project)
    db.session.flush()
    
    subtasks = data.get('subtasks', [])
    if subtasks and isinstance(subtasks[0], dict):
        temp_id_map = {}
        # First Pass: Create new records
        for idx, s_data in enumerate(subtasks):
            client_id = s_data.get('id')
            title = s_data.get('title', '').strip()
            is_side = s_data.get('is_side_project', False)
            
            new_sub = SubTask(
                title=title,
                project_id=new_project.id,
                is_side_project=is_side,
                parent_id=None,
                order_index=idx
            )
            db.session.add(new_sub)
            db.session.flush() # Generate database ID
            if client_id:
                temp_id_map[str(client_id)] = new_sub.id
                
        # Second Pass: Resolve parent_id mappings (temp parents)
        for s_data in subtasks:
            client_id = s_data.get('id')
            p_id = s_data.get('parent_id')
            if p_id is not None:
                p_str = str(p_id)
                db_parent_id = temp_id_map.get(p_str)
                db_sub_id = temp_id_map.get(str(client_id)) if client_id else None
                
                if db_sub_id and db_parent_id:
                    sub_record = SubTask.query.get(db_sub_id)
                    if sub_record:
                        sub_record.parent_id = db_parent_id
    else:
        for idx, sub_title in enumerate(subtasks):
            if isinstance(sub_title, str) and sub_title.strip():
                db.session.add(SubTask(title=sub_title.strip(), project_id=new_project.id, order_index=idx))

    db.session.commit()
    
    record_activity()
    
    return jsonify({"success": True, "message": "Task added", "id": new_project.id})

@app.route('/add_project_from_template', methods=['POST'])
def add_project_from_template():
    project = add_project_from_template_logic(request.json)
    if project:
        return jsonify({"success": True, "id": project.id})
    return jsonify({"success": False}), 400

def add_project_from_template_logic(data):
    template_id = data.get('template_id')
    if not template_id: return None
    template = TaskTemplate.query.get(template_id)
    if not template: return None
    
    max_order = db.session.query(func.max(Project.order_index)).scalar() or 0
    new_project = Project(
        title=template.name, category=template.category, priority=template.priority,
        notes=template.notes, tags=template.tags, order_index=max_order + 1
    )
    db.session.add(new_project)
    db.session.flush()
    for subtask in template.template_subtasks:
        db.session.add(SubTask(title=subtask.title, project_id=new_project.id))
    db.session.commit()
    return new_project

@app.route('/apply_templates', methods=['POST'])
def apply_templates():
    data = request.json or {}
    template_ids = data.get('template_ids', [])
    project_ids = []
    for tid in template_ids:
        project = add_project_from_template_logic({'template_id': tid})
        if project:
            project_ids.append(project.id)
    return jsonify({"success": True, "count": len(project_ids), "project_ids": project_ids})

@app.route('/update_project/<int:id>', methods=['POST'])
def update_project(id):
    project = Project.query.get_or_404(id)
    data = request.json or {}
    
    if data.get('title'):
        project.title = data['title'].strip()
    
    project.priority = data.get('priority', project.priority)
    project.category = data.get('category', project.category)
    project.notes = data.get('notes', project.notes)
    project.tags = data.get('tags', project.tags)
    
    if data.get('due_date') is not None:
        project.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data['due_date'] else None
    
    # Process Subtasks & Side Projects
    if 'subtasks' in data:
        temp_id_map = {}
        # First Pass: Create new or update existing flat records
        for s_data in data['subtasks']:
            client_id = s_data.get('id')
            title = s_data.get('title', '').strip()
            is_side = s_data.get('is_side_project', False)
            
            if client_id and not str(client_id).startswith('temp_'):
                # Existing subtask
                sub = SubTask.query.get(client_id)
                if sub and sub.project_id == project.id:
                    sub.title = title
                    sub.is_side_project = is_side
                    p_id = s_data.get('parent_id')
                    if p_id and not str(p_id).startswith('temp_'):
                        sub.parent_id = int(p_id)
                    elif p_id is None:
                        sub.parent_id = None
            else:
                # New subtask/side project
                new_sub = SubTask(
                    title=title,
                    project_id=project.id,
                    is_side_project=is_side,
                    parent_id=None
                )
                db.session.add(new_sub)
                db.session.flush() # Generate database ID
                if client_id:
                    temp_id_map[str(client_id)] = new_sub.id
                    
        # Second Pass: Resolve parent_id mappings (both temp and existing)
        for s_data in data['subtasks']:
            client_id = s_data.get('id')
            p_id = s_data.get('parent_id')
            if p_id is not None:
                p_str = str(p_id)
                db_parent_id = None
                if p_str.startswith('temp_'):
                    db_parent_id = temp_id_map.get(p_str)
                else:
                    db_parent_id = int(p_id)
                
                # Fetch the database record for this subtask to update parent_id
                db_sub_id = None
                if client_id and not str(client_id).startswith('temp_'):
                    db_sub_id = int(client_id)
                elif client_id:
                    db_sub_id = temp_id_map.get(str(client_id))
                    
                if db_sub_id and db_parent_id:
                    sub_record = SubTask.query.get(db_sub_id)
                    if sub_record:
                        sub_record.parent_id = db_parent_id
    
    if 'delete_subtasks' in data:
        for s_id in data['delete_subtasks']:
            if s_id and not str(s_id).startswith('temp_'):
                sub = SubTask.query.get(int(s_id))
                if sub and sub.project_id == project.id:
                    db.session.delete(sub)
    
    project.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({"success": True})

@app.route('/get_project_subtasks/<int:id>')
def get_project_subtasks(id):
    project = Project.query.get_or_404(id)
    subtasks = [{
        'id': s.id,
        'title': s.title,
        'is_completed': s.is_completed,
        'parent_id': s.parent_id,
        'is_side_project': s.is_side_project
    } for s in project.subtasks]
    return jsonify({"success": True, "subtasks": subtasks})

@app.route('/update_deadline/<int:id>', methods=['POST'])
def update_deadline(id):
    project = Project.query.get_or_404(id)
    data = request.json or {}
    
    if data.get('due_date') is not None:
        project.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data['due_date'] else None
    
    db.session.commit()
    return jsonify({"success": True})

@app.route('/add_subtask/<int:project_id>', methods=['POST'])
def add_subtask(project_id):
    data = request.json or {}
    title = data.get('title', '').strip()
    parent_id = data.get('parent_id')
    is_side_project = data.get('is_side_project', False)
    
    if not title:
        return jsonify({"success": False, "message": "Title is required"}), 400
        
    if parent_id is not None:
        parent = SubTask.query.get(parent_id)
        if not parent:
            return jsonify({"success": False, "message": "Parent not found"}), 404
        if not parent.is_side_project:
            return jsonify({"success": False, "message": "Cannot add items under a Sub-task. Only Side Projects can have children."}), 400

    max_order = db.session.query(func.max(SubTask.order_index)).filter_by(project_id=project_id, parent_id=parent_id).scalar() or 0
    
    new_sub = SubTask(
        title=title,
        project_id=project_id,
        parent_id=parent_id,
        is_side_project=is_side_project,
        order_index=max_order + 1
    )
    db.session.add(new_sub)
    db.session.commit()
    
    return jsonify({"success": True, "id": new_sub.id})

@app.route('/move_subtask/<int:id>', methods=['POST'])
def move_subtask(id):
    sub = SubTask.query.get_or_404(id)
    data = request.json or {}
    new_parent_id = data.get('new_parent_id')
    new_project_id = data.get('new_project_id')
    
    # Same project validation
    if new_project_id and int(new_project_id) != sub.project_id:
        return jsonify({"success": False, "message": "Cannot move items between different projects"}), 400
        
    parsed_new_parent_id = int(new_parent_id) if new_parent_id is not None else None
    if sub.parent_id != parsed_new_parent_id:
        return jsonify({"success": False, "message": "Movement is restricted to items under the same parent branch and depth level."}), 400
        
    if new_parent_id is not None:
        new_parent = SubTask.query.get(new_parent_id)
        if not new_parent:
            return jsonify({"success": False, "message": "Target parent not found"}), 404
        if new_parent.project_id != sub.project_id:
            return jsonify({"success": False, "message": "Target parent belongs to a different project"}), 400
        # Sub-task cannot have children
        if not new_parent.is_side_project:
            return jsonify({"success": False, "message": "A sub-task cannot have children. Only Side Projects can have children."}), 400
            
        # Circular reference check
        curr = new_parent
        while curr is not None:
            if curr.id == sub.id:
                return jsonify({"success": False, "message": "Circular dependency detected. Cannot move an item under its own descendants."}), 400
            curr = curr.parent if curr.parent_id else None

    # Update parent_id
    sub.parent_id = new_parent_id
    
    # Reorder siblings in the target container
    siblings = SubTask.query.filter_by(project_id=sub.project_id, parent_id=new_parent_id).order_by(SubTask.order_index).all()
    # Remove sub from siblings if it's there
    siblings = [s for s in siblings if s.id != sub.id]
    
    # Insert sub at the desired position
    new_index = data.get('new_index', len(siblings))
    siblings.insert(new_index, sub)
    
    for idx, s in enumerate(siblings):
        s.order_index = idx
        
    db.session.commit()
    return jsonify({"success": True})

@app.route('/add_side_project/<int:project_id>', methods=['POST'])
def add_side_project(project_id):
    data = request.json or {}
    title = data.get('title', '').strip()
    if not title:
        return jsonify({"success": False, "message": "Title is required"}), 400
    
    max_idx = db.session.query(db.func.max(SubTask.order_index)).filter_by(project_id=project_id, parent_id=None).scalar()
    new_order = (max_idx + 1) if max_idx is not None else 0

    side_project = SubTask(
        title=title,
        project_id=project_id,
        is_side_project=True,
        parent_id=None,
        order_index=new_order
    )
    db.session.add(side_project)
    db.session.flush()
    
    for idx, sub_title in enumerate(data.get('subtasks', [])):
        if sub_title.strip():
            db.session.add(SubTask(
                title=sub_title.strip(),
                project_id=project_id,
                parent_id=side_project.id,
                is_side_project=False,
                order_index=idx
            ))
    
    db.session.commit()
    return jsonify({"success": True, "id": side_project.id})

@app.route('/toggle_subtask/<int:id>', methods=['POST'])
def toggle_subtask(id):
    sub = SubTask.query.get_or_404(id)
    sub.is_completed = not sub.is_completed
    db.session.commit()
    check_auto_archive(sub.parent_project)
    return jsonify({"success": True})

@app.route('/delete_subtask/<int:id>', methods=['POST'])
def delete_subtask(id):
    sub = SubTask.query.get_or_404(id)
    project_id = sub.project_id
    db.session.delete(sub)
    db.session.commit()
    
    project = Project.query.get(project_id)
    if project:
        check_auto_archive(project)
    
    return jsonify({"success": True})

@app.route('/update_subtask/<int:id>', methods=['POST'])
def update_subtask(id):
    sub = SubTask.query.get_or_404(id)
    data = request.json or {}
    
    title = data.get('title', '').strip()
    if title:
        sub.title = title
        
    # Process nested subtasks under a side project
    if 'subtasks' in data:
        for s_data in data['subtasks']:
            s_id = s_data.get('id')
            s_title = s_data.get('title', '').strip()
            if not s_title:
                continue
                
            if s_id and not str(s_id).startswith('temp_'):
                # Existing subtask
                child = SubTask.query.get(int(s_id))
                if child and child.parent_id == sub.id:
                    child.title = s_title
                    if 'is_completed' in s_data:
                        child.is_completed = s_data['is_completed']
            else:
                # New subtask
                max_idx = db.session.query(db.func.max(SubTask.order_index)).filter_by(
                    project_id=sub.project_id, parent_id=sub.id
                ).scalar()
                new_idx = (max_idx + 1) if max_idx is not None else 0
                
                new_child = SubTask(
                    title=s_title,
                    project_id=sub.project_id,
                    parent_id=sub.id,
                    is_side_project=False,
                    order_index=new_idx
                )
                db.session.add(new_child)
                
    if 'delete_subtasks' in data:
        for s_id in data['delete_subtasks']:
            if s_id and not str(s_id).startswith('temp_'):
                child = SubTask.query.get(int(s_id))
                if child and child.parent_id == sub.id:
                    db.session.delete(child)
                    
    db.session.commit()
    return jsonify({"success": True})


@app.route('/reorder_subtasks', methods=['POST'])
def reorder_subtasks():
    data = request.json or {}
    project_id = data.get('project_id')
    subtask_ids = data.get('subtask_ids', [])
    
    if project_id is not None:
        for index, sub_id in enumerate(subtask_ids):
            sub = SubTask.query.get(sub_id)
            if sub:
                sub.project_id = project_id
                sub.order_index = index
        db.session.commit()
    return jsonify({"success": True})

@app.route('/archive_project/<int:id>', methods=['POST'])
def archive_project(id):
    project = Project.query.get_or_404(id)
    project.is_archived = True
    project.is_completed = True
    project.completed_at = datetime.utcnow()
    db.session.commit()
    record_activity()
    return jsonify({"success": True})

@app.route('/delete_project/<int:id>', methods=['POST'])
def delete_project(id):
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/restore_project/<int:id>', methods=['POST'])
def restore_project(id):
    project = Project.query.get_or_404(id)
    project.is_archived = False
    project.is_completed = False
    project.completed_at = None
    db.session.commit()
    return jsonify({"success": True})

@app.route('/bulk_action', methods=['POST'])
def bulk_action():
    data = request.json or {}
    action = data.get('action')
    task_ids = data.get('task_ids', [])
    
    if not task_ids:
        return jsonify({"success": False}), 400
    
    tasks = Project.query.filter(Project.id.in_(task_ids)).all()
    
    if action == 'archive':
        now = datetime.utcnow()
        for task in tasks:
            task.is_archived = True
            task.is_completed = True
            task.completed_at = now
        message = f"{len(tasks)} tasks archived"
    elif action == 'delete':
        for task in tasks:
            db.session.delete(task)
        message = f"{len(tasks)} tasks deleted"
    elif action == 'restore':
        for task in tasks:
            task.is_archived = False
            task.is_completed = False
            task.completed_at = None
        message = f"{len(tasks)} tasks restored"
    else:
        return jsonify({"success": False}), 400
    
    db.session.commit()
    return jsonify({"success": True, "message": message})

@app.route('/reorder_tasks', methods=['POST'])
def reorder_tasks():
    data = request.json or {}
    task_ids = data.get('task_ids', [])
    
    # Update order indices
    for index, task_id in enumerate(task_ids):
        task = Project.query.get(task_id)
        if task:
            task.order_index = index
    
    # Automatically switch to manual sort order so it persists
    setting = Settings.query.filter_by(key='sort_order').first()
    if setting:
        setting.value = 'manual'
    else:
        db.session.add(Settings(key='sort_order', value='manual'))
    
    db.session.commit()
    return jsonify({"success": True})

# --- Template API ---

@app.route('/add_template', methods=['POST'])
def add_template():
    data = request.json or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({"success": False, "message": "Name is required"}), 400
        
    template = TaskTemplate(
        name=name,
        category=data.get('category', 'General'),
        priority=data.get('priority', 'Normal'),
        tags=data.get('tags', ''),
        notes=data.get('notes', '')
    )
    db.session.add(template)
    db.session.flush()
    
    for sub in data.get('subtasks', []):
        if isinstance(sub, str) and sub.strip():
            db.session.add(TemplateSubTask(title=sub.strip(), template_id=template.id))
    
    db.session.commit()
    return jsonify({"success": True, "id": template.id})

@app.route('/delete_template/<int:id>', methods=['POST'])
def delete_template(id):
    template = TaskTemplate.query.get_or_404(id)
    db.session.delete(template)
    db.session.commit()
    return jsonify({"success": True})

# --- Settings API ---

@app.route('/save_settings', methods=['POST'])
def save_settings():
    data = request.json or {}
    valid_keys = [
        'auto_archive', 'notifications', 'default_view', 'theme_color', 'font_size', 'sort_order',
        'theme_bg', 'theme_surface', 'theme_accent', 'theme_text', 'theme_muted', 'theme_border', 'theme_name'
    ]
    
    for key, value in data.items():
        if key in valid_keys:
            setting = Settings.query.filter_by(key=key).first()
            if setting:
                setting.value = str(value)
            else:
                db.session.add(Settings(key=key, value=str(value)))
    
    db.session.commit()
    return jsonify({"success": True})

# --- Quotes API ---

@app.route('/add_quote', methods=['POST'])
def add_quote():
    data = request.json or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({"success": False}), 400
    
    q = Quote(text=text)
    db.session.add(q)
    db.session.commit()
    return jsonify({"success": True, "id": q.id})

@app.route('/delete_quote/<int:id>', methods=['POST'])
def delete_quote(id):
    Quote.query.get_or_404(id)
    Quote.query.filter_by(id=id).delete()
    db.session.commit()
    return jsonify({"success": True})

@app.route('/toggle_quote/<int:id>', methods=['POST'])
def toggle_quote(id):
    quote = Quote.query.get_or_404(id)
    quote.is_active = not quote.is_active
    db.session.commit()
    return jsonify({"success": True, "is_active": quote.is_active})

# --- Habits API ---

@app.route('/habits')
def habits_view():
    habits = Habit.query.order_by(Habit.order_index.asc()).all()
    
    # Get today's date from query param or system
    today_str = request.args.get('today')
    if today_str:
        try:
            today = datetime.strptime(today_str, '%Y-%m-%d').date()
        except ValueError:
            today = date.today()
    else:
        today = date.today()
        
    active_habits = len(habits)
    
    # Bulk fetch entries for all habits to solve N+1 problem
    all_habit_ids = [h.id for h in habits]
    all_entries = HabitEntry.query.filter(HabitEntry.habit_id.in_(all_habit_ids)).all()
    
    entries_map = defaultdict(dict)
    for entry in all_entries:
        entries_map[entry.habit_id][entry.date] = entry.completed
        
    habits_data = []
    total_streak = 0
    best_streak_all = 0
    today_done = 0
    
    for habit in habits:
        h_entries = entries_map[habit.id]
        is_completed_today = h_entries.get(today, False)
        
        if is_completed_today:
            today_done += 1
            
        current_streak = 0
        check_date = today
        
        while True:
            if h_entries.get(check_date):
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                if check_date == today:
                    check_date -= timedelta(days=1)
                    continue
                break
                
        if habit.best_streak > best_streak_all:
            best_streak_all = habit.best_streak
            
        total_streak += current_streak
        
        habits_data.append({
            'id': habit.id,
            'name': habit.name,
            'icon': habit.icon,
            'color': habit.color,
            'notes': habit.notes or '',
            'group_name': habit.group_name or 'General',
            'best_streak': habit.best_streak,
            'current_streak': current_streak,
            'is_completed_today': is_completed_today
        })
        
    avg_streak = round(total_streak / active_habits, 1) if active_habits > 0 else 0
    unique_groups = sorted(list(set(h['group_name'] for h in habits_data)))
    
    return render_template('habits.html', 
                         habits=habits_data,
                         active_habits=active_habits,
                         today_done=today_done,
                         best_streak=best_streak_all,
                         avg_streak=avg_streak,
                         groups=unique_groups)

@app.route('/add_habit', methods=['POST'])
def add_habit():
    data = request.json or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({"success": False, "message": "Name is required"}), 400
        
    habit = Habit(
        name=name,
        icon=data.get('icon', 'fas fa-dumbbell'),
        color=data.get('color', '#ffffff'),
        notes=data.get('notes', ''),
        group_name=data.get('group_name', 'General')
    )
    db.session.add(habit)
    db.session.commit()
    return jsonify({"success": True, "id": habit.id})

@app.route('/update_habit/<int:id>', methods=['POST'])
def update_habit(id):
    habit = Habit.query.get_or_404(id)
    data = request.json or {}
    
    if 'name' in data and data['name'].strip():
        habit.name = data['name'].strip()
    if 'icon' in data:
        habit.icon = data['icon'].strip() or 'fas fa-dumbbell'
    if 'color' in data:
        habit.color = data['color'].strip()
    if 'notes' in data:
        habit.notes = data['notes'].strip()
    if 'group_name' in data:
        habit.group_name = data['group_name'].strip() or 'General'
        
    db.session.commit()
    return jsonify({"success": True})

@app.route('/toggle_habit/<int:id>', methods=['POST'])
def toggle_habit(id):
    habit = Habit.query.get_or_404(id)
    data = request.json or {}
    date_str = data.get('date')
    
    if date_str:
        try:
            today = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            today = date.today()
    else:
        today = date.today()
    
    entry = HabitEntry.query.filter_by(habit_id=habit.id, date=today).first()
    if entry:
        entry.completed = not entry.completed
    else:
        entry = HabitEntry(habit_id=habit.id, date=today, completed=True)
        db.session.add(entry)
    
    if entry.completed:
        record_activity()
        
        # Calculate and update best streak if needed
        h_entries = HabitEntry.query.filter_by(habit_id=habit.id).order_by(HabitEntry.date.desc()).all()
        entry_dates = {e.date: e.completed for e in h_entries}
        
        current_streak = 0
        check_date = today
        while True:
            if entry_dates.get(check_date):
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                if check_date == today:
                    check_date -= timedelta(days=1)
                    continue
                break
        
        if current_streak > habit.best_streak:
            habit.best_streak = current_streak
            
    db.session.commit()
    return jsonify({"success": True})

@app.route('/reorder_habits', methods=['POST'])
def reorder_habits():
    data = request.json or {}
    habit_ids = data.get('habit_ids', [])
    for index, habit_id in enumerate(habit_ids):
        habit = Habit.query.get(habit_id)
        if habit:
            habit.order_index = index
    db.session.commit()
    return jsonify({"success": True})

@app.route('/delete_habit/<int:id>', methods=['POST'])
def delete_habit(id):
    habit = Habit.query.get_or_404(id)
    db.session.delete(habit)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/get_habit_card/<int:id>')
def get_habit_card(id):
    habit_obj = Habit.query.get_or_404(id)
    today = date.today()
    
    entry = HabitEntry.query.filter_by(habit_id=id, date=today).first()
    is_completed_today = entry.completed if entry else False
    
    # Calculate current streak
    h_entries = HabitEntry.query.filter_by(habit_id=id).all()
    entries_map = {e.date: e.completed for e in h_entries}
    
    current_streak = 0
    check_date = today
    while True:
        if entries_map.get(check_date):
            current_streak += 1
            check_date -= timedelta(days=1)
        else:
            if check_date == today:
                check_date -= timedelta(days=1)
                continue
            break
            
    habit_data = {
        'id': habit_obj.id,
        'name': habit_obj.name,
        'icon': habit_obj.icon,
        'color': habit_obj.color,
        'notes': habit_obj.notes or '',
        'group_name': habit_obj.group_name or 'General',
        'best_streak': habit_obj.best_streak,
        'current_streak': current_streak,
        'is_completed_today': is_completed_today
    }
    return render_template('partials/habit_card.html', habit=habit_data)

@app.route('/get_habit_stats')
def get_habit_stats():
    today = date.today()
    total_habits = Habit.query.count()
    completed_habits = HabitEntry.query.filter_by(date=today, completed=True).count()
    return jsonify({
        "success": True,
        "today_done": completed_habits,
        "active_habits": total_habits
    })

@app.route('/get_template_card/<int:id>')
def get_template_card(id):
    template = TaskTemplate.query.get_or_404(id)
    return render_template('partials/template_card.html', template=template)

@app.route('/habit_data/<int:id>', methods=['GET'])
def habit_data(id):
    habit = Habit.query.get_or_404(id)
    today = date.today()
    start_date = today - timedelta(days=29)
    
    entries = HabitEntry.query.filter(
        HabitEntry.habit_id == habit.id,
        HabitEntry.date >= start_date,
        HabitEntry.date <= today
    ).order_by(HabitEntry.date.asc()).all()
    
    entry_dict = {e.date: e.completed for e in entries}
    
    data = []
    labels = []
    for i in range(30):
        d = start_date + timedelta(days=i)
        labels.append(d.strftime('%m-%d'))
        data.append(1 if entry_dict.get(d, False) else 0)
        
    return jsonify({
        "success": True,
        "labels": labels,
        "data": data,
        "color": habit.color
    })

@app.route('/habit_calendar_data', methods=['GET'])
def habit_calendar_data():
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    if not month or not year:
        today = date.today()
        month = today.month
        year = today.year
        
    start_date = date(year, month, 1)
    end_date = date(year, month, calendar.monthrange(year, month)[1])
    
    entries = db.session.query(HabitEntry, Habit).join(Habit).filter(
        HabitEntry.date >= start_date,
        HabitEntry.date <= end_date,
        HabitEntry.completed == True
    ).all()
    
    data = defaultdict(list)
    for entry, habit in entries:
        day_str = entry.date.strftime('%Y-%m-%d')
        data[day_str].append({
            'id': habit.id,
            'name': habit.name,
            'color': habit.color
        })
        
    return jsonify({"success": True, "data": dict(data)})

@app.route('/habit_weekly_report')
def habit_weekly_report():
    offset = request.args.get('week_offset', 0, type=int)
    today = date.today()
    
    # Calculate start of week (Monday)
    start_of_week = today - timedelta(days=today.weekday())
    start_date = start_of_week - timedelta(weeks=offset)
    end_date = start_date + timedelta(days=6)
    
    habits = Habit.query.all()
    entries = HabitEntry.query.filter(HabitEntry.date >= start_date, HabitEntry.date <= end_date, HabitEntry.completed == True).all()
    
    habit_counts = defaultdict(int)
    daily_counts = { (start_date + timedelta(days=i)).strftime('%Y-%m-%d'): 0 for i in range(7) }
    
    for entry in entries:
        habit_counts[entry.habit_id] += 1
        daily_counts[entry.date.strftime('%Y-%m-%d')] += 1
        
    habit_progress = {}
    for h in habits:
        habit_progress[h.id] = {
            'name': h.name,
            'color': h.color,
            'completed_days': habit_counts[h.id]
        }
        
    chart_labels = []
    chart_data = []
    for i in range(7):
        d = start_date + timedelta(days=i)
        chart_labels.append(d.strftime('%a'))
        chart_data.append(daily_counts[d.strftime('%Y-%m-%d')])
        
    return jsonify({
        "success": True,
        "week_label": f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}",
        "habit_progress": habit_progress,
        "chart_labels": chart_labels,
        "chart_data": chart_data
    })

# --- Data Export ---

def get_full_backup_data():
    return {
        "app_name": "TaskFlow Noir",
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "2.0",
        "tables": {
            "projects": [{
                'id': p.id, 'title': p.title, 'category': p.category,
                'priority': p.priority, 'due_date': str(p.due_date) if p.due_date else None,
                'tags': p.tags, 'notes': p.notes, 'is_archived': p.is_archived,
                'is_completed': p.is_completed, 'completed_at': str(p.completed_at) if p.completed_at else None,
                'created_at': str(p.created_at), 'order_index': p.order_index
            } for p in Project.query.all()],
            "subtasks": [{
                'id': s.id, 'title': s.title, 'is_completed': s.is_completed,
                'project_id': s.project_id, 'order_index': s.order_index,
                'parent_id': s.parent_id, 'is_side_project': s.is_side_project
            } for s in SubTask.query.all()],
            "habits": [{
                'id': h.id, 'name': h.name, 'icon': h.icon, 'color': h.color,
                'notes': h.notes, 'group_name': h.group_name, 'best_streak': h.best_streak,
                'order_index': h.order_index, 'created_at': str(h.created_at)
            } for h in Habit.query.all()],
            "habit_entries": [{
                'id': e.id, 'habit_id': e.habit_id, 'date': str(e.date), 'completed': e.completed
            } for e in HabitEntry.query.all()],
            "task_templates": [{
                'id': t.id, 'name': t.name, 'category': t.category, 'priority': t.priority,
                'tags': t.tags, 'notes': t.notes, 'created_at': str(t.created_at)
            } for t in TaskTemplate.query.all()],
            "template_subtasks": [{
                'id': s.id, 'title': s.title, 'template_id': s.template_id
            } for s in TemplateSubTask.query.all()],
            "settings": [{
                'id': s.id, 'key': s.key, 'value': s.value
            } for s in Settings.query.all()],
            "quotes": [{
                'id': q.id, 'text': q.text, 'is_active': q.is_active
            } for q in Quote.query.all()],
            "daily_activity": [{
                'id': a.id, 'date': str(a.date), 'tasks_completed': a.tasks_completed
            } for a in DailyActivity.query.all()],
            "achievements": [{
                'id': a.id, 'key': a.key, 'unlocked_at': str(a.unlocked_at)
            } for a in Achievement.query.all()],
            "inbox_items": [{
                'id': i.id,
                'title': i.title,
                'subtasks_json': i.subtasks_json,
                'notes': i.notes,
                'created_at': str(i.created_at),
                'is_converted': i.is_converted
            } for i in InboxItem.query.all()],
            "ai_prompts": [{
                'id': p.id,
                'name': p.name,
                'description': p.description,
                'prompt_text': p.prompt_text,
                'example_input': p.example_input,
                'example_output': p.example_output,
                'category': p.category,
                'order_index': p.order_index,
                'created_at': str(p.created_at) if p.created_at else None
            } for p in AIPrompt.query.all()]
        }
    }

def auto_backup():
    with app.app_context():
        backup_folder = get_setting('backup_folder')
        if not backup_folder:
            return False
            
        today_str = date.today().strftime('%Y-%m-%d')
        filename = f'taskflow_backup_{today_str}.json'
        filepath = os.path.join(backup_folder, filename)
        
        if not os.path.exists(filepath):
            try:
                os.makedirs(backup_folder, exist_ok=True)
                data = get_full_backup_data()
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"Auto-backup created at {filepath}")
                return True
            except Exception as e:
                print(f"Auto-backup failed: {e}")
                return False
        return True

@app.route('/export_data')
def export_data():
    format_type = request.args.get('format', 'json')
    
    if format_type == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Title', 'Category', 'Priority', 'Due Date', 'Tags', 'Notes', 'Archived'])
        for p in Project.query.all():
            writer.writerow([p.id, p.title, p.category, p.priority, str(p.due_date) if p.due_date else '', p.tags, p.notes, p.is_archived])
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=tasks_export.csv'
        return response
    
    # JSON Export - Full Backup
    data = get_full_backup_data()
    
    response = make_response(json.dumps(data, indent=2, ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json'
    today = date.today().strftime('%Y-%m-%d')
    filename = f'taskflow_backup_{today}.json'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@app.route('/import_preview', methods=['POST'])
def import_preview():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected"}), 400
    
    try:
        data = json.load(file)
        if "tables" not in data:
            return jsonify({"success": False, "message": "Invalid backup format"}), 400
        
        tables = data["tables"]
        
        counts = {
            "projects_add": 0,
            "projects_skip": 0,
            "subtasks_add": 0,
            "habits_add": 0,
            "templates_add": 0,
            "inbox_items_add": 0,
            "prompts_add": 0,
            "prompts_skip": 0
        }

        # Simulated maps (old ID -> new simulated ID)
        project_map = {}
        subtask_map = {}
        habit_map = {}
        template_map = {}

        # 1. Projects
        import_subs_by_project = {}
        for s_data in tables.get("subtasks", []):
            import_subs_by_project.setdefault(s_data['project_id'], set()).add(s_data['title'])

        for p_data in tables.get("projects", []):
            due_str = p_data.get('due_date') or ''
            import_sub_titles = import_subs_by_project.get(p_data['id'], set())

            candidates = Project.query.filter_by(
                title=p_data['title'],
                is_archived=p_data['is_archived']
            ).all()

            existing = None
            for cand in candidates:
                cand_due = cand.due_date.strftime('%Y-%m-%d') if cand.due_date else ''
                if cand_due != due_str:
                    continue
                if {s.title for s in cand.subtasks} == import_sub_titles:
                    existing = cand
                    break

            if existing:
                project_map[p_data['id']] = existing.id
                counts["projects_skip"] += 1
            else:
                simulated_id = f"sim_p_{p_data['id']}"
                project_map[p_data['id']] = simulated_id
                counts["projects_add"] += 1

        # 2. Subtasks (2-pass Relational Dependency Resolver - simulated)
        queue = list(tables.get("subtasks", []))
        progress = True
        
        while queue and progress:
            progress = False
            for s_data in list(queue):
                old_parent_id = s_data.get('parent_id')
                
                if old_parent_id is None or old_parent_id in subtask_map:
                    new_project_id = project_map.get(s_data['project_id'])
                    if new_project_id:
                        new_parent_id = subtask_map.get(old_parent_id) if old_parent_id else None
                        is_sp = s_data.get('is_side_project', False)
                        
                        existing = None
                        if isinstance(new_project_id, int):
                            existing = SubTask.query.filter_by(
                                title=s_data['title'],
                                project_id=new_project_id,
                                parent_id=new_parent_id,
                                is_side_project=is_sp
                            ).first()
                        
                        if existing:
                            subtask_map[s_data['id']] = existing.id
                        else:
                            simulated_id = f"sim_s_{s_data['id']}"
                            subtask_map[s_data['id']] = simulated_id
                            counts["subtasks_add"] += 1
                            
                    queue.remove(s_data)
                    progress = True
                    
        for s_data in queue:
            new_project_id = project_map.get(s_data['project_id'])
            if new_project_id:
                counts["subtasks_add"] += 1

        # 3. Habits
        for h_data in tables.get("habits", []):
            existing = Habit.query.filter_by(
                name=h_data['name'],
                group_name=h_data['group_name'],
                color=h_data['color']
            ).first()
            if existing and (existing.notes or '') != (h_data.get('notes') or ''):
                existing = None

            if existing:
                habit_map[h_data['id']] = existing.id
            else:
                habit_map[h_data['id']] = f"sim_h_{h_data['id']}"
                counts["habits_add"] += 1

        # 4. Templates
        import_tsubs_by_template = {}
        for ts_data in tables.get("template_subtasks", []):
            import_tsubs_by_template.setdefault(ts_data['template_id'], set()).add(ts_data['title'])

        for t_data in tables.get("task_templates", []):
            import_sub_titles = import_tsubs_by_template.get(t_data['id'], set())
            candidates = TaskTemplate.query.filter_by(name=t_data['name']).all()
            existing = None
            for cand in candidates:
                if {s.title for s in cand.template_subtasks} == import_sub_titles:
                    existing = cand
                    break

            if existing:
                template_map[t_data['id']] = existing.id
            else:
                template_map[t_data['id']] = f"sim_t_{t_data['id']}"
                counts["templates_add"] += 1

        # 5. Inbox Items
        for i_data in tables.get("inbox_items", []):
            existing = InboxItem.query.filter_by(title=i_data['title']).first()
            if not existing:
                counts["inbox_items_add"] += 1

        # 6. AI Prompts
        prompts_data = tables.get("ai_prompts", [])
        for p_data in prompts_data:
            existing = AIPrompt.query.filter_by(name=p_data['name']).first()
            if existing:
                counts["prompts_skip"] += 1
            else:
                counts["prompts_add"] += 1

        return jsonify({
            "success": True,
            "counts": counts
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Preview failed: {str(e)}"}), 500

@app.route('/import_data', methods=['POST'])
def import_data():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected"}), 400
    
    try:
        data = json.load(file)
        if "tables" not in data:
            return jsonify({"success": False, "message": "Invalid backup format"}), 400
        
        tables = data["tables"]
        
        counts = {
            "projects_added": 0, "projects_skipped": 0,
            "subtasks_added": 0, "subtasks_skipped": 0,
            "habits_added": 0, "habits_skipped": 0,
            "habit_entries_added": 0, "habit_entries_skipped": 0,
            "templates_added": 0, "templates_skipped": 0,
            "settings_updated": 0, "quotes_added": 0,
            "inbox_items_added": 0, "inbox_items_skipped": 0,
            "prompts_added": 0, "prompts_updated": 0
        }

        # ID Mappings (Old ID -> New ID)
        project_map = {}
        habit_map = {}
        template_map = {}

        # Helper: parse datetime string with fallback
        def parse_dt(s):
            if not s: return None
            for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
                try: return datetime.strptime(s, fmt)
                except ValueError: pass
            return None

        # Pre-build subtask title sets per project from the import file
        import_subs_by_project = {}
        for s_data in tables.get("subtasks", []):
            import_subs_by_project.setdefault(s_data['project_id'], set()).add(s_data['title'])

        # Pre-build template-subtask title sets per template from the import file
        import_tsubs_by_template = {}
        for ts_data in tables.get("template_subtasks", []):
            import_tsubs_by_template.setdefault(ts_data['template_id'], set()).add(ts_data['title'])

        # 1. Projects — match: title + is_archived + due_date + set of subtask titles
        for p_data in tables.get("projects", []):
            due_str = p_data.get('due_date') or ''
            import_sub_titles = import_subs_by_project.get(p_data['id'], set())

            candidates = Project.query.filter_by(
                title=p_data['title'],
                is_archived=p_data['is_archived']
            ).all()

            existing = None
            for cand in candidates:
                cand_due = cand.due_date.strftime('%Y-%m-%d') if cand.due_date else ''
                if cand_due != due_str:
                    continue
                if {s.title for s in cand.subtasks} == import_sub_titles:
                    existing = cand
                    break

            if existing:
                project_map[p_data['id']] = existing.id
                counts["projects_skipped"] += 1
            else:
                p = Project(
                    title=p_data['title'], category=p_data['category'],
                    priority=p_data['priority'], notes=p_data['notes'], tags=p_data['tags'],
                    is_archived=p_data['is_archived'], is_completed=p_data['is_completed'],
                    order_index=p_data['order_index'],
                    due_date=datetime.strptime(p_data['due_date'], '%Y-%m-%d').date() if p_data.get('due_date') else None,
                    completed_at=parse_dt(p_data.get('completed_at')),
                    created_at=parse_dt(p_data.get('created_at')) or datetime.utcnow()
                )
                db.session.add(p)
                db.session.flush()
                project_map[p_data['id']] = p.id
                counts["projects_added"] += 1

        # 2. Subtasks (2-pass Relational Dependency Resolver)
        subtask_map = {}
        queue = list(tables.get("subtasks", []))
        progress = True
        
        while queue and progress:
            progress = False
            for s_data in list(queue):
                old_parent_id = s_data.get('parent_id')
                
                # Check if we can process it (no parent, or parent already processed)
                if old_parent_id is None or old_parent_id in subtask_map:
                    new_project_id = project_map.get(s_data['project_id'])
                    if new_project_id:
                        new_parent_id = subtask_map.get(old_parent_id) if old_parent_id else None
                        is_sp = s_data.get('is_side_project', False)
                        
                        # Smart Matching: compares title + project_id + parent_id + is_side_project
                        existing = SubTask.query.filter_by(
                            title=s_data['title'],
                            project_id=new_project_id,
                            parent_id=new_parent_id,
                            is_side_project=is_sp
                        ).first()
                        
                        if existing:
                            subtask_map[s_data['id']] = existing.id
                            counts["subtasks_skipped"] += 1
                        else:
                            s = SubTask(
                                title=s_data['title'],
                                is_completed=s_data.get('is_completed', False),
                                project_id=new_project_id,
                                parent_id=new_parent_id,
                                is_side_project=is_sp,
                                order_index=s_data.get('order_index', 0)
                            )
                            db.session.add(s)
                            db.session.flush()
                            subtask_map[s_data['id']] = s.id
                            counts["subtasks_added"] += 1
                            
                    queue.remove(s_data)
                    progress = True
                    
        # Fallback for remaining items in case of cyclic/broken imports
        for s_data in queue:
            new_project_id = project_map.get(s_data['project_id'])
            if new_project_id:
                is_sp = s_data.get('is_side_project', False)
                s = SubTask(
                    title=s_data['title'],
                    is_completed=s_data.get('is_completed', False),
                    project_id=new_project_id,
                    parent_id=None,
                    is_side_project=is_sp,
                    order_index=s_data.get('order_index', 0)
                )
                db.session.add(s)
                db.session.flush()
                subtask_map[s_data['id']] = s.id
                counts["subtasks_added"] += 1

        # 3. Habits — match: name + group_name + color + notes
        for h_data in tables.get("habits", []):
            existing = Habit.query.filter_by(
                name=h_data['name'],
                group_name=h_data['group_name'],
                color=h_data['color']
            ).first()
            # Also verify notes match
            if existing and (existing.notes or '') != (h_data.get('notes') or ''):
                existing = None

            if existing:
                habit_map[h_data['id']] = existing.id
                counts["habits_skipped"] += 1
            else:
                h = Habit(
                    name=h_data['name'], icon=h_data['icon'], color=h_data['color'],
                    notes=h_data['notes'], group_name=h_data['group_name'], best_streak=h_data['best_streak'],
                    order_index=h_data['order_index'],
                    created_at=parse_dt(h_data.get('created_at')) or datetime.utcnow()
                )
                db.session.add(h)
                db.session.flush()
                habit_map[h_data['id']] = h.id
                counts["habits_added"] += 1

        # 4. Habit Entries — match: habit (via name+group map) + date + completed
        for e_data in tables.get("habit_entries", []):
            new_habit_id = habit_map.get(e_data['habit_id'])
            if not new_habit_id: continue

            entry_date = datetime.strptime(e_data['date'], '%Y-%m-%d').date()
            existing = HabitEntry.query.filter_by(
                habit_id=new_habit_id, date=entry_date, completed=e_data['completed']
            ).first()
            if existing:
                counts["habit_entries_skipped"] += 1
            else:
                db.session.add(HabitEntry(
                    habit_id=new_habit_id, completed=e_data['completed'], date=entry_date
                ))
                counts["habit_entries_added"] += 1

        # 5. Templates — match: name + set of template subtask titles
        for t_data in tables.get("task_templates", []):
            import_sub_titles = import_tsubs_by_template.get(t_data['id'], set())
            candidates = TaskTemplate.query.filter_by(name=t_data['name']).all()
            existing = None
            for cand in candidates:
                if {s.title for s in cand.template_subtasks} == import_sub_titles:
                    existing = cand
                    break

            if existing:
                template_map[t_data['id']] = existing.id
                counts["templates_skipped"] += 1
            else:
                t = TaskTemplate(
                    name=t_data['name'], category=t_data['category'],
                    priority=t_data['priority'], notes=t_data['notes'],
                    tags=",".join(t_data['tags']) if isinstance(t_data['tags'], list) else t_data['tags'],
                    created_at=parse_dt(t_data.get('created_at')) or datetime.utcnow()
                )
                db.session.add(t)
                db.session.flush()
                template_map[t_data['id']] = t.id
                counts["templates_added"] += 1

        # Template subtasks — only for newly created templates
        for ts_data in tables.get("template_subtasks", []):
            new_template_id = template_map.get(ts_data['template_id'])
            if not new_template_id: continue
            if not TemplateSubTask.query.filter_by(title=ts_data['title'], template_id=new_template_id).first():
                db.session.add(TemplateSubTask(title=ts_data['title'], template_id=new_template_id))

        # 6. Settings
        for set_data in tables.get("settings", []):
            setting = Settings.query.filter_by(key=set_data['key']).first()
            if setting:
                setting.value = set_data['value']
            else:
                db.session.add(Settings(key=set_data['key'], value=set_data['value']))
            counts["settings_updated"] += 1
            
        # 7. Quotes — skip if text exists
        for q_data in tables.get("quotes", []):
            if not Quote.query.filter_by(text=q_data['text']).first():
                db.session.add(Quote(text=q_data['text'], is_active=q_data['is_active']))
                counts["quotes_added"] += 1

        # 8. Daily Activity — update tasks_completed (take max) if date exists
        for a_data in tables.get("daily_activity", []):
            act_date = datetime.strptime(a_data['date'], '%Y-%m-%d').date()
            existing_act = DailyActivity.query.filter_by(date=act_date).first()
            if existing_act:
                existing_act.tasks_completed = max(existing_act.tasks_completed, a_data['tasks_completed'])
            else:
                db.session.add(DailyActivity(date=act_date, tasks_completed=a_data['tasks_completed']))

        # 9. Achievements — skip if key exists
        for ach_data in tables.get("achievements", []):
            if not Achievement.query.filter_by(key=ach_data['key']).first():
                db.session.add(Achievement(
                    key=ach_data['key'],
                    unlocked_at=parse_dt(ach_data.get('unlocked_at')) or datetime.utcnow()
                ))

        # 10. Inbox Items
        for i_data in tables.get("inbox_items", []):
            existing = InboxItem.query.filter_by(title=i_data['title']).first()
            if existing:
                counts["inbox_items_skipped"] += 1
            else:
                item = InboxItem(
                    title=i_data['title'],
                    subtasks_json=i_data.get('subtasks_json'),
                    notes=i_data.get('notes'),
                    created_at=parse_dt(i_data.get('created_at')) or datetime.utcnow(),
                    is_converted=i_data.get('is_converted', False)
                )
                db.session.add(item)
                counts["inbox_items_added"] += 1

        # 11. AI Prompts - match by name
        for prompt_data in tables.get("ai_prompts", []):
            existing = AIPrompt.query.filter_by(name=prompt_data['name']).first()
            if existing:
                # Update existing prompt with imported data
                existing.description = prompt_data.get('description', '')
                existing.prompt_text = prompt_data.get('prompt_text', '')
                existing.example_input = prompt_data.get('example_input', '')
                existing.example_output = prompt_data.get('example_output', '')
                existing.category = prompt_data.get('category', 'General')
                existing.order_index = prompt_data.get('order_index', 0)
                counts["prompts_updated"] += 1
            else:
                new_prompt = AIPrompt(
                    name=prompt_data['name'],
                    description=prompt_data.get('description', ''),
                    prompt_text=prompt_data.get('prompt_text', ''),
                    example_input=prompt_data.get('example_input', ''),
                    example_output=prompt_data.get('example_output', ''),
                    category=prompt_data.get('category', 'General'),
                    order_index=prompt_data.get('order_index', 0),
                    created_at=parse_dt(prompt_data.get('created_at')) or datetime.utcnow()
                )
                db.session.add(new_prompt)
                counts["prompts_added"] += 1

        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Data merged successfully!", 
            "counts": counts
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Import failed: {str(e)}"}), 500

@app.route('/inbox')
def inbox_view():
    items = InboxItem.query.order_by(InboxItem.created_at.desc()).all()
    inbox_count = InboxItem.query.count()
    
    # Convert to dictionaries for JSON serialization
    items_dict = [{
        'id': item.id,
        'title': item.title,
        'notes': item.notes,
        'planned_date': item.planned_date.isoformat() if item.planned_date else None,
        'created_at': item.created_at.isoformat() if item.created_at else None,
        'subtasks_json': item.subtasks_json,
        'is_converted': item.is_converted
    } for item in items]
    
    return render_template('inbox.html', items=items_dict, inbox_count=inbox_count)

@app.route('/inbox/count')
def inbox_count():
    count = InboxItem.query.filter_by(is_converted=False).count()
    return jsonify({"success": True, "count": count})

@app.route('/inbox/add', methods=['POST'])
def inbox_add():
    data = request.json or {}
    title = data.get('title', '').strip()
    if not title:
        return jsonify({"success": False, "message": "Title is required"}), 400
    
    subtasks = data.get('subtasks', [])
    notes = data.get('notes', '')
    planned_date = None
    if data.get('planned_date'):
        try:
            planned_date = datetime.strptime(data['planned_date'], '%Y-%m-%d').date()
        except:
            pass
    
    item = InboxItem(
        title=title,
        subtasks_json=json.dumps(subtasks),
        notes=notes,
        planned_date=planned_date
    )
    db.session.add(item)
    db.session.commit()
    
    return jsonify({
        "success": True, 
        "message": "Item added to Brain Dump",
        "item": {
            "id": item.id,
            "title": item.title,
            "subtasks": subtasks,
            "notes": item.notes,
            "planned_date": str(item.planned_date) if item.planned_date else None,
            "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
    })

@app.route('/inbox/delete/<int:id>', methods=['POST'])
def inbox_delete(id):
    item = InboxItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"success": True, "message": "Item deleted"})

@app.route('/inbox/update-date/<int:id>', methods=['POST'])
def inbox_update_date(id):
    item = InboxItem.query.get_or_404(id)
    data = request.json or {}
    planned_date_str = data.get('planned_date')
    if planned_date_str:
        try:
            item.planned_date = datetime.strptime(planned_date_str, '%Y-%m-%d').date()
        except:
            item.planned_date = None
    else:
        item.planned_date = None
    db.session.commit()
    return jsonify({"success": True, "planned_date": str(item.planned_date) if item.planned_date else None})


def _create_subtasks_from_json(node_list, project_id, parent_id=None, order_start=0):
    """Recursively create SubTask records from the inbox subtasks_json format."""
    for idx, node in enumerate(node_list):
        if not isinstance(node, dict):
            if str(node).strip():
                db.session.add(SubTask(
                    title=str(node).strip(),
                    project_id=project_id,
                    parent_id=parent_id,
                    is_side_project=False,
                    order_index=order_start + idx
                ))
            continue

        node_type = node.get('type', 'subtask')
        node_title = node.get('title', '').strip()
        if not node_title:
            continue

        is_side = (node_type == 'side_project')
        new_sub = SubTask(
            title=node_title,
            project_id=project_id,
            parent_id=parent_id,
            is_side_project=is_side,
            order_index=order_start + idx
        )
        db.session.add(new_sub)
        db.session.flush()

        children = node.get('children', [])
        if children and is_side:
            _create_subtasks_from_json(children, project_id, parent_id=new_sub.id)


@app.route('/inbox/convert/project/<int:id>', methods=['POST'])
def inbox_convert_project(id):
    item = InboxItem.query.get_or_404(id)
    data = request.json or {}
    title = data.get('title', item.title).strip()
    if not title:
        return jsonify({"success": False, "message": "Title is required"}), 400

    due_date = None
    if data.get('due_date'):
        try:
            due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
        except:
            pass

    notes = data.get('notes', item.notes)
    category = data.get('category', 'General')
    priority = data.get('priority', 'Normal')

    max_order = db.session.query(func.max(Project.order_index)).scalar() or 0
    new_project = Project(
        title=title, category=category, priority=priority,
        due_date=due_date, notes=notes, order_index=max_order + 1
    )
    db.session.add(new_project)
    db.session.flush()

    subtasks = data.get('subtasks')
    if subtasks is None:
        try:
            subtasks = json.loads(item.subtasks_json) if item.subtasks_json else []
        except:
            subtasks = []

    _create_subtasks_from_json(subtasks, new_project.id)
    item.is_converted = True
    db.session.commit()
    return jsonify({"success": True, "message": "Converted to Project", "project_id": new_project.id})


@app.route('/inbox/convert/task/<int:id>', methods=['POST'])
def inbox_convert_task(id):
    item = InboxItem.query.get_or_404(id)
    data = request.json or {}
    title = data.get('title', item.title).strip()
    if not title:
        return jsonify({"success": False, "message": "Title is required"}), 400

    due_date = None
    if data.get('due_date'):
        try:
            due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
        except:
            pass

    notes = data.get('notes', item.notes)
    category = data.get('category', 'General')
    priority = data.get('priority', 'Normal')

    max_order = db.session.query(func.max(Project.order_index)).scalar() or 0
    new_project = Project(
        title=title, category=category, priority=priority,
        due_date=due_date, notes=notes, order_index=max_order + 1
    )
    db.session.add(new_project)
    db.session.flush()

    def flatten_subtasks(node_list):
        flat = []
        for node in node_list:
            if isinstance(node, str):
                if node.strip(): flat.append(node.strip())
            elif isinstance(node, dict):
                t = node.get('title', '').strip()
                if t: flat.append(t)
                flat.extend(flatten_subtasks(node.get('children', [])))
        return flat

    subtasks_raw = data.get('subtasks')
    if subtasks_raw is None:
        try:
            subtasks_raw = json.loads(item.subtasks_json) if item.subtasks_json else []
        except:
            subtasks_raw = []

    for idx, s_title in enumerate(flatten_subtasks(subtasks_raw)):
        db.session.add(SubTask(
            title=s_title, project_id=new_project.id,
            is_side_project=False, parent_id=None, order_index=idx
        ))

    item.is_converted = True
    db.session.commit()
    return jsonify({"success": True, "message": "Converted to Task", "project_id": new_project.id})


@app.route('/inbox/bulk_convert', methods=['POST'])
def inbox_bulk_convert():
    data = request.json or {}
    ids = data.get('ids', [])
    target = data.get('target', 'project')

    if not ids:
        return jsonify({"success": False, "message": "No items selected"}), 400

    items = InboxItem.query.filter(InboxItem.id.in_(ids), InboxItem.is_converted == False).all()
    max_order = db.session.query(func.max(Project.order_index)).scalar() or 0

    def flatten_all(nodes):
        flat = []
        for n in nodes:
            if isinstance(n, str) and n.strip():
                flat.append(n.strip())
            elif isinstance(n, dict):
                t = n.get('title', '').strip()
                if t: flat.append(t)
                flat.extend(flatten_all(n.get('children', [])))
        return flat

    project_ids = []
    for idx, item in enumerate(items):
        new_project = Project(
            title=item.title, notes=item.notes,
            order_index=max_order + idx + 1, category='General', priority='Normal'
        )
        db.session.add(new_project)
        db.session.flush()
        project_ids.append(new_project.id)

        try:
            subtasks = json.loads(item.subtasks_json) if item.subtasks_json else []
        except:
            subtasks = []

        if target == 'project':
            _create_subtasks_from_json(subtasks, new_project.id)
        else:
            for s_idx, s_title in enumerate(flatten_all(subtasks)):
                db.session.add(SubTask(
                    title=s_title, project_id=new_project.id,
                    is_side_project=False, parent_id=None, order_index=s_idx
                ))

        item.is_converted = True

    db.session.commit()
    return jsonify({"success": True, "message": f"{len(items)} items converted", "project_ids": project_ids})


@app.route('/inbox/bulk_delete', methods=['POST'])
def inbox_bulk_delete():
    data = request.json or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify({"success": False, "message": "No items selected"}), 400

    InboxItem.query.filter(InboxItem.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"success": True, "message": "Selected items deleted"})

@app.route('/clear_all_data', methods=['POST'])
def clear_all_data():
    data = request.json
    target = data.get('target', 'all')
    
    if target == 'all':
        SubTask.query.delete()
        Project.query.delete()
        HabitEntry.query.delete()
        Habit.query.delete()
        TemplateSubTask.query.delete()
        TaskTemplate.query.delete()
        DailyActivity.query.delete()
        Achievement.query.delete()
        InboxItem.query.delete()
        # Keep Quotes and Settings (user preferences)
    elif target == 'archived':
        Project.query.filter_by(is_archived=True).delete()
    elif target == 'active':
        Project.query.filter_by(is_archived=False).delete()
    
    db.session.commit()
    return jsonify({"success": True, "message": "All data cleared"})

@app.route('/choose_backup_folder', methods=['POST'])
def choose_backup_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder_path = filedialog.askdirectory(title="Choose Backup Folder")
        root.destroy()
        
        if folder_path:
            setting = Settings.query.filter_by(key='backup_folder').first()
            if setting:
                setting.value = folder_path
            else:
                db.session.add(Settings(key='backup_folder', value=folder_path))
            db.session.commit()
            
            auto_backup()
            
            return jsonify({"success": True, "path": folder_path})
        return jsonify({"success": False, "message": "No folder selected"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/inbox/restore/<int:id>', methods=['POST'])
def inbox_restore(id):
    """Restore a previously deleted inbox item (for undo)"""
    data = request.json
    item = InboxItem(
        id=data.get('id'),
        title=data['title'],
        subtasks_json=data.get('subtasks_json'),
        notes=data.get('notes'),
        planned_date=datetime.strptime(data['planned_date'], '%Y-%m-%d').date() if data.get('planned_date') else None,
        created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.utcnow(),
        is_converted=False
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/project/delete/<int:id>', methods=['DELETE'])
def project_delete_undo(id):
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    auto_backup()
    # في آخر app.py، غير السطر ده:
    app.run(debug=True, port=3000, host='0.0.0.0')