import sys
import io

# Safe print function that works without console
def safe_print(*args, **kwargs):
    try:
        if sys.stdout is not None:
            print(*args, **kwargs)
    except:
        pass

# Fix encoding for Windows console (only if stdout exists)
if sys.platform == 'win32':
    if sys.stdout is not None:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr is not None:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import warnings
warnings.filterwarnings("ignore")
import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)

from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import json
from datetime import datetime
import os
import threading
import webview

# Load Telegram config
TELEGRAM_CONFIG_FILE = "telegram_config.json"
PENDING_TASKS_FILE = "pending_telegram_tasks.json"
bot = None
bot_thread = None
TELEGRAM_TOKEN = None
TELEGRAM_ENABLED = False

try:
    if os.path.exists(TELEGRAM_CONFIG_FILE):
        with open(TELEGRAM_CONFIG_FILE, 'r') as f:
            config = json.load(f)
            TELEGRAM_TOKEN = config.get('bot_token', 'YOUR_BOT_TOKEN_HERE')
            TELEGRAM_ENABLED = config.get('enabled', False)
except:
    TELEGRAM_TOKEN = "YOUR_BOT_TOKEN_HERE"
    TELEGRAM_ENABLED = False

# Import telebot only if enabled
if TELEGRAM_ENABLED and TELEGRAM_TOKEN != "YOUR_BOT_TOKEN_HERE":
    try:
        import telebot
        from telebot import types
        telebot_available = True
    except ImportError:
        safe_print("⚠️ telebot not installed. Install it with: pip install pyTelegramBotAPI")
        telebot_available = False
else:
    telebot_available = False

app = Flask(__name__)

# Database initialization
def init_db():
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()
    
    # Create folders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#667eea',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create todos table with folder_id and new fields for Kanban/Archive
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            completed BOOLEAN DEFAULT FALSE,
            priority TEXT DEFAULT 'medium',
            category TEXT DEFAULT 'general',
            folder_id INTEGER DEFAULT NULL,
            kanban_status TEXT DEFAULT 'todo',
            added_to_today BOOLEAN DEFAULT FALSE,
            today_date TIMESTAMP DEFAULT NULL,
            archived BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE SET NULL
        )
    ''')

    # Create notes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert default folder if none exists
    cursor.execute('SELECT COUNT(*) FROM folders')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO folders (name, color) VALUES (?, ?)', ('General', '#667eea'))

    # Migration: Add new columns to existing databases
    cursor.execute("PRAGMA table_info(todos)")
    existing_columns = [column[1] for column in cursor.fetchall()]

    if 'kanban_status' not in existing_columns:
        cursor.execute('ALTER TABLE todos ADD COLUMN kanban_status TEXT DEFAULT "todo"')
    if 'added_to_today' not in existing_columns:
        cursor.execute('ALTER TABLE todos ADD COLUMN added_to_today BOOLEAN DEFAULT FALSE')
    if 'today_date' not in existing_columns:
        cursor.execute('ALTER TABLE todos ADD COLUMN today_date TIMESTAMP DEFAULT NULL')
    if 'archived' not in existing_columns:
        cursor.execute('ALTER TABLE todos ADD COLUMN archived BOOLEAN DEFAULT FALSE')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# ============= TELEGRAM BOT FUNCTIONS =============

def load_pending_tasks():
    """Load pending tasks from Telegram messages"""
    if not os.path.exists(PENDING_TASKS_FILE):
        return []

    try:
        with open(PENDING_TASKS_FILE, 'r', encoding='utf-8') as f:
            tasks = json.load(f)

        # Clear the file after loading
        with open(PENDING_TASKS_FILE, 'w') as f:
            json.dump([], f)

        return tasks
    except:
        return []

def save_telegram_task(user_id, username, message):
    """Save a Telegram message as a pending task"""
    tasks = []

    if os.path.exists(PENDING_TASKS_FILE):
        try:
            with open(PENDING_TASKS_FILE, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
        except:
            tasks = []

    task = {
        'user_id': user_id,
        'username': username,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }

    tasks.append(task)

    with open(PENDING_TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def import_telegram_tasks_to_db():
    """Import pending Telegram tasks into the database"""
    pending_tasks = load_pending_tasks()
    imported_count = 0

    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()

    for task in pending_tasks:
        # Add task to General folder (folder_id = 1)
        try:
            cursor.execute('''
                INSERT INTO todos (title, description, priority, category, folder_id, kanban_status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                task['message'][:100],  # Title (limit to 100 chars)
                f"From Telegram bot via @{task['username']}",  # Description
                'medium',  # Default priority
                'general',  # Default category
                1,  # General folder
                'todo'  # Default kanban status
            ))
            imported_count += 1
        except Exception as e:
            print(f"Error importing task: {e}")

    conn.commit()
    conn.close()

    return imported_count

