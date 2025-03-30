
# app.py
from flask import Flask
from flask_restful import Api
from flask_migrate import Migrate
from models import db  # Import db from models.py
from resources import CustomerResource, OrderResource

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///customers_orders.db'  # SQLite database
app.config['SECRET_KEY'] = 'your_secret_key'  # Set a secret key for session management

# Initialize extensions
db.init_app(app)  # Initialize SQLAlchemy
migrate = Migrate(app, db)  # Initialize Flask-Migrate with app and db
api = Api(app)  # Initialize Flask-RESTful API

# Register API resources
api.add_resource(CustomerResource, '/customers')
api.add_resource(OrderResource, '/orders')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure tables are created before running the app
    app.run(debug=True)
