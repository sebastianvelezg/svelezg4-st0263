import os
import logging
import sqlite3
from flask import Flask, request, jsonify
import json
from datetime import datetime
from threading import Thread
import time

HEARTBEAT_TIMEOUT = 10
SERVER_URL = os.getenv('SERVER_URL')
SERVER_PORT = os.getenv('SERVER_PORT')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

users = {
    "1": "1",
    "2": "2",
    "3": "3"
}

DATABASE = 'peers.db'

def get_db():
    db = sqlite3.connect(DATABASE) 
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS peers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                grpc_url TEXT NOT NULL,
                grpc_port TEXT NOT NULL,
                status TEXT NOT NULL,
                files TEXT NOT NULL,
                last_heartbeat TIMESTAMP
            )
        ''')
        db.commit()

def check_peer_heartbeats():
    while True:
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT username, last_heartbeat FROM peers WHERE last_heartbeat IS NOT NULL')
            peers = cursor.fetchall()
            now = datetime.utcnow()

            for peer in peers:
                last_heartbeat_str = peer['last_heartbeat']
                if last_heartbeat_str:
                    last_heartbeat = datetime.strptime(last_heartbeat_str, '%Y-%m-%d %H:%M:%S.%f')
                    if (now - last_heartbeat).total_seconds() > HEARTBEAT_TIMEOUT:
                        cursor.execute('UPDATE peers SET status = ? WHERE username = ?', ('down', peer['username']))
                    db.commit()
            time.sleep(HEARTBEAT_TIMEOUT)
        except Exception as e:
            logging.error(f"Error checking heartbeats: {e}")


@app.route('/')
def index():
    return "P2P File Sharing Server is running."

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data['username']
    password = data['password']
    grpc_url = data.get('grpc_url')
    grpc_port = data.get('grpc_port')
    status = 'online'
    files = '[]'

    if username in users and users[username] == password:
        logging.info(f"User '{username}' logged in successfully.")
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO peers (username, grpc_url, grpc_port, status, files)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                grpc_url=excluded.grpc_url,
                grpc_port=excluded.grpc_port,
                status=excluded.status,
                files=excluded.files
        ''', (username, grpc_url, grpc_port, status, files))
        db.commit()
        return jsonify({"message": f"User {username} logged in successfully"}), 200
    else:
        logging.warning(f"Login failed for user '{username}'.")
        return jsonify({"message": "Invalid username or password"}), 403
    
@app.route('/logout', methods=['POST'])
def logout():
    data = request.json
    username = data['username']

    db = get_db()
    cursor = db.cursor()

    cursor.execute('UPDATE peers SET status = ? WHERE username = ?', ('down', username))
    db.commit()

    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    username = data['username']
    now = datetime.utcnow()

    db = get_db()
    cursor = db.cursor()

    cursor.execute('UPDATE peers SET status = ?, last_heartbeat = ? WHERE username = ?', ('active', now, username))
    db.commit()

    return jsonify({"message": "Heartbeat received"}), 200

@app.route('/list_peers', methods=['GET'])
def list_peers():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT username, grpc_url, grpc_port, status, files FROM peers WHERE status = "active"')
    active_peers = cursor.fetchall()

    peers_list = []
    for peer in active_peers:
        files_list = json.loads(peer['files']) if peer['files'] else []
        num_files = len(files_list)

        peers_list.append({
            "username": peer["username"],
            "grpc_url": peer["grpc_url"],
            "grpc_port": peer["grpc_port"],
            "status": peer["status"],
            "num_files": num_files  
        })

    return jsonify(peers_list), 200

@app.route('/upload_file', methods=['POST'])
def upload_file():
    data = request.json
    username = data['username']
    filename = data['filename']
    fileurl = data['fileurl']

    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT files FROM peers WHERE username = ?', (username,))
    user_record = cursor.fetchone()

    if user_record:
        try:
            current_files = json.loads(user_record['files']) if user_record['files'] else []
        except json.JSONDecodeError:
            current_files = []

        current_files.append({'filename': filename, 'fileurl': fileurl})
        updated_files = json.dumps(current_files)

        cursor.execute('UPDATE peers SET files = ? WHERE username = ?', (updated_files, username))
        db.commit()

        return jsonify({"message": "File uploaded successfully"}), 200
    else:
        return jsonify({"message": "User not found"}), 404
    
@app.route('/list_files', methods=['GET'])
def list_files():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT files FROM peers WHERE status = 'active'")
    
    file_counts = {}
    for row in cursor.fetchall():
        peer_files = json.loads(row['files'])
        for file in peer_files:
            if file['filename'] in file_counts:
                file_counts[file['filename']]['count'] += 1
            else:
                file['count'] = 1 
                file_counts[file['filename']] = file

    return jsonify(list(file_counts.values())), 200  


@app.route('/discover_file', methods=['POST'])
def discover_file():
    data = request.json
    filename = data.get('filename')

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT username, grpc_url, grpc_port FROM peers WHERE files LIKE ?", (f'%{filename}%',))
    peers = cursor.fetchall()

    if peers:
        peers_info = [{"username": peer["username"], "grpc_url": peer["grpc_url"], "grpc_port": peer["grpc_port"]} for peer in peers]
        return jsonify(peers_info), 200
    else:
        return jsonify({"message": "File not found"}), 404


if __name__ == "__main__":
    init_db()

    heartbeat_check_thread = Thread(target=check_peer_heartbeats)
    heartbeat_check_thread.daemon = True
    heartbeat_check_thread.start()

    app.run(host='0.0.0.0', port=(SERVER_PORT), debug=True)