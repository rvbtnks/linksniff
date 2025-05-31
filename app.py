# app.py
# Version: 0.4 - Fixed excessive database writes and WAL bloat

import os
import sqlite3
import subprocess
import threading
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

# --- paths & defaults ---
APP_DIR             = os.path.abspath(os.path.dirname(__file__))
DATA_DIR            = os.path.join(APP_DIR, 'data')
DB_PATH             = os.path.join(DATA_DIR, 'tasks.db')
SETTINGS_PATH       = os.path.join(DATA_DIR, 'settings.json')
SCRIPTS_DIR         = '/app/scripts'
MEDIA_DIR           = '/media'
DEFAULT_CONCURRENCY = 3

# ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Thread-local storage for database connections
thread_local = threading.local()

def get_db_connection():
    """Get a thread-local database connection"""
    if not hasattr(thread_local, 'connection'):
        thread_local.connection = sqlite3.connect(
            DB_PATH, 
            timeout=30.0,
            check_same_thread=False
        )
        # Enable WAL mode with better checkpoint settings
        thread_local.connection.execute('PRAGMA journal_mode=WAL')
        thread_local.connection.execute('PRAGMA synchronous=NORMAL')
        thread_local.connection.execute('PRAGMA cache_size=1000')
        thread_local.connection.execute('PRAGMA temp_store=memory')
        # More aggressive WAL checkpointing
        thread_local.connection.execute('PRAGMA wal_autocheckpoint=1000')
    return thread_local.connection

def close_db_connection():
    """Close thread-local database connection"""
    if hasattr(thread_local, 'connection'):
        thread_local.connection.close()
        delattr(thread_local, 'connection')

def checkpoint_database():
    """Force a WAL checkpoint"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        conn.close()
        print("Database checkpoint completed")
    except Exception as e:
        print(f"Error during checkpoint: {e}")

# initialize SQLite schema with WAL mode
conn = sqlite3.connect(DB_PATH)
conn.execute('PRAGMA journal_mode=WAL')
conn.execute('PRAGMA synchronous=NORMAL')
conn.execute('PRAGMA wal_autocheckpoint=1000')
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER PRIMARY KEY,
    script       TEXT    NOT NULL,
    url          TEXT    NOT NULL,
    status       TEXT    NOT NULL,
    added_time   TEXT    NOT NULL,
    start_time   TEXT,
    end_time     TEXT,
    log          TEXT
)
""")
conn.commit()
conn.close()

# Force initial checkpoint
checkpoint_database()

# load or create settings
if os.path.exists(SETTINGS_PATH):
    with open(SETTINGS_PATH) as f:
        settings = json.load(f)
else:
    settings = {'concurrency': DEFAULT_CONCURRENCY}
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f)

lock = threading.Lock()
active_count = 0

def save_settings():
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f)

