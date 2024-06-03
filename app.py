from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expense_sharing.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    friends = db.relationship('Friend', backref='user', lazy=True)
    expenses = db.relationship('Expense', backref='payer', lazy=True)

class Friend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    split_between = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('signup'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if username or email already exists
        user_by_username = User.query.filter_by(username=username).first()
        user_by_email = User.query.filter_by(email=email).first()

        if user_by_username:
            flash('Username already taken', 'danger')
            return redirect(url_for('signup'))
        elif user_by_email:
            flash('Email already registered', 'danger')
            return redirect(url_for('signup'))
        else:
            new_user = User(username=username, email=email, password=generate_password_hash(password, method='sha256'))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('index'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/index')
@login_required
def index():
    friends = current_user.friends
    return render_template('index.html', friends=friends)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        description = request.form.get('description')
        amount = request.form.get('amount')
        split_between = request.form.get('split_between')
        new_expense = Expense(description=description, amount=amount, payer_id=current_user.id, split_between=split_between)
        db.session.add(new_expense)
        db.session.commit()
        return redirect(url_for('view_expenses'))
    return render_template('add_expense.html')

@app.route('/view')
@login_required
def view_expenses():
    expenses = Expense.query.filter_by(payer_id=current_user.id).all()
    return render_template('view_expenses.html', expenses=expenses)

@app.route('/balances')
@login_required
def view_balances():
    balances = calculate_balances()
    return render_template('balances.html', balances=balances)

def calculate_balances():
    balances = {}
    for friend in current_user.friends:
        balance = 0
        for expense in Expense.query.filter_by(payer_id=current_user.id).all():
            balance += expense.amount / len(expense.split_between.split(','))
        balances[friend.name] = balance
    return balances

@app.route('/add_friend', methods=['GET', 'POST'])
@login_required
def add_friend():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        new_friend = Friend(name=name, email=email, user_id=current_user.id)
        db.session.add(new_friend)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_friend.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
