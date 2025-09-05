from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import pickle
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Use a strong secret key in production

# Initialize SQLite3 database
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # Create a table for users if it doesn't already exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

# Decorator to ensure user is logged in
def login_required(route_function):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return route_function(*args, **kwargs)
    wrapper.__name__ = route_function.__name__
    return wrapper

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            # Save new user in SQLite3 database
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return 'Username already exists. Please choose another one.'
    return render_template('signup.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Verify user credentials
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]  # Store user ID in session
            return redirect(url_for('predict'))
        else:
            return 'Invalid username or password'
    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove user ID from session
    return redirect(url_for('home'))

def predict_transaction( Amount,Old_balance, New_balance, Transaction_type,Location, is_vpn):
    with open('KNN.pkl', 'rb') as model_file:
            model = pickle.load(model_file)
    new_data = {
        'Amount': Amount,
        'Old_balance':Old_balance,
        'New_balance': New_balance,
        'Transaction_type': Transaction_type,
        'Location': Location,
        'is_vpn': is_vpn
    }



    # Convert to DataFrame
    new_df = pd.DataFrame([new_data])

    # Ensure columns match model training data
    prediction_result = model.predict(new_df)
    
    return prediction_result[0]

# Prediction route
@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    if request.method == 'POST':
        Amount = float(request.form['Amount'])
        Old_balance = float(request.form['Old_balance'])
        New_balance = float(request.form['New_balance'])
        Transaction_type = request.form['Transaction_type']
        Location = request.form['Location']
        is_vpn = request.form['is_vpn']
        email = request.form['email']  # Email from user

        # Predict the result
        prediction_result = predict_transaction(Amount, Old_balance, New_balance, Transaction_type, Location, is_vpn)
        print(prediction_result)

        # SMTP Configuration
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        from_email = 'cyberfranklin007@gmail.com'
        password = 'qdworfxufzgpgphj'

        to_email = email  # Send to user

        # Compose Email
        subject = "Transaction Prediction Result"
        body = f"""
Hello,

This is to inform you about the result of your transaction analysis.

Prediction Result: {'FRAUD' if prediction_result == 'yes' else 'GENUINE'}

Thank you,
Cyber Franklin Bot
"""

        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
            print("✅ Email sent successfully!")
            server.quit()
        except Exception as e:
            print("❌ Error sending email:", e)

        return render_template('result.html', prediction=prediction_result)

    return render_template('predict.html')




if __name__ == '__main__':
    init_db() 
    app.run(debug=True)
