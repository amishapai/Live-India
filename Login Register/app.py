from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'users.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        db = get_db()
        # Create tables
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_type TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                language_preferences TEXT,
                destination TEXT,
                certificate TEXT
            );
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS guides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                language_preferences TEXT,
                location TEXT,
                certificate TEXT
            );
        ''')
        db.commit()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']
        
        db = get_db()
        if user_type == 'Tourist':
            user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        else:
            user = db.execute('SELECT * FROM guides WHERE email = ?', (email,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_type'] = user_type
            return redirect(url_for('profile'))
        else:
            flash('Invalid login credentials.')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_type = request.form['user_type']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        language_preferences = request.form.getlist('language_preferences')
        destination = request.form.get('destination') if user_type == 'Tourist' else None
        location = request.form.get('location') if user_type == 'Tour Guide' else None
        certificate = request.files.get('certificate')
        certificate_path = None
        
        if certificate:
            certificate_path = f"static/{certificate.filename}"
            certificate.save(certificate_path)
        
        db = get_db()
        
        if user_type == 'Tourist':
            db.execute('INSERT INTO users (user_type, email, username, password, language_preferences, destination, certificate) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (user_type, email, username, hashed_password, ','.join(language_preferences), destination, certificate_path))
        else:
            db.execute('INSERT INTO guides (email, username, password, language_preferences, location, certificate) VALUES (?, ?, ?, ?, ?, ?)',
                       (email, username, hashed_password, ','.join(language_preferences), location, certificate_path))
        
        db.commit()
        
        flash('Registration successful. Please log in.')
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    
    if not user_id:
        return redirect(url_for('index'))
    
    db = get_db()
    user = db.execute(f'SELECT * FROM {"users" if user_type == "Tourist" else "guides"} WHERE id = ?', (user_id,)).fetchone()
    
    if user_type == 'Tourist':
        user_languages = set(user['language_preferences'].split(','))
        guides = db.execute('SELECT * FROM guides WHERE location = ?', (user['destination'],)).fetchall()
        
        matching_guides = []
        for guide in guides:
            guide_languages = set(guide['language_preferences'].split(','))
            if user_languages.intersection(guide_languages):
                matching_guides.append(guide)
    else:
        matching_guides = []

    return render_template('profile.html', user=user, user_type=user_type, matching_guides=matching_guides)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_type', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)
