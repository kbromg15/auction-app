from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask_paginate import Pagination, get_page_parameter
from sqlalchemy.dialects.postgresql import UUID
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from models import db, User, AuctionItem, Bid, Sale, Watchlist, Category
from forms import LoginForm, RegisterForm, AuctionForm
import io
import csv
from sqlalchemy import inspect

# Initialize the Flask app
app = Flask(__name__)

# Configurations
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auction.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'

# Initialize the database and login manager
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print("Existing tables:", tables)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guid = db.Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    auctions = db.relationship('AuctionItem', backref='owner', lazy=True)
    bids = db.relationship('Bid', backref='bidder', lazy=True)
    sales = db.relationship('Sale', backref='seller', lazy=True)
    watchlist = db.relationship('Watchlist', backref='watcher', lazy=True)

class AuctionItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    starting_bid = db.Column(db.Float, nullable=False)
    current_bid = db.Column(db.Float, nullable=False, default=0)
    image_filename = db.Column(db.String(150))
    status = db.Column(db.String(20), default='Ongoing')
    end_time = db.Column(db.DateTime, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    bids = db.relationship('Bid', backref='auction', lazy=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    auctions = db.relationship('AuctionItem', backref='category', lazy=True)

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    auction_id = db.Column(db.Integer, db.ForeignKey('auction_item.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    auction_id = db.Column(db.Integer, db.ForeignKey('auction_item.id'), nullable=False)

# Routes

# Home Page
@app.route('/')
def index():
    return render_template('index.html')

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))  # Redirect to home if already logged in
    
    form = LoginForm()  # Create the login form instance
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()  # Fetch user from DB
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))  # Redirect to the home page after login
    
    return render_template('login.html', form=form)  # Pass the form to the template

# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Logout
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()  # Create the register form instance
    if form.validate_on_submit():
        existing_user = User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first()
        if existing_user:
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        user = User(email=form.email.data, username=form.username.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))  # Redirect to the login page after registration
    
    return render_template('register.html', form=form)  # Pass the form to the template

def serialize_bid(bid):
    auction = bid.auction
    highest_bid = max(auction.bids, key=lambda b: b.amount, default=None)
    is_winner = highest_bid and highest_bid.user_id == bid.user_id and auction.end_time < datetime.utcnow()
    return {
        'id': bid.id,
        'amount': bid.amount,
        'timestamp': bid.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'auction_id': bid.auction_id,
        'auction': {
            'title': bid.auction.title,
            'image_filename': bid.auction.image_filename,
            'end_time': bid.auction.end_time.strftime('%Y-%m-%dT%H:%M:%S')
        },
        'status': 'Won' if is_winner else 'Lost',
        'is_winner': is_winner
    }

# Add Item Page
@app.route('/add_item', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        starting_bid = request.form['starting_bid']
        end_time = request.form['end_time']
        image = request.files['image']

        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = None

        auction_item = AuctionItem(
            title=title,
            description=description,
            starting_bid=starting_bid,
            current_bid=starting_bid,
            end_time=datetime.strptime(end_time, '%Y-%m-%dT%H:%M'),
            image_filename=filename,
            owner_id=current_user.id,
            category_id=1  # Assuming a default category for simplicity
        )

        db.session.add(auction_item)
        db.session.commit()
        flash('Item added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('add_item.html')

# Auctions Page
@app.route('/auctions', methods=['GET'])
def auctions():
    search = request.args.get('search', '')
    category_id = request.args.get('category', None)

    auctions_query = AuctionItem.query
    if search:
        auctions_query = auctions_query.filter(AuctionItem.title.like(f'%{search}%'))
    if category_id:
        auctions_query = auctions_query.filter_by(category_id=category_id)

    page = request.args.get(get_page_parameter(), type=int, default=1)
    auctions = auctions_query.paginate(page=page, per_page=10)

    categories = Category.query.all()
    return render_template('auctions.html', auctions=auctions, categories=categories)

# Auction Details
@app.route('/auction/<int:id>', methods=['GET'])
def auction_details(id):
    auction = AuctionItem.query.get_or_404(id)
    return render_template('auction.html', auction=auction, datetime=datetime)

# View User's Bids
@app.route('/bids', methods=['GET'])
@login_required
def bids():
    page = request.args.get('page', 1, type=int)
    bids_query = Bid.query.filter_by(user_id=current_user.id).order_by(Bid.timestamp.desc())
    bids = bids_query.paginate(page=page, per_page=10)
    serialized_bids = [serialize_bid(bid) for bid in bids.items]
    return render_template('bids.html', bids=bids, serialized_bids=serialized_bids)


# View User's Sales
@app.route('/sales', methods=['GET'])
@login_required
def sales():
    user_sales = Sale.query.filter_by(user_id=current_user.id).all()
    return render_template('sales.html', sales=user_sales)





# View User's Watchlist
@app.route('/watchlist', methods=['GET'])
@login_required
def watchlist():
    user_watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()
    return render_template('watchlist.html', watchlist=user_watchlist)

# Add to Watchlist
@app.route('/add_to_watchlist/<int:auction_id>', methods=['POST'])
@login_required
def add_to_watchlist(auction_id):
    existing_item = Watchlist.query.filter_by(user_id=current_user.id, auction_id=auction_id).first()
    if not existing_item:
        new_watchlist_item = Watchlist(user_id=current_user.id, auction_id=auction_id)
        db.session.add(new_watchlist_item)
        db.session.commit()
        flash('Item added to watchlist', 'success')
    else:
        flash('Item already in watchlist', 'info')
    return redirect(url_for('auction_details', id=auction_id))

# Remove from Watchlist
@app.route('/remove_from_watchlist/<int:id>', methods=['POST'])
@login_required
def remove_from_watchlist(id):
    watchlist_item = Watchlist.query.get_or_404(id)
    if watchlist_item.user_id != current_user.id:
        flash('You do not have permission to remove this item', 'danger')
        return redirect(url_for('watchlist'))
    db.session.delete(watchlist_item)
    db.session.commit()
    flash('Item removed from watchlist', 'success')
    return redirect(url_for('watchlist'))

# Remove Auction (for admin or auction owner)
@app.route('/auction/<int:id>/remove', methods=['GET'])
@login_required
def remove_auction(id):
    auction = AuctionItem.query.get_or_404(id)
    if auction.owner_id != current_user.id:
        flash('You do not have permission to remove this auction.', 'danger')
        return redirect(url_for('auctions'))

    db.session.delete(auction)
    db.session.commit()
    flash('Auction removed successfully.', 'success')
    return redirect(url_for('auctions'))

# Place Bid
@app.route('/place_bid/<int:id>', methods=['POST'])
@login_required
def place_bid(id):
    auction = AuctionItem.query.get_or_404(id)
    bid_amount = request.form['bid_amount']
    if float(bid_amount) > auction.current_bid:
        new_bid = Bid(amount=bid_amount, user_id=current_user.id, auction_id=auction.id)
        auction.current_bid = bid_amount
        db.session.add(new_bid)
        db.session.commit()
        flash('Your bid has been placed successfully!', 'success')
    else:
        flash('Your bid must be higher than the current bid.', 'danger')
    return redirect(url_for('auction_details', id=auction.id))

# Run the app
if __name__ == '__main__':
    db.create_all()  # Ensure database is created
    app.run(debug=True)