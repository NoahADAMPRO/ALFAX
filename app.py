from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit
import json, os, paramiko, time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'alfax_ultra_secret_2025'
socketio = SocketIO(app, cors_allowed_origins="*")

DB_FILE = 'alfax_data.json'
ssh_sessions = {}

# --- GESTION BDD ---
def db_exists():
    return os.path.exists(DB_FILE)

def load_db():
    if not db_exists():
        return None
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- ROUTES PRINCIPALES ---

@app.route('/')
def index():
    if not db_exists(): return redirect(url_for('setup'))
    if 'user' not in session: return redirect(url_for('login'))
    
    db = load_db()
    curr_u = session['user']['username']
    
    # Filtrage : services dont l'utilisateur est propriétaire ou qui sont partagés avec lui
    user_services = [
        s for s in db['services'] 
        if s.get('owner') == curr_u or curr_u in s.get('shared_with', [])
    ]
    
    user_data = next((u for u in db['users'] if u['username'] == curr_u), None)
    if not user_data: return redirect(url_for('logout'))
    
    return render_template('index.html', user=user_data, services=user_services, db=db)

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if db_exists(): return redirect(url_for('login'))

    if request.method == 'POST':
        data = request.json
        admin_data = {
            "config": {
                "theme": data.get('theme', 'light'),
                "logo": data.get('project_name', 'ALFAX OS'),
                "timezone": data.get('timezone', 'Europe/Paris')
            },
            "users": [{
                "username": data.get('username'),
                "email": data.get('email'),
                "password": data.get('password'),
                "role": "ADMIN",
                "avatar": data.get('avatar'),
                "security": {
                    "question": data.get('question'),
                    "answer": data.get('answer')
                }
            }],
            "services": []
        }
        save_db(admin_data)
        return jsonify({'status': 'success'})

    return render_template('setup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if not db_exists(): return redirect(url_for('setup'))
    
    db = load_db()
    if request.method == 'POST':
        idnt = request.form.get('identifier')
        pwd = request.form.get('password')
        user = next((u for u in db['users'] if (u['username'] == idnt or u.get('email') == idnt) and u['password'] == pwd), None)
        if user:
            session['user'] = user
            return redirect(url_for('index'))
        return render_template('login.html', error="Identifiants incorrects", db=db)
    return render_template('login.html', db=db)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- GESTION DES SERVICES ---

@app.route('/add_service', methods=['POST'])
def add_service():
    if 'user' not in session: 
        return redirect(url_for('login'))
    
    db = load_db()
    
    # Création de l'objet service avec un ID unique basé sur le timestamp
    new_service = {
        "id": str(int(time.time())),
        "name": request.form.get('name'),
        "type": request.form.get('type'),
        "icon": request.form.get('icon'),
        "url_or_ip": request.form.get('url_or_ip'),
        "ssh_user": request.form.get('ssh_user'),
        "ssh_pass": request.form.get('ssh_pass'),
        "owner": session['user']['username'],
        "shared_with": []
    }
    
    db['services'].append(new_service)
    save_db(db)
    
    return redirect(url_for('index'))

# --- API UTILISATEURS & RÉGLAGES ---

@app.route('/api/manage_users', methods=['POST'])
def manage_users():
    if 'user' not in session: return jsonify({'status': 'error'})
    data = request.json
    db = load_db()
    action = data.get('action')
    
    if action == 'add' and session['user']['role'] == 'ADMIN':
        db['users'].append({
            "username": data['username'],
            "email": data['email'],
            "password": data['password'],
            "role": data['role'],
            "avatar": f"https://api.dicebear.com/7.x/avataaars/svg?seed={data['username']}"
        })
    elif action == 'delete' and session['user']['role'] == 'ADMIN':
        db['users'] = [u for u in db['users'] if u['username'] != data['username']]
    elif action == 'delete_self':
        db['users'] = [u for u in db['users'] if u['username'] != session['user']['username']]
        save_db(db)
        session.clear()
        return jsonify({'status': 'redirect', 'url': '/login'})
    elif action == 'admin_update_pass' and session['user']['role'] == 'ADMIN':
        for u in db['users']:
            if u['username'] == data['username']:
                u['password'] = data['new_pass']
    
    save_db(db)
    return jsonify({'status': 'success'})

@app.route('/api/share_service', methods=['POST'])
def share_service():
    if 'user' not in session or session['user']['role'] != 'ADMIN': return jsonify({'status': 'error'})
    data = request.json
    db = load_db()
    target_user = next((u for u in db['users'] if u['username'] == data['target'] or u.get('email') == data['target']), None)
    if not target_user: return jsonify({'error': 'Utilisateur introuvable'})
    
    for s in db['services']:
        if s['id'] == data['service_id']:
            if target_user['username'] not in s['shared_with']:
                s['shared_with'].append(target_user['username'])
    save_db(db)
    return jsonify({'status': 'success'})

@app.route('/api/update_settings', methods=['POST'])
def update_settings():
    db = load_db()
    data = request.json
    if 'theme' in data: db['config']['theme'] = data['theme']
    if 'logo' in data: db['config']['logo'] = data['logo']
    save_db(db)
    return jsonify({'status': 'success'})

@app.route('/api/update_password', methods=['POST'])
def update_password():
    db = load_db()
    new_p = request.json.get('password')
    for u in db['users']:
        if u['username'] == session['user']['username']:
            u['password'] = new_p
    save_db(db)
    return jsonify({'status': 'success'})

# --- SSH SOCKET ---

def listen_to_ssh(sid, chan):
    while True:
        try:
            if chan.recv_ready():
                data = chan.recv(1024).decode('utf-8', 'ignore')
                socketio.emit('ssh_output', {'data': data}, room=sid)
            socketio.sleep(0.01)
        except: break

@socketio.on('connect_ssh')
def handle_ssh_connect(data):
    try:
        global ssh_sessions
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(data['host'], username=data['user'], password=data['pass'], timeout=5)
        chan = client.invoke_shell(term='xterm')
        ssh_sessions[request.sid] = chan
        socketio.start_background_task(target=listen_to_ssh, sid=request.sid, chan=chan)
    except Exception as e:
        socketio.emit('ssh_output', {'data': f"\r\n\x1b[31m[ERREUR] {str(e)}\x1b[0m\r\n"}, room=request.sid)

@socketio.on('ssh_input')
def handle_ssh_input(data):
    if request.sid in ssh_sessions:
        try: ssh_sessions[request.sid].send(data['input'])
        except: pass

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)