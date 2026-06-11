````markdown
████████╗ █████╗ ███████╗██╗  ██╗███████╗██╗ ██████╗ ██╗    ██╗
╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝██╔════╝██║██╔═══██╗██║    ██║
   ██║   ███████║███████╗█████╔╝ █████╗  ██║██║   ██║██║ █╗ ██║
   ██║   ██╔══██║╚════██║██╔═██╗ ██╔══╝  ██║██║   ██║██║███╗██║
   ██║   ██║  ██║███████║██║  ██╗███████╗██║╚██████╔╝╚███╔███╔╝
   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝ ╚═════╝  ╚══╝╚══╝

# 🖤 TaskFlow Noir

> A minimalist dark productivity system for organizing tasks, ideas, habits, and workflows.

---

![Version](https://img.shields.io/badge/version-3.1.0-black)
![Python](https://img.shields.io/badge/Python-3.x-blue)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-green)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey)
![License](https://img.shields.io/badge/license-MIT-purple)

**Version:** 3.1.0 (June 2026)

````

# 📦 Installation

```bash
cd TaskFlow-Noir
pip install flask flask-sqlalchemy
python app.py
```

Open:

```text
http://localhost:3000
```

---

# 🖤 Overview

TaskFlow Noir is a full local productivity system built with Flask + SQLite, designed for:

* Tasks
* Projects
* Brain dumping
* Habits
* AI prompts
* Templates
* Analytics
* Backups

---

# ✨ Features

## 📋 1. Task Management (Projects)

* Title, category, priority (Urgent/High/Normal)
* Due dates, notes, tags
* Subtask system
* Progress bar (auto-calculated)
* Overdue detection
* Drag & drop (SortableJS)

---

## 🌳 2. Subtasks & Side Projects

### Subtasks

* Flat checklist tasks

### Side Projects

* Nested folders inside projects
* Can contain:

  * Subtasks
  * Other side projects
* Unlimited nesting depth
* Drag & drop between parents
* Progress excludes side projects

---

## 🧠 3. Brain Dump / Inbox

Capture anything instantly.

Each item:

* Title
* Notes
* Planned date
* Full JSON task tree

### Views:

* List
* Grid
* Boxes (Kanban by date)
* Calendar
* Timeline

### Actions:

* Convert → Project (keeps hierarchy)
* Convert → Task (flattens structure)
* Bulk actions (delete / convert)
* Drag between date boxes

---

## 👁️ 4. Dashboard Views

* List View (table)
* Grid View (cards)
* Kanban View:

  * Urgent
  * High
  * Normal
* Drag changes priority

---

## 🧘 5. Habit Tracker

* Name, icon, color, group
* Daily completion toggle
* Streak (current + best)
* Monthly calendar view
* Weekly Chart.js analytics
* Drag & reorder habits

---

## 🤖 6. AI Prompts Manager

* Store prompts
* Categories:

  * Import
  * Extract
  * Organize
  * Generate
  * General
  * Coding
  * Writing
* Copy to clipboard
* Drag reorder
* Filter by category

---

## 📄 7. Templates

* Save task structures
* Apply instantly
* Built-ins:

  * Team Meeting
  * Grocery Shopping

---

## 🗃️ 8. Archive

* Completed tasks grouped by date
* Restore tasks
* Permanent delete
* Search archive

---

## 📊 9. Reports

* Daily / Weekly / Monthly / Yearly
* Created vs completed charts
* Best day analysis
* Activity tracking

---

## 🎨 10. Themes (18)

Midnight, Emerald, Crimson, Royal, Amber, Amethyst, Deep Ocean, Rose, Slate, Mocha, Nord, Dracula, Synthwave, Everforest, Catppuccin, Solarized, One Dark, B&W

* Instant switching
* Persistent settings

---

## 💾 11. Data Management

* Export full JSON database:
  projects, habits, inbox, prompts, templates, settings, etc.
* Import with duplicate detection
* Auto daily backups
* Reset / clear archive

---

## ⚡ 12. Quick Capture Bar

* Floating input bar
* `Ctrl + Shift + N` focus
* Enter = create task

---

## ⌨️ Keyboard Shortcuts

| Shortcut         | Action        |
| ---------------- | ------------- |
| N                | New Task      |
| I                | Brain Dump    |
| Ctrl + K         | Search        |
| Ctrl + Shift + I | Inbox         |
| Ctrl + Shift + N | Quick Capture |
| Ctrl + Z         | Undo          |
| Ctrl + B         | Sidebar       |
| ?                | Help          |
| ESC              | Close         |

---

# 🛠️ Tech Stack

* Python 3.x + Flask
* SQLite + SQLAlchemy ORM
* Jinja2 Templates
* TailwindCSS (CDN)
* Vanilla JavaScript
* Chart.js
* SortableJS
* Font Awesome 6

---

---

# 🌐 Routes

* `/` Dashboard
* `/inbox`
* `/habits`
* `/archive`
* `/reports`
* `/templates`
* `/settings`
* `/ai-prompts`
* `/export_data`
* `/import_data`
* `/api/prompts/*`
* `/inbox/*`

---

# 📁 Project Structure

```text
TaskFlow-Noir/
├── app.py
├── todo_noir.db
├── requirements.txt
├── README.md
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── inbox.html
│   ├── habits.html
│   ├── archive.html
│   ├── reports.html
│   ├── settings.html
│   ├── ai_prompts.html
│   └── partials/
│       ├── task_row.html
│       ├── habit_card.html
│       └── template_card.html
│
├── electron/
│   ├── main.js
│   └── package.json
│
└── Backup/
```

---

# 🗺️ Roadmap

* Cloud sync
* Mobile app
* Team collaboration
* Advanced analytics
* Desktop improvements

---

# 🤝 Contributing

```bash
git checkout -b feature/new-feature
git add .
git commit -m "update"
git push origin feature/new-feature
```

---

# 📜 License

MIT License

---

# 🖤 TaskFlow Noir

> Capture ideas. Organize projects. Execute flawlessly.

```
```
=======

>>>>>>> 37beef204751d639666032aaa6819e40982aa144
