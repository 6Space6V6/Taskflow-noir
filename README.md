# **🖤 TaskFlow Noir**

**A minimalist dark-themed task management application**

TaskFlow Noir is a sleek, distraction-free productivity hub designed for professionals and creators who thrive in dark mode. It seamlessly combines advanced task management, habit tracking, and comprehensive productivity analytics into a single desktop application.

## **🚀 Features**

### **📋 Task Management**

* **Flexible Architecture:** Organize your life with dedicated spaces for Projects, Subtasks, and independent Side Projects.  
* **Fluid UI:** Move tasks across stages seamlessly using **Drag & Drop** powered by SortableJS.  
* **Smart Prioritization:** Classify and filter your tasks based on urgency and importance.

### **🧘 Habit Tracker**

* **Consistency Booster:** Track daily habits and maintain your progress with an automated **Streak Counter**.  
* **Visual Progress:** View your habit history clearly through a dedicated Calendar View.  
* **Smart Grouping:** Categorize habits into customized groups for better organization.

### **📊 Reports & Analytics**

* **Multi-dimensional Views:** Analyze your productivity with Daily, Weekly, Monthly, and Yearly breakdown reports.  
* **Data Visualization:** Beautiful and dynamic charts powered by Chart.js to track your completion rates.

### **📄 Templates**

* **Pre-made Frameworks:** Jumpstart your day with built-in productivity templates.  
* **Custom Templates:** Create, save, and reuse your own task structures for recurring workflows.

### **🎨 Themes**

* **18 Dark Flavors:** Choose from 18 distinct dark-themed aesthetics split across 5 specialized categories.  
* **Seamless Sync:** Themes instantly apply across all views, modals, and charts.

### **💾 Data & Security**

* **Full Ownership:** Export and Import your entire database anytime using standard JSON format.  
* **Peace of Mind:** Integrated Auto-backup system to prevent any data loss.

## **🛠️ Tech Stack**

TaskFlow Noir is built using a robust, lightweight, and modern technology stack:

* **Backend:** Python (Flask)  
* **Database:** SQLite (with SQLAlchemy ORM)  
* **Frontend:** HTML5, Tailwind CSS, Chart.js, SortableJS, Font Awesome  
* **Desktop Wrapper:** Electron

## **💻 Installation & Setup**

### **Prerequisites**

Make sure you have **Python 3.x** installed on your machine.

### **Step-by-Step Setup**

1. **Clone or Download the Repository:**  
   git clone https://github.com/6Space6V6/Taskflow-noir.git  
   cd Taskflow-noir

2. **Install the Required Dependencies:**  
   pip install flask flask-sqlalchemy

3. **Run the Application:**  
   python app.py

4. **Access the App:**  
   Open your preferred web browser and navigate to:  
   http://localhost:3000

   *(Note: For the native desktop experience, run the Electron wrapper from the electron/ directory).*

## **📖 Usage Guide**

* 🎛️ **Dashboard:** Your command center. Use it to add daily tasks or quickly jot down thoughts using **Quick Capture**.  
* 🧭 **Sidebar Navigation:** Quickly switch between Tasks, Habits, Reports, Templates, and Settings.  
* 🎨 **Changing Themes:** Go to **Settings**, browse through the 5 theme categories, and select one of the 18 dark variations.  
* 🔄 **Data Management:** Keep your data safe by visiting Settings to trigger a manual JSON export or configure Auto-backup.

## **⌨️ Keyboard Shortcuts**

Increase your workflow speed using these built-in global shortcuts:

| Shortcut | Action |
| ----: | ----: |
| N | New Task |
| Ctrl \+ K | Search |
| Ctrl \+ Shift \+ N | Quick Capture |
| ? | Open Shortcuts Panel |
| ESC | Close Active Modal |
| Ctrl \+ D | Go to Dashboard |

## **🎨 Theme Directory**

Explore 18 meticulously designed themes tailored for low-light environments, grouped into **5 distinct categories**:

1. **Noir Classics:** Ultimate dark modes (Pure Black, Jet Black, Charcoal).  
2. **Cyberpunk:** Vibrant neon accents against deep dark backdrops.  
3. **Nordic & Forest:** Muted blues, greens, and cozy cold-atmosphere tones.  
4. **Deep Ocean:** Rich navy and midnight blue hues.  
5. **Vintage Dark:** Warm, sepia-tinted dark themes for a retro feel.

*Themes can be hot-swapped instantly inside the **Settings** panel without needing a restart.*

## **📂 Project Structure**

taskflow-noir/  
├── app.py                     \# Main Flask Application Entry Point  
├── todo\_noir.db               \# SQLite Local Database  
├── templates/                 \# Frontend HTML Views  
│   ├── base.html              \# Core Layout & Sidebar  
│   ├── index.html             \# Main Dashboard & Tasks  
│   ├── habits.html            \# Habit Tracker & Streaks  
│   ├── archive.html           \# Completed & Archived Tasks  
│   ├── reports.html           \# Analytics & Charts  
│   ├── settings.html          \# Themes & Data Settings  
│   └── template\_manager.html  \# Custom Templates Framework  
└── electron/                  \# Desktop Application Wrapper  
    ├── main.js                \# Electron Main Process  
    └── package.json           \# Electron Configuration

## **🤝 Credits**

* **Built & Developed by:** [Space\_V](https://github.com/6Space6V6)  
* **Icons:** [Font Awesome](https://fontawesome.com)  
* **Data Visualization:** [Chart.js](https://www.chartjs.org)  
* **Drag & Drop Functionality:** [SortableJS](https://sortablejs.github.io/Sortable/)
