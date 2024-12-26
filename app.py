import os
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import google.generativeai as genai
from google.cloud import vision

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:saishravan45@localhost/water_data'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Configure Google Vision and Gemini
GENAI_API_KEY = "AIzaSyDzD4t6Xi73eH1DwDpN8vp_YxpnIDyXL14"  # Replace with your actual API key
genai.configure(api_key=GENAI_API_KEY)

# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    product_id = db.Column(db.String(100), nullable=True)
    tenure_end_date = db.Column(db.DateTime, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    water_quality_score = db.Column(db.Integer, nullable=True)  # Score from 0 to 5

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))

        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!', 'danger')

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.product_id:
        remaining_days = (current_user.tenure_end_date - datetime.now()).days
        return render_template('dashboard.html', name=current_user.name, product_id=current_user.product_id, remaining_days=remaining_days)
    else:
        return render_template('dashboard.html', name=current_user.name, product_id=None)

@app.route('/labs', methods=['GET', 'POST'])
@login_required
def labs():
    if not current_user.product_id:
        flash('You need to buy the product to access the virtual lab.', 'danger')
        return render_template('labs.html', product_id=None)

    analysis = None  # Initialize analysis
    if request.method == 'POST':
        try:
            # Get form data
            turbidity = float(request.form['turbidity'])
            ph = float(request.form['ph'])
            hardness = float(request.form['hardness'])
            latitude = float(request.form['latitude'])
            longitude = float(request.form['longitude'])

            # Update user location
            current_user.latitude = latitude
            current_user.longitude = longitude
            db.session.commit()

            # Connect to Gemini API
            prompt = (
                f"Analyze water quality with the following parameters: "
                f"Turbidity: {turbidity}, pH: {ph}, Hardness: {hardness}. "
                f"Location: Latitude {latitude}, Longitude {longitude}. "
                f"Give a score out of 5 where 0 is worst and 5 is best, your last character in the responseshould be a single digit score,  no other character should come after that"
            )
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            analysis = response.text if response else "No analysis available."

            # Extract score (you may need to adapt this depending on the response format)
            score = int(response.text.strip().split()[-1])  # Assuming the score is the last word in the response
            current_user.water_quality_score = score
            db.session.commit()

            flash('Water quality analysis completed!', 'success')

        except Exception as e:
            print("Error in analysis:", str(e))
            flash(f"Error during analysis: {str(e)}", "danger")

    return render_template('labs.html', name=current_user.name, product_id=current_user.product_id, analysis=analysis)

@app.route('/buy', methods=['GET', 'POST'])
@login_required
def buy():
    if current_user.product_id:
        flash(f'You have already purchased the product. Product ID: {current_user.product_id}.', 'info')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        tenure = int(request.form['tenure'])
        product_id = f"PROD-{random.randint(1000, 9999)}"
        tenure_end_date = datetime.now() + timedelta(days=tenure * 30)
        current_user.product_id = product_id
        current_user.tenure_end_date = tenure_end_date
        db.session.commit()

        flash('Product purchased successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('buy.html')

@app.route('/maps')
@login_required
def maps():
    users_with_scores = User.query.filter(
        User.latitude.isnot(None),
        User.longitude.isnot(None),
        User.water_quality_score.isnot(None)
    ).all()

    # Serialize user data into a list of dictionaries
    serialized_users = [
        {
            'latitude': user.latitude,
            'longitude': user.longitude,
            'water_quality_score': user.water_quality_score
        }
        for user in users_with_scores
    ]
    return render_template('maps.html', users=serialized_users)




@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