def setup_telegram_bot():
    """Setup the Telegram bot handlers"""
    global bot

    if not TELEGRAM_ENABLED:
        safe_print("⚠️ Telegram bot is disabled in telegram_config.json")
        return None

    if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
        safe_print("⚠️ Telegram bot token not configured!")
        print("To enable Telegram bot:")
        print("1. Open telegram_config.json")
        print("2. Replace 'YOUR_BOT_TOKEN_HERE' with your bot token from @BotFather")
        print("3. Set 'enabled' to true")
        return None

    if not telebot_available:
        safe_print("⚠️ telebot library not installed!")
        print("Install it with: pip install pyTelegramBotAPI")
        return None

    try:
        bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode='HTML')

        @bot.message_handler(commands=['start'])
        def send_welcome(message):
            welcome_text = """
👋 <b>Welcome to TaskMaster Bot!</b>

I'm your personal task assistant. Just send me any text and I'll save it as a task!

<b>How to use:</b>
• Send me any message → I'll save it as a task
• When you open TaskMaster app, your tasks will be imported
• Tasks go to the "General" folder

<b>Commands:</b>
/start - Show this welcome message
/help - Show help
/tasks - Show how many pending tasks you have

💡 <i>Tip: You can send tasks while you're away, and they'll be waiting when you get home!</i>
            """
            bot.reply_to(message, welcome_text)

        @bot.message_handler(commands=['help'])
        def send_help(message):
            help_text = """
📚 <b>TaskMaster Bot Help</b>

<b>How it works:</b>
1. Send me any message
2. I'll save it until you open TaskMaster
3. When you open the app, all pending tasks are imported

<b>Commands:</b>
/start - Welcome message
/help - Show this help
/tasks - Count pending tasks

<i>Just type your task and send it!</i>
            """
            bot.reply_to(message, help_text)

        @bot.message_handler(commands=['tasks'])
        def show_pending_count(message):
            count = 0
            if os.path.exists(PENDING_TASKS_FILE):
                try:
                    with open(PENDING_TASKS_FILE, 'r', encoding='utf-8') as f:
                        tasks = json.load(f)
                        # Count only this user's tasks
                        count = sum(1 for t in tasks if t['user_id'] == message.chat.id)
                except:
                    pass

            bot.reply_to(message, f"📝 You have <b>{count}</b> pending task(s) waiting to be imported!")

        @bot.message_handler(func=lambda message: True)
        def handle_all_messages(message):
            """Save all text messages as pending tasks"""
            if message.text and not message.text.startswith('/'):
                username = message.chat.username or message.chat.first_name or "User"
                save_telegram_task(message.chat.id, username, message.text)

                # Send confirmation
                bot.reply_to(message, f"✅ Task saved: <b>{message.text[:50]}</b>\n\n📥 It will be imported when you open TaskMaster!")

        return bot

    except Exception as e:
        safe_print(f"❌ Error setting up Telegram bot: {e}")
        return None

def run_telegram_bot():
    """Run the Telegram bot in a background thread"""
    global bot

    bot = setup_telegram_bot()

    if bot:
        safe_print("🤖 Telegram bot is running...")
        safe_print("💬 Send messages to your bot to save tasks!")
        try:
            bot.polling(non_stop=True, interval=1, timeout=60)
        except Exception as e:
            safe_print(f"❌ Bot error: {e}")

@app.route('/api/telegram/import', methods=['POST'])
def import_telegram_tasks():
    """API endpoint to manually import Telegram tasks"""
    count = import_telegram_tasks_to_db()
    return jsonify({'imported': count, 'message': f'Imported {count} tasks'})

# ============= END TELEGRAM BOT FUNCTIONS =============

