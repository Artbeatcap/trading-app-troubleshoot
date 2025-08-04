from flask import render_template, url_for
from flask_mail import Message
from app import mail, app
from models import MarketBriefSubscriber
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def send_confirmation_email(subscriber):
    """Send confirmation email to new subscriber"""
    try:
        # Generate confirmation token if not already set
        if not subscriber.token:
            subscriber.generate_confirmation_token()
            from app import db
            db.session.commit()
        
        # Create confirmation URL using url_for with external=True for full domain
        confirm_url = url_for('confirm_subscription',
                             token=subscriber.token,
                             _external=True,           # full https://optionsplunge.com/confirm/<token>
                             _scheme='https')          # force https in production
        
        html = render_template('email/confirm_brief.html', 
                             name=subscriber.name, 
                             url=confirm_url)
        
        msg = Message(
            'Confirm your Morning Market Brief subscription',
            recipients=[subscriber.email],
            html=html,
            sender=app.config['MAIL_DEFAULT_SENDER']
        )
        
        mail.send(msg)
        logger.info(f"Confirmation email sent to {subscriber.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending confirmation email to {subscriber.email}: {str(e)}")
        return False

def send_daily_brief_to_subscribers(brief_html, date_str=None):
    """Send daily brief to all confirmed subscribers"""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    # Get all confirmed and active subscribers
    subscribers = MarketBriefSubscriber.query.filter_by(
        confirmed=True, 
        is_active=True
    ).all()
    
    if not subscribers:
        logger.info("No confirmed subscribers found")
        return 0
    
    success_count = 0
    
    for subscriber in subscribers:
        try:
            # Create unsubscribe and preferences URLs
            domain = app.config.get('SERVER_NAME', 'localhost:5000')
            scheme = app.config.get('PREFERRED_URL_SCHEME', 'http')
            unsubscribe_url = f"{scheme}://{domain}/unsubscribe/{subscriber.email}"
            preferences_url = f"{scheme}://{domain}/market_brief"
            
            # Render the email with the brief content
            email_html = render_template('email/daily_brief.html',
                                       content=brief_html,
                                       date=date_str,
                                       unsubscribe_url=unsubscribe_url,
                                       preferences_url=preferences_url)
            
            msg = Message(
                f'Morning Market Brief - {date_str}',
                recipients=[subscriber.email],
                html=email_html,
                sender=app.config['MAIL_DEFAULT_SENDER']
            )
            
            mail.send(msg)
            
            # Update last_brief_sent timestamp
            subscriber.last_brief_sent = datetime.utcnow()
            from app import db
            db.session.commit()
            
            success_count += 1
            logger.info(f"Daily brief sent to {subscriber.email}")
            
        except Exception as e:
            logger.error(f"Error sending daily brief to {subscriber.email}: {str(e)}")
            continue
    
    logger.info(f"Daily brief sent to {success_count}/{len(subscribers)} subscribers")
    return success_count

def send_welcome_email(subscriber):
    """Send welcome email after confirmation"""
    try:
        html = render_template('email/welcome_brief.html', name=subscriber.name)
        
        msg = Message(
            'Welcome to the Morning Market Brief!',
            recipients=[subscriber.email],
            html=html,
            sender=app.config['MAIL_DEFAULT_SENDER']
        )
        
        mail.send(msg)
        logger.info(f"Welcome email sent to {subscriber.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending welcome email to {subscriber.email}: {str(e)}")
        return False

def send_admin_notification(subscriber):
    """Notify admin of new subscription"""
    try:
        admin_email = app.config.get('ADMIN_EMAIL')
        if not admin_email:
            return False
            
        msg = Message(
            'New Market Brief Subscriber',
            recipients=[admin_email],
            body=f"""
New subscriber to Morning Market Brief:
Name: {subscriber.name}
Email: {subscriber.email}
Date: {subscriber.subscribed_at.strftime('%Y-%m-%d %H:%M:%S')}
            """.strip(),
            sender=app.config['MAIL_DEFAULT_SENDER']
        )
        
        mail.send(msg)
        logger.info(f"Admin notification sent for {subscriber.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending admin notification: {str(e)}")
        return False 