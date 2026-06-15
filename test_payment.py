import requests
import json
from datetime import datetime, timedelta
import sqlite3

BASE = 'http://localhost:8000/api/v1'

# Register new user
print('=== Register User ===')
reg = requests.post(f'{BASE}/auth/register', json={
    'username': 'paytest',
    'email': 'paytest@example.com',
    'password': 'TestPass123',
    'first_name': 'Pay',
    'last_name': 'Test'
})
print(f'Status: {reg.status_code}')

# Get verification token
conn = sqlite3.connect('event_management.db')
cursor = conn.cursor()
cursor.execute('SELECT token FROM email_verification_tokens WHERE is_used=0 ORDER BY created_at DESC LIMIT 1')
token_row = cursor.fetchone()
conn.close()
verify_token = token_row[0]

# Verify email
verify = requests.post(f'{BASE}/auth/verify-email', json={'token': verify_token})
print(f'Verify: {verify.status_code}')

# Login
login = requests.post(f'{BASE}/auth/login', json={'username': 'paytest', 'password': 'TestPass123'})
access_token = login.json()['data']['access_token']
headers = {'Authorization': f'Bearer {access_token}'}
print(f'Login: {login.status_code}')

# Admin login
admin_login = requests.post(f'{BASE}/auth/login', json={'username': 'admin', 'password': 'Admin@1234'})
admin_token = admin_login.json()['data']['access_token']
admin_headers = {'Authorization': f'Bearer {admin_token}'}

# Create event
event_date = (datetime.now() + timedelta(days=30)).isoformat()
event = requests.post(f'{BASE}/events/', headers=admin_headers, json={
    'title': 'Payment Test Event',
    'description': 'Test payment flow',
    'location': 'Online',
    'event_date': event_date,
    'total_seats': 50,
    'price': 49.99
})
event_id = event.json()['data']['id']
print(f'Event created: {event_id}')

# Book event
booking = requests.post(f'{BASE}/bookings/', headers=headers, json={
    'event_id': event_id,
    'number_of_seats': 1
})
booking_id = booking.json()['data']['id']
print(f'Booking created: {booking_id}')

# Check payment created
payments = requests.get(f'{BASE}/payments/booking/{booking_id}', headers=headers)
payment_id = payments.json()['data'][0]['id']
print(f'Payment created: {payment_id}, Status: {payments.json()["data"][0]["status"]}')

# Simulate payment success
simulate = requests.post(f'{BASE}/payments/simulate', headers=headers, json={
    'payment_id': payment_id,
    'success': True,
    'gateway_transaction_id': 'test_gateway_123'
})
print(f'Simulate: {simulate.status_code}')

# Check payment after simulation
payment = requests.get(f'{BASE}/payments/{payment_id}', headers=headers)
print(f'Payment status: {payment.json()["data"]["status"]}')
print(f'Booking payment_status: {requests.get(f"{BASE}/bookings/{booking_id}", headers=headers).json()["data"]["payment_status"]}')

# Test refund
refund = requests.post(f'{BASE}/payments/{payment_id}/refund', headers=headers, json={
    'amount': None,
    'reason': 'Test refund'
})
print(f'Refund: {refund.status_code}')

# Check payment after refund
payment = requests.get(f'{BASE}/payments/{payment_id}', headers=headers)
print(f'Payment after refund: {payment.json()["data"]["status"]}')
print(f'Booking after refund: {requests.get(f"{BASE}/bookings/{booking_id}", headers=headers).json()["data"]["payment_status"]}')

# Test payment failure simulation (new booking)
print('\n=== Test Payment Failure ===')
booking2 = requests.post(f'{BASE}/bookings/', headers=headers, json={
    'event_id': event_id,
    'number_of_seats': 1
})
booking_id2 = booking2.json()['data']['id']
payments2 = requests.get(f'{BASE}/payments/booking/{booking_id2}', headers=headers)
payment_id2 = payments2.json()['data'][0]['id']

simulate_fail = requests.post(f'{BASE}/payments/simulate', headers=headers, json={
    'payment_id': payment_id2,
    'success': False,
    'gateway_transaction_id': 'fail_gateway_456',
    'failure_reason': 'Insufficient funds'
})
print(f'Simulate failure: {simulate_fail.status_code}')

payment_fail = requests.get(f'{BASE}/payments/{payment_id2}', headers=headers)
print(f'Payment failure status: {payment_fail.json()["data"]["status"]}')
print(f'Failure reason: {payment_fail.json()["data"]["failure_reason"]}')
print(f'Booking failure payment_status: {requests.get(f"{BASE}/bookings/{booking_id2}", headers=headers).json()["data"]["payment_status"]}')

print('\n=== ALL TESTS PASSED ===')