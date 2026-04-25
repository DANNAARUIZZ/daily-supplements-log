from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os
from datetime import datetime, date, timedelta

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            log_date DATE UNIQUE NOT NULL,
            taken BOOLEAN NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.before_request
def setup():
    if not hasattr(app, '_db_initialized'):
        init_db()
        app._db_initialized = True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/logs', methods=['GET'])
def get_logs():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT log_date, taken FROM logs ORDER BY log_date DESC LIMIT 100")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = {str(row['log_date']): row['taken'] for row in rows}
    return jsonify(result)

@app.route('/api/logs', methods=['POST'])
def save_log():
    data = request.json
    log_date = data.get('date')
    taken = data.get('taken')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO logs (log_date, taken)
        VALUES (%s, %s)
        ON CONFLICT (log_date) DO UPDATE SET taken = EXCLUDED.taken
    """, (log_date, taken))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
