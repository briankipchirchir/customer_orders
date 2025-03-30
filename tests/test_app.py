import unittest
from app import app, db
from models import Customer, Order

class TestFlaskAPI(unittest.TestCase):

    # Set up the test environment
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        # Create the tables in the test database
        with app.app_context():
            db.create_all()

    # Clean up after each test
    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # Test case for valid customer creation
    def test_create_customer(self):
        response = self.app.post('/customers', json={
            'name': 'brian',
            'code': '5555',
            'phone_number': '+254746110366'
        })
        self.assertEqual(response.status_code, 201)
        response_json = response.get_json()
        self.assertIn('Customer added successfully', response_json['message'])

    # Test case for valid order creation
    def test_create_order(self):
        # Create a customer to associate with the order
        customer = Customer(name="brian", code="1234", phone_number="254746110366")
        with app.app_context():
            db.session.add(customer)
            db.session.commit()

        # Create an order for the customer
        response = self.app.post('/orders', json={
            'item': 'Laptop',
            'amount': 1500.50,
            'time': '2025-03-30 14:30:00',
            'customer_code': '5555'
        })

        self.assertEqual(response.status_code, 201)
        response_json = response.get_json()
        self.assertIn('Order added and SMS sent', response_json['message'])
        self.assertIn('Laptop', response_json['order']['item'])
        self.assertIn('brian', response_json['order']['customer_name'])
        self.assertEqual(response_json['order']['amount'], 1500.50)
        self.assertEqual(response_json['order']['time'], '2025-03-30 14:30:00')

    # Test invalid customer creation (missing name)
    def test_create_customer_invalid(self):
        response = self.app.post('/customers', json={
            'code': '5555'  # Missing 'name'
        })
        self.assertEqual(response.status_code, 400)
        response_json = response.get_json()
        self.assertIn('name', response_json['message'])  # Check for missing 'name' field under 'message'

    # Test invalid order creation (invalid time format)
    def test_create_order_invalid_time(self):
        response = self.app.post('/orders', json={
            'item': 'Laptop',
            'amount': 1500.50,
            'time': 'invalid_time',  # Invalid time format
            'customer_code': '1234'
        })
        self.assertEqual(response.status_code, 400)  # Ensure bad request due to invalid time format
        response_json = response.get_json()
        self.assertIn('Invalid time format', response_json['message'])  # Ensure proper error message

    # Test case for missing 'item' in the order
    def test_create_order_missing_item(self):
        customer = Customer(name="brian", code="1234", phone_number="254746110366")
        with app.app_context():
            db.session.add(customer)
            db.session.commit()

        response = self.app.post('/orders', json={
            'amount': 1500.50,
            'time': '2025-03-30 14:30:00',
            'customer_code': '1234'  # Missing 'item'
        })
        self.assertEqual(response.status_code, 400)  # Ensure it fails due to missing 'item'
        response_json = response.get_json()
        self.assertIn('item', response_json['message'])  # Check for missing 'item' field under 'message'

if __name__ == '__main__':
    unittest.main()
