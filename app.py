import os
from flask import Flask, redirect, session, url_for, render_template
from flask_restful import Api
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
from models import db  # Import db from models.py
from resources import CustomerResource, OrderResource
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Set the SQLAlchemy database URI
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///customers_orders.db')  

# Auth0 Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
app.config['AUTH0_DOMAIN'] = os.getenv('AUTH0_DOMAIN')
app.config['AUTH0_CLIENT_ID'] = os.getenv('AUTH0_CLIENT_ID')
app.config['AUTH0_CLIENT_SECRET'] = os.getenv('AUTH0_CLIENT_SECRET')
app.config['AUTH0_REDIRECT_URI'] = os.getenv('AUTH0_REDIRECT_URI')
app.config['AUTH0_LOGOUT_URI'] = os.getenv('AUTH0_LOGOUT_URI')

# Initialize extensions
db.init_app(app)  
migrate = Migrate(app, db)  # Initialize Flask-Migrate with app and db
api = Api(app)  # Initialize Flask-RESTful API
oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=app.config['AUTH0_CLIENT_ID'],
    client_secret=app.config['AUTH0_CLIENT_SECRET'],
    authorize_url=f"https://{app.config['AUTH0_DOMAIN']}/authorize",
    access_token_url=f"https://{app.config['AUTH0_DOMAIN']}/oauth/token",
    api_base_url=f"https://{app.config['AUTH0_DOMAIN']}/userinfo",
    client_kwargs={'scope': 'openid profile email'},
)

# Register API resources
api.add_resource(CustomerResource, '/customers')
api.add_resource(OrderResource, '/orders')


# Utility function to ensure the user is logged in
def requires_auth(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_info' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# Route for login
@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=app.config['AUTH0_REDIRECT_URI'])


# Route for callback from Auth0
@app.route('/callback')
def callback():
    token = auth0.authorize_access_token()
    user_info = auth0.parse_id_token(token)
    session['user_info'] = user_info
    return redirect('/dashboard')


# Route for logging out
@app.route('/logout')
def logout():
    session.clear()
    return redirect(f"https://{app.config['AUTH0_DOMAIN']}/v2/logout?returnTo=http://localhost:5000")


# Dashboard route (only accessible when logged in)
@app.route('/dashboard')
@requires_auth
def dashboard():
    user_info = session['user_info']
    return render_template('dashboard.html', user_info=user_info)


# Handle login route and other application routes
@app.route('/')
def home():
    return redirect(url_for('login'))


# Start the Flask application
if __name__ == '__main__':
    app.run(debug=True)
