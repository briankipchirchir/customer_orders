from flask_restful import Resource, reqparse
from datetime import datetime
from models import db, Customer, Order
import africastalking
import re

# Africa's Talking setup for SMS
username = "sandbox"  # Replace with your Africa's Talking username
api_key = "atsk_a8ea13227600ee3759d7d30e67a96135352705af8f9dec9c2512de8c6f1b7705771388e9"  # Replace with your Africa's Talking API key
africastalking.initialize(username, api_key)
sms = africastalking.SMS

# Phone number validation function
def validate_phone_number(phone_number):
    # Define a simple pattern: only digits, length between 10 and 15
    pattern = r'^\+?\d{10,15}$'
    return re.match(pattern, phone_number)

class CustomerResource(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help="Name cannot be blank")
        parser.add_argument('code', type=str, required=True, help="Code cannot be blank")
        parser.add_argument('phone_number', type=str, help="Phone number is optional")
        args = parser.parse_args()

        # Validate phone number if provided
        if args.get('phone_number') and not validate_phone_number(args['phone_number']):
            return {'message': 'Invalid phone number format. Must be 10-15 digits.'}, 400

        # Create new customer
        new_customer = Customer(
            name=args['name'],
            code=args['code'],
            phone_number=args.get('phone_number')
        )

        db.session.add(new_customer)
        db.session.commit()
        return {'message': 'Customer added successfully', 'customer': {'name': new_customer.name, 'code': new_customer.code}}, 201


class OrderResource(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('item', type=str, required=True, help="Item cannot be blank")
        parser.add_argument('amount', type=float, required=True, help="Amount cannot be blank")
        parser.add_argument('time', type=str, required=True, help="Time cannot be blank (format: YYYY-MM-DD HH:MM:SS)")
        parser.add_argument('customer_code', type=str, required=True, help="Customer code cannot be blank")
        args = parser.parse_args()

        # Find customer by code
        customer = Customer.query.filter_by(code=args['customer_code']).first()
        if not customer:
            return {'message': 'Customer not found'}, 404

        # Convert time to datetime object
        try:
            order_time = datetime.strptime(args['time'], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return {'message': 'Invalid time format. Use YYYY-MM-DD HH:MM:SS'}, 400
        
        try:
            # Create new order
            new_order = Order(
                item=args['item'],
                amount=args['amount'],
                time=order_time,
                customer_id=customer.id
            )

            db.session.add(new_order)
            db.session.commit()

            # Send SMS to customer
            message = f"Dear {customer.name}, your order for {args['item']} has been successfully placed."
            if customer.phone_number:
                recipients = [customer.phone_number]
                try:
                    sms.send(message, recipients)
                except Exception as e:
                    return {'message': 'Failed to send SMS', 'error': str(e)}, 500

            return {
                'message': 'Order added and SMS sent',
                'customer_name': customer.name,
                'item': new_order.item,
                'order_time': new_order.time.strftime('%Y-%m-%d %H:%M:%S'),
                'amount': new_order.amount
            }, 201
        except Exception as e:
            return {'message': 'An error occurred while processing your request', 'error': str(e)}, 500