@app.route('/api/telegram/status', methods=['GET'])
def telegram_status():
    """Get Telegram bot status"""
    return jsonify({
        'enabled': TELEGRAM_ENABLED,
        'configured': TELEGRAM_TOKEN != "YOUR_BOT_TOKEN_HERE",
        'library_installed': telebot_available
    })

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/mainfont.ttf')
def serve_font():
    return send_file('mainfont.ttf', mimetype='font/ttf')

# API Routes for Folders
@app.route('/api/folders', methods=['GET'])
def get_folders():
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT f.id, f.name, f.color, f.created_at, COUNT(t.id) as todo_count
        FROM folders f
        LEFT JOIN todos t ON f.id = t.folder_id
        GROUP BY f.id
        ORDER BY f.created_at ASC
    ''')
    
    folders = []
    for row in cursor.fetchall():
        folder_id = row[0]
        # Obtener cantidad de tareas completadas para este folder
        cursor2 = conn.cursor()
        cursor2.execute('SELECT COUNT(*) FROM todos WHERE folder_id = ? AND completed = 1', (folder_id,))
        completed_count = cursor2.fetchone()[0]
        folders.append({
            'id': row[0],
            'name': row[1],
            'color': row[2],
            'created_at': row[3],
            'todo_count': row[4],
            'completed_count': completed_count
        })
    
    conn.close()
    return jsonify(folders)

@app.route('/api/folders', methods=['POST'])
def create_folder():
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'error': 'Folder name is required'}), 400
    
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO folders (name, color)
        VALUES (?, ?)
    ''', (
        data['name'],
        data.get('color', '#667eea')
    ))
    
    folder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'id': folder_id, 'message': 'Folder created successfully'}), 201

