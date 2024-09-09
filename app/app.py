from flask import Flask, request, render_template, redirect, url_for, flash
from flask_mail import Mail, Message
import sqlite3
import random
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Mail setup
app.config['MAIL_SERVER'] = 'smtp.example.com'  # Update with actual SMTP server
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'your_email@example.com'
app.config['MAIL_PASSWORD'] = 'your_email_password'
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

# Database setup
def get_db_connection():
    conn = sqlite3.connect('secret_santa.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize DB
def init_db():
    conn = get_db_connection()
    with conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL UNIQUE,
                num_participants INTEGER
            );
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT,
                email TEXT NOT NULL,
                wishlist TEXT
            );
        ''')
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

# 1. Create Secret Santa group
@app.route('/create_group', methods=['POST'])
def create_group():
    num_participants = request.form['num_participants']
    group_id = str(uuid.uuid4())
    
    conn = get_db_connection()
    conn.execute('INSERT INTO groups (group_id, num_participants) VALUES (?, ?)', (group_id, num_participants))
    conn.commit()
    conn.close()

    group_link = f"{request.host_url}join/{group_id}"
    return render_template('group.html', group_link=group_link)

# 2. Participants join with their email
@app.route('/join/<group_id>', methods=['GET', 'POST'])
def join_group(group_id):
    if request.method == 'POST':
        email = request.form['email']
        wishlist = request.form['wishlist']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO participants (group_id, email, wishlist) VALUES (?, ?, ?)', (group_id, email, wishlist))
        conn.commit()
        conn.close()
        
        flash('You have successfully joined the group!', 'success')
        return redirect(url_for('join_group', group_id=group_id))
    
    return render_template('wishlists.html', group_id=group_id)

# 3. Once all participants are in, pair givers & receivers
@app.route('/pair/<group_id>')
def pair_givers_receivers(group_id):
    conn = get_db_connection()
    
    participants = conn.execute('SELECT email, wishlist FROM participants WHERE group_id = ?', (group_id,)).fetchall()
    conn.close()

    if len(participants) == 0:
        flash('No participants found.', 'danger')
        return redirect('/')

    givers = [p['email'] for p in participants]
    receivers = [p['email'] for p in participants]
    
    random.shuffle(receivers)

    # Ensure no one is assigned to themselves
    attempts = 0
    while any(g == r for g, r in zip(givers, receivers)) and attempts < 1000:
        random.shuffle(receivers)
        attempts += 1
    
    if attempts == 1000:
        flash('Error in pairing. Try again.', 'danger')
        return redirect('/')
    
    # 4. Send emails to givers
    for i, giver in enumerate(givers):
        receiver_email = receivers[i]
        receiver_wishlist = next(p['wishlist'] for p in participants if p['email'] == receiver_email)
        
        # Sending email to the giver
        msg = Message(f"Secret Santa Assignment", sender="your_email@example.com", recipients=[giver])
        msg.body = f"Hi {giver},\n\nYou are the Secret Santa for {receiver_email}.\n\nHere is their wishlist:\n{receiver_wishlist}\n\nHappy Holidays!"
        mail.send(msg)

    flash('All givers have been paired with receivers!', 'success')
    return redirect('/')

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

