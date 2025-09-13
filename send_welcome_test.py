from app import app
from emails import send_welcome_email
class S: pass
s=S(); s.email='support@optionsplunge.com'; s.name='Test'
with app.app_context():
    print('Triggering send_welcome_email...')
    print('Result:', send_welcome_email(s))