@app.route('/api/folders/<int:folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()
    
    # Check if folder exists
    cursor.execute('SELECT * FROM folders WHERE id = ?', (folder_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Folder not found'}), 404
    
    # Delete all todos in this folder first
    cursor.execute('DELETE FROM todos WHERE folder_id = ?', (folder_id,))
    
    # Delete the folder
    cursor.execute('DELETE FROM folders WHERE id = ?', (folder_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Folder and all its tasks deleted successfully'})

# API Routes for Todos
@app.route('/api/todos', methods=['GET'])
def get_todos():
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()
    
    # Get query parameters
    filter_status = request.args.get('status', 'all')
    search_query = request.args.get('search', '')
    category_filter = request.args.get('category', 'all')
    folder_filter = request.args.get('folder', 'all')
    
    # Build query with JOIN to get folder information
    query = """
        SELECT t.id, t.title, t.description, t.completed, t.priority,
               t.category, t.folder_id, t.created_at, t.updated_at,
               f.name as folder_name, f.color as folder_color,
               t.kanban_status, t.added_to_today, t.today_date, t.archived
        FROM todos t
        LEFT JOIN folders f ON t.folder_id = f.id
        WHERE 1=1
    """
    params = []
    
    if filter_status == 'completed':
        query += " AND t.completed = 1"
    elif filter_status == 'pending':
        query += " AND t.completed = 0"
    
    if search_query:
        query += " AND (t.title LIKE ? OR t.description LIKE ?)"
        params.extend([f'%{search_query}%', f'%{search_query}%'])
    
    if category_filter != 'all':
        query += " AND t.category = ?"
        params.append(category_filter)
    
    if folder_filter != 'all':
        query += " AND t.folder_id = ?"
        params.append(folder_filter)

    # Exclude archived tasks from normal view (unless specifically requested)
    if request.args.get('include_archived') != 'true':
        query += " AND t.archived = 0"
    
    query += " ORDER BY t.created_at DESC"
    
    cursor.execute(query, params)
    todos = cursor.fetchall()
    
    # Convert to list of dictionaries
    todos_list = []
    for todo in todos:
        todos_list.append({
            'id': todo[0],
            'title': todo[1],
            'description': todo[2],
            'completed': bool(todo[3]),
            'priority': todo[4],
            'category': todo[5],
            'folder_id': todo[6],
            'created_at': todo[7],
            'updated_at': todo[8],
            'folder_name': todo[9] or 'General',
            'folder_color': todo[10] or '#667eea',
            'kanban_status': todo[11] or 'todo',
            'added_to_today': bool(todo[12]) if todo[12] is not None else False,
            'today_date': todo[13],
            'archived': bool(todo[14]) if todo[14] is not None else False
        })
    
    conn.close()
    return jsonify(todos_list)

@app.route('/api/todos', methods=['POST'])
def create_todo():
    data = request.get_json()
    
    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400
    
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO todos (title, description, priority, category, folder_id, kanban_status, added_to_today, today_date, archived)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['title'],
        data.get('description', ''),
        data.get('priority', 'medium'),
        data.get('category', 'general'),
        data.get('folder_id', 1),  # Default to General folder
        data.get('kanban_status', 'todo'),
        data.get('added_to_today', False),
        data.get('today_date', None),
        data.get('archived', False)
    ))
    
    todo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'id': todo_id, 'message': 'Todo created successfully'}), 201

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    data = request.get_json()
    
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()
    
    # Check if todo exists
    cursor.execute('SELECT * FROM todos WHERE id = ?', (todo_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Todo not found'}), 404
    
    # Update todo
    update_fields = []
    params = []
    
    if 'title' in data:
        update_fields.append('title = ?')
        params.append(data['title'])
    
    if 'description' in data:
        update_fields.append('description = ?')
        params.append(data['description'])
    
    if 'completed' in data:
        update_fields.append('completed = ?')
        params.append(data['completed'])
    
    if 'priority' in data:
        update_fields.append('priority = ?')
        params.append(data['priority'])
    
    if 'category' in data:
        update_fields.append('category = ?')
        params.append(data['category'])
    
    if 'folder_id' in data:
        update_fields.append('folder_id = ?')
        params.append(data['folder_id'])

    if 'kanban_status' in data:
        update_fields.append('kanban_status = ?')
        params.append(data['kanban_status'])

    if 'added_to_today' in data:
        update_fields.append('added_to_today = ?')
        params.append(data['added_to_today'])

    if 'today_date' in data:
        update_fields.append('today_date = ?')
        params.append(data['today_date'])

    if 'archived' in data:
        update_fields.append('archived = ?')
        params.append(data['archived'])
    
    update_fields.append('updated_at = CURRENT_TIMESTAMP')
    params.append(todo_id)
    
    query = f"UPDATE todos SET {', '.join(update_fields)} WHERE id = ?"
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Todo updated successfully'})

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()
    
    # Check if todo exists
    cursor.execute('SELECT * FROM todos WHERE id = ?', (todo_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Todo not found'}), 404
    
    cursor.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Todo deleted successfully'})

# ============= NOTES API =============

@app.route('/api/notes', methods=['GET'])
def get_notes():
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, content, created_at, updated_at FROM notes ORDER BY created_at DESC')
    notes = [{
        'id': row[0],
        'content': row[1],
        'created_at': row[2],
        'updated_at': row[3]
    } for row in cursor.fetchall()]
    conn.close()
    return jsonify(notes)

@app.route('/api/notes', methods=['POST'])
def create_note():
    data = request.get_json()
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'error': 'Content is required'}), 400

    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO notes (content) VALUES (?)', (content,))
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'id': note_id, 'message': 'Note created successfully'}), 201

@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()

    # Check if note exists
    cursor.execute('SELECT * FROM notes WHERE id = ?', (note_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Note not found'}), 404

    cursor.execute('DELETE FROM notes WHERE id = ?', (note_id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Note deleted successfully'})

@app.route('/api/todos/<int:todo_id>/toggle', methods=['PUT'])
def toggle_todo(todo_id):
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()
    
    # Check if todo exists
    cursor.execute('SELECT completed FROM todos WHERE id = ?', (todo_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({'error': 'Todo not found'}), 404
    
    # Toggle completed status
    new_status = not result[0]
    cursor.execute('''
        UPDATE todos 
        SET completed = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (new_status, todo_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'completed': new_status, 'message': 'Todo toggled successfully'})

# API Routes for Today View
@app.route('/api/todos/today', methods=['GET'])
def get_today_todos():
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()

    query = """
        SELECT t.id, t.title, t.description, t.completed, t.priority,
               t.category, t.folder_id, t.created_at, t.updated_at,
               f.name as folder_name, f.color as folder_color,
               t.kanban_status, t.added_to_today, t.today_date, t.archived
        FROM todos t
        LEFT JOIN folders f ON t.folder_id = f.id
        WHERE t.added_to_today = 1 AND t.archived = 0
        ORDER BY t.today_date DESC, t.created_at DESC
    """

    cursor.execute(query)
    todos = cursor.fetchall()

    todos_list = []
    for todo in todos:
        todos_list.append({
            'id': todo[0],
            'title': todo[1],
            'description': todo[2],
            'completed': bool(todo[3]),
            'priority': todo[4],
            'category': todo[5],
            'folder_id': todo[6],
            'created_at': todo[7],
            'updated_at': todo[8],
            'folder_name': todo[9] or 'General',
            'folder_color': todo[10] or '#667eea',
            'kanban_status': todo[11] or 'todo',
            'added_to_today': bool(todo[12]) if todo[12] is not None else False,
            'today_date': todo[13],
            'archived': bool(todo[14]) if todo[14] is not None else False
        })

    conn.close()
    return jsonify(todos_list)

# API Routes for Archived Todos
@app.route('/api/todos/archived', methods=['GET'])
def get_archived_todos():
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()

    query = """
        SELECT t.id, t.title, t.description, t.completed, t.priority,
               t.category, t.folder_id, t.created_at, t.updated_at,
               f.name as folder_name, f.color as folder_color,
               t.kanban_status, t.added_to_today, t.today_date, t.archived
        FROM todos t
        LEFT JOIN folders f ON t.folder_id = f.id
        WHERE t.archived = 1
        ORDER BY t.updated_at DESC
    """

    cursor.execute(query)
    todos = cursor.fetchall()

    todos_list = []
    for todo in todos:
        todos_list.append({
            'id': todo[0],
            'title': todo[1],
            'description': todo[2],
            'completed': bool(todo[3]),
            'priority': todo[4],
            'category': todo[5],
            'folder_id': todo[6],
            'created_at': todo[7],
            'updated_at': todo[8],
            'folder_name': todo[9] or 'General',
            'folder_color': todo[10] or '#667eea',
            'kanban_status': todo[11] or 'todo',
            'added_to_today': bool(todo[12]) if todo[12] is not None else False,
            'today_date': todo[13],
            'archived': bool(todo[14]) if todo[14] is not None else False
        })

    conn.close()
    return jsonify(todos_list)

@app.route('/api/todos/<int:todo_id>/kanban-status', methods=['PUT'])
def update_kanban_status(todo_id):
    data = request.get_json()

    if not data or 'status' not in data:
        return jsonify({'error': 'Status is required'}), 400

    if data['status'] not in ['todo', 'doing', 'done']:
        return jsonify({'error': 'Invalid status. Must be todo, doing, or done'}), 400

    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()

    # Check if todo exists
    cursor.execute('SELECT * FROM todos WHERE id = ?', (todo_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Todo not found'}), 404

    # Update kanban status
    # If status is 'done', also mark as completed and archived
    if data['status'] == 'done':
        cursor.execute('''
            UPDATE todos
            SET kanban_status = ?, completed = 1, archived = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (data['status'], todo_id))
    else:
        cursor.execute('''
            UPDATE todos
            SET kanban_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (data['status'], todo_id))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Kanban status updated successfully'})

@app.route('/api/todos/<int:todo_id>/add-to-today', methods=['PUT'])
def add_to_today(todo_id):
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()

    # Check if todo exists
    cursor.execute('SELECT * FROM todos WHERE id = ?', (todo_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Todo not found'}), 404

    cursor.execute('''
        UPDATE todos
        SET added_to_today = 1, today_date = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (todo_id,))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Todo added to Today successfully'})

@app.route('/api/todos/<int:todo_id>/remove-from-today', methods=['PUT'])
def remove_from_today(todo_id):
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()

    # Check if todo exists
    cursor.execute('SELECT * FROM todos WHERE id = ?', (todo_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Todo not found'}), 404

    cursor.execute('''
        UPDATE todos
        SET added_to_today = 0, today_date = NULL, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (todo_id,))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Todo removed from Today successfully'})

@app.route('/api/todos/<int:todo_id>/archive', methods=['PUT'])
def archive_todo(todo_id):
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()

    # Check if todo exists
    cursor.execute('SELECT * FROM todos WHERE id = ?', (todo_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Todo not found'}), 404

    cursor.execute('''
        UPDATE todos
        SET archived = 1, completed = 1, kanban_status = 'done', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (todo_id,))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Todo archived successfully'})

@app.route('/api/todos/<int:todo_id>/unarchive', methods=['PUT'])
def unarchive_todo(todo_id):
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()

    # Check if todo exists
    cursor.execute('SELECT * FROM todos WHERE id = ?', (todo_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Todo not found'}), 404

    cursor.execute('''
        UPDATE todos
        SET archived = 0, completed = 0, kanban_status = 'todo', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (todo_id,))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Todo unarchived successfully'})

# ============= BATCH OPERATIONS =============

@app.route('/api/todos/batch', methods=['DELETE'])
def batch_delete_todos():
    """Delete multiple todos at once"""
    data = request.get_json()
    if not data or 'ids' not in data:
        return jsonify({'error': 'IDs list is required'}), 400

    todo_ids = data['ids']
    if not isinstance(todo_ids, list) or len(todo_ids) == 0:
        return jsonify({'error': 'IDs must be a non-empty list'}), 400

    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()

    # Use placeholders for all IDs
    placeholders = ','.join('?' * len(todo_ids))
    query = f'DELETE FROM todos WHERE id IN ({placeholders})'

    cursor.execute(query, todo_ids)
    deleted_count = cursor.rowcount

    conn.commit()
    conn.close()

    return jsonify({'message': f'{deleted_count} todo(s) deleted successfully', 'count': deleted_count})

@app.route('/api/todos/batch/move', methods=['PUT'])
def batch_move_todos():
    """Move multiple todos to a folder at once"""
    data = request.get_json()
    if not data or 'ids' not in data or 'folder_id' not in data:
        return jsonify({'error': 'IDs list and folder_id are required'}), 400

    todo_ids = data['ids']
    folder_id = data['folder_id']

    if not isinstance(todo_ids, list) or len(todo_ids) == 0:
        return jsonify({'error': 'IDs must be a non-empty list'}), 400

    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()

    # Verify folder exists
    cursor.execute('SELECT * FROM folders WHERE id = ?', (folder_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Folder not found'}), 404

    # Update all todos
    placeholders = ','.join('?' * len(todo_ids))
    query = f'UPDATE todos SET folder_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders})'

    cursor.execute(query, [folder_id] + todo_ids)
    updated_count = cursor.rowcount

    conn.commit()
    conn.close()

    return jsonify({'message': f'{updated_count} todo(s) moved successfully', 'count': updated_count})

@app.route('/api/stats')
def get_stats():
    conn = sqlite3.connect('todos.db')
    cursor = conn.cursor()
    
    # Get total todos
    cursor.execute('SELECT COUNT(*) FROM todos')
    total = cursor.fetchone()[0]
    
    # Get completed todos
    cursor.execute('SELECT COUNT(*) FROM todos WHERE completed = 1')
    completed = cursor.fetchone()[0]
    
    # Get pending todos
    cursor.execute('SELECT COUNT(*) FROM todos WHERE completed = 0')
    pending = cursor.fetchone()[0]
    
    # Get todos by priority
    cursor.execute('SELECT priority, COUNT(*) FROM todos GROUP BY priority')
    priority_stats = dict(cursor.fetchall())
    
    # Get todos by category
    cursor.execute('SELECT category, COUNT(*) FROM todos GROUP BY category')
    category_stats = dict(cursor.fetchall())
    
    # Get todos by folder
    cursor.execute('''
        SELECT f.name, COUNT(t.id) 
        FROM folders f 
        LEFT JOIN todos t ON f.id = t.folder_id 
        GROUP BY f.id
    ''')
    folder_stats = dict(cursor.fetchall())
    
    conn.close()
    
    return jsonify({
        'total': total,
        'completed': completed,
        'pending': pending,
        'priority_stats': priority_stats,
        'category_stats': category_stats,
        'folder_stats': folder_stats
    })

def start_flask():
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)

if __name__ == '__main__':
    # Import pending Telegram tasks on startup
    safe_print("📥 Checking for pending Telegram tasks...")
    imported_count = import_telegram_tasks_to_db()
    if imported_count > 0:
        safe_print(f"✅ Imported {imported_count} task(s) from Telegram!")
    else:
        safe_print("📭 No pending Telegram tasks.")

    # Start Flask server
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()

    import time
    time.sleep(1)

    # Start Telegram bot in background
    bot_thread = threading.Thread(target=run_telegram_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # Create window
    webview.create_window("TaskMaster", "http://127.0.0.1:5000", width=1100, height=800)
    webview.start(gui='edgechromium') 