from flask_restful import Resource, reqparse
from datetime import datetime
from models import db, Customer, Order
import africastalking
import re
import requests
from jose import jwt
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Africa's Talking setup for SMS
username = os.getenv('AFRICASTALKING_USERNAME') 
api_key = os.getenv('AFRICASTALKING_API_KEY')  
africastalking.initialize(username, api_key)
sms = africastalking.SMS

AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')

# Phone number validation function
def validate_phone_number(phone_number):

    pattern = r'^\+?\d{10,15}$'
    return re.match(pattern, phone_number)

# JWT Decoding & Verification
def get_rsa_key(token):
    """
    Retrieve RSA public key from Auth0's JWKS endpoint to verify JWT token.
    """
    try:
        
        response = requests.get(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json")
        response.raise_for_status()
        jwks = response.json()

        
        unverified_header = jwt.get_unverified_header(token)
        if unverified_header is None:
            raise ValueError("Unable to find header")

        rsa_key = {}
        for key in jwks['keys']:
            if key['kid'] == unverified_header['kid']:
                rsa_key = {
                    'kty': key['kty'],
                    'kid': key['kid'],
                    'use': key['use'],
                    'n': key['n'],
                    'e': key['e'],
                }
                break

        if not rsa_key:
            raise ValueError(f"Unable to find appropriate key for kid: {unverified_header['kid']}")

        return rsa_key
    
    except Exception as e:
        print(f"Error getting RSA key: {str(e)}")
        raise

def verify_jwt_token(token):
    """
    Verify the JWT token with the public key from Auth0.
    """
    try:
        # Get the RSA public key dynamically
        rsa_key = get_rsa_key(token)

        # Decode the JWT token using the RSA public key
        payload = jwt.decode(token, rsa_key, algorithms=['RS256'], audience="your-api-identifier")
        
        # The payload will contain the claims from the JWT
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.JWTClaimsError:
        raise ValueError("Invalid claims")
    except Exception as e:
        raise ValueError(f"Invalid token: {str(e)}")

class CustomerResource(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help="Name cannot be blank")
        parser.add_argument('code', type=str, required=True, help="Code cannot be blank")
        parser.add_argument('phone_number', type=str, help="Phone number is optional")
        parser.add_argument('Authorization', type=str, required=True, help="Authorization token is required")
        args = parser.parse_args()

        # Verify the Authorization token
        try:
            token = args['Authorization'].split(" ")[1]  # Bearer <token>
            verify_jwt_token(token)
        except Exception as e:
            return {'message': f'Unauthorized: {str(e)}'}, 401

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
        parser.add_argument('Authorization', type=str, required=True, help="Authorization token is required")
        args = parser.parse_args()

        # Verify the Authorization token
        try:
            token = args['Authorization'].split(" ")[1]  # Bearer <token>
            verify_jwt_token(token)
        except Exception as e:
            return {'message': f'Unauthorized: {str(e)}'}, 401

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