def execute_db_query(query, params=(), fetch=False):
    """Execute database query with proper error handling"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(query, params)
            
            if fetch:
                result = cur.fetchall()
                return result
            else:
                conn.commit()
                return cur.lastrowid if cur.lastrowid else None
                
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"Database locked, retrying... (attempt {attempt + 1})")
                time.sleep(0.1 * (attempt + 1))
                continue
            else:
                print(f"Database error: {e}")
                raise
        except Exception as e:
            print(f"Unexpected database error: {e}")
            raise

def process_queue():
    """Enforce one session per distinct site, up to concurrency limit."""
    try:
        maxc = settings.get('concurrency', DEFAULT_CONCURRENCY)

        # Determine which scripts are already running
        active_scripts_rows = execute_db_query(
            "SELECT DISTINCT script FROM tasks WHERE status='active'", 
            fetch=True
        )
        active_scripts = {row[0] for row in active_scripts_rows}

        # Calculate available slots
        slots = maxc - len(active_scripts)
        if slots <= 0:
            return

        # Fetch pending tasks, oldest first
        pending_rows = execute_db_query(
            "SELECT id, script, url FROM tasks "
            "WHERE status='pending' "
            "ORDER BY added_time ASC",
            fetch=True
        )

        started = 0
        for tid, script, url in pending_rows:
            if started >= slots:
                break
            if script in active_scripts:
                continue
            threading.Thread(
                target=run_task,
                args=(tid, script, url),
                daemon=True
            ).start()
            active_scripts.add(script)
            started += 1
            
    except Exception as e:
        print(f"Error in process_queue: {e}")

def run_task(tid, script, url):
    global active_count
    out_dir = os.path.join(MEDIA_DIR, script)
    os.makedirs(out_dir, exist_ok=True)

    try:
        # mark task as active
        execute_db_query(
            "UPDATE tasks SET status=?, start_time=? WHERE id=?",
            ('active', datetime.utcnow().isoformat(), tid)
        )

        # run the linksniff script
        script_file = os.path.join(SCRIPTS_DIR, f'linksniff-{script}.py')
        proc = subprocess.Popen(
            ['python', script_file, url],
            cwd=out_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        log_lines = []
        line_count = 0
        last_update = time.time()
        
        # FIXED: Batch log updates instead of updating every line
        for line in proc.stdout:
            log_lines.append(line)
            line_count += 1
            
            # Update database every 50 lines OR every 10 seconds
            current_time = time.time()
            if line_count >= 50 or (current_time - last_update) >= 10:
                try:
                    log_text = ''.join(log_lines)
                    execute_db_query("UPDATE tasks SET log=? WHERE id=?", (log_text, tid))
                    last_update = current_time
                    line_count = 0  # Reset counter but keep log_lines for final update
                except Exception as e:
                    print(f"Error updating log for task {tid}: {e}")

        # Final log update with complete output
        try:
            final_log = ''.join(log_lines)
            execute_db_query("UPDATE tasks SET log=? WHERE id=?", (final_log, tid))
        except Exception as e:
            print(f"Error with final log update for task {tid}: {e}")

        code = proc.wait()
        status = 'completed' if code == 0 else 'failed'
        end_t = datetime.utcnow().isoformat()

        # Final status update
        execute_db_query(
            "UPDATE tasks SET status=?, end_time=? WHERE id=?",
            (status, end_t, tid)
        )

    except Exception as e:
        print(f"Error in run_task {tid}: {e}")
        try:
            execute_db_query(
                "UPDATE tasks SET status=?, end_time=? WHERE id=?",
                ('failed', datetime.utcnow().isoformat(), tid)
            )
        except Exception as update_error:
            print(f"Error updating failed status for task {tid}: {update_error}")
    finally:
        close_db_connection()
        with lock:
            active_count -= 1

# Schedule queue processing and periodic checkpoints
scheduler = BackgroundScheduler()
scheduler.add_job(process_queue, 'interval', seconds=5)
scheduler.add_job(checkpoint_database, 'interval', minutes=15)  # Checkpoint every 15 minutes
scheduler.start()

# --- Flask app ---
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/jobs')
def jobs():
    try:
        rows = execute_db_query(
            "SELECT id, script, url, status, added_time, start_time, end_time "
            "FROM tasks ORDER BY id DESC",
            fetch=True
        )
        
        return jsonify({
            'jobs': [
                {
                    'id':    r[0],
                    'script':r[1],
                    'url':   r[2],
                    'status':r[3],
                    'added': r[4],
                    'start': r[5],
                    'end':   r[6]
                } for r in rows
            ],
            'concurrency': settings.get('concurrency', DEFAULT_CONCURRENCY)
        })
    except Exception as e:
        print(f"Error in /jobs: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/add', methods=['POST'])
def add():
    try:
        url = request.json.get('url', '').strip()
        host = url.split('//')[-1].split('/')[0]
        name = host.split('.')[-2] if '.' in host else host
        script_path = os.path.join(SCRIPTS_DIR, f'linksniff-{name}.py')
        if not os.path.isfile(script_path):
            return jsonify({'error': f'No script for site "{name}"'}), 400

        now = datetime.utcnow().isoformat()
        tid = execute_db_query(
            "INSERT INTO tasks(script, url, status, added_time) VALUES (?, ?, ?, ?)",
            (name, url, 'pending', now)
        )
        return jsonify({'id': tid})
    except Exception as e:
        print(f"Error in /add: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/requeue/<int:tid>', methods=['POST'])
def requeue(tid):
    try:
        rows = execute_db_query("SELECT status FROM tasks WHERE id=?", (tid,), fetch=True)
        if not rows or rows[0][0] != 'failed':
            return jsonify({'error': 'Not a failed task'}), 400
            
        execute_db_query(
            "UPDATE tasks SET status='pending', log=NULL, start_time=NULL, end_time=NULL WHERE id=?",
            (tid,)
        )
        return jsonify({'id': tid})
    except Exception as e:
        print(f"Error in /requeue: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/clear_completed', methods=['POST'])
def clear_completed():
    try:
        execute_db_query("DELETE FROM tasks WHERE status='completed'")
        # Force checkpoint after cleanup
        checkpoint_database()
        return '', 204
    except Exception as e:
        print(f"Error in /clear_completed: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/clear_all', methods=['POST'])
def clear_all():
    try:
        execute_db_query("DELETE FROM tasks")
        # Force checkpoint after cleanup
        checkpoint_database()
        return '', 204
    except Exception as e:
        print(f"Error in /clear_all: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/set_concurrency', methods=['POST'])
def set_concurrency():
    try:
        val = int(request.json.get('concurrency', DEFAULT_CONCURRENCY))
        settings['concurrency'] = val
        save_settings()
        return '', 204
    except Exception as e:
        print(f"Error in /set_concurrency: {e}")
        return jsonify({'error': 'Settings error'}), 500

@app.route('/update_ytdlp', methods=['POST'])
def update_ytdlp():
    try:
        print("Starting yt-dlp update...")
        result = subprocess.run(
            ['pip', 'install', '--upgrade', 'yt-dlp'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print("yt-dlp updated successfully")
            return jsonify({'success': True, 'message': 'yt-dlp updated successfully'})
        else:
            print(f"yt-dlp update failed: {result.stderr}")
            return jsonify({'success': False, 'error': result.stderr}), 500
            
    except subprocess.TimeoutExpired:
        print("yt-dlp update timed out")
        return jsonify({'success': False, 'error': 'Update timed out'}), 500
    except Exception as e:
        print(f"Error updating yt-dlp: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Add a manual checkpoint endpoint for emergency cleanup
@app.route('/checkpoint_db', methods=['POST'])
def manual_checkpoint():
    try:
        checkpoint_database()
        return jsonify({'success': True, 'message': 'Database checkpoint completed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9559)
