from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS supplements (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS supplement_logs (
            id SERIAL PRIMARY KEY,
            supplement_id INTEGER REFERENCES supplements(id) ON DELETE CASCADE,
            log_date DATE NOT NULL,
            taken BOOLEAN NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(supplement_id, log_date)
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

@app.route('/api/supplements', methods=['GET'])
def get_supplements():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, name FROM supplements ORDER BY created_at")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)

@app.route('/api/supplements', methods=['POST'])
def add_supplement():
    name = request.json.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("INSERT INTO supplements (name) VALUES (%s) RETURNING id, name", (name,))
        row = cur.fetchone()
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({'error': 'Supplement already exists'}), 409
    cur.close()
    conn.close()
    return jsonify(row), 201

@app.route('/api/supplements/<int:sid>', methods=['DELETE'])
def delete_supplement(sid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM supplements WHERE id = %s", (sid,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT sl.supplement_id, sl.log_date, sl.taken
        FROM supplement_logs sl
        ORDER BY sl.log_date DESC
        LIMIT 500
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = {}
    for r in rows:
        sid = str(r['supplement_id'])
        if sid not in result:
            result[sid] = {}
        result[sid][str(r['log_date'])] = r['taken']
    return jsonify(result)

@app.route('/api/logs', methods=['POST'])
def save_log():
    data = request.json
    sid = data.get('supplement_id')
    log_date = data.get('date')
    taken = data.get('taken')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO supplement_logs (supplement_id, log_date, taken)
        VALUES (%s, %s, %s)
        ON CONFLICT (supplement_id, log_date) DO UPDATE SET taken = EXCLUDED.taken
    """, (sid, log_date, taken))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
