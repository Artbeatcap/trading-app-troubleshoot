from flask import render_template, url_for
import os
from flask_mail import Message
from app import mail, app
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SGMail, Email as SGEmail, To as SGTo, Content as SGContent
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
        
        html = render_template('email/confirm_brief.html', name=subscriber.name, url=confirm_url)

        # Prefer SendGrid if configured, fallback to Flask-Mail
        sendgrid_key = app.config.get('SENDGRID_KEY') or os.getenv('SENDGRID_KEY')
        if sendgrid_key:
            try:
                sg = SendGridAPIClient(api_key=sendgrid_key)
                from_email_name, from_email_addr = app.config.get('MAIL_DEFAULT_SENDER', (None, None))
                from_email = SGEmail(from_email_addr or 'support@optionsplunge.com', from_email_name or 'Options Plunge Support')
                to_email = SGTo(subscriber.email)
                subject = 'Confirm your Morning Market Brief subscription'
                content = SGContent("text/html", html)
                sg_mail = SGMail(from_email, to_email, subject, content)
                response = sg.send(sg_mail)
                if response.status_code not in (200, 202):
                    raise RuntimeError(f"SendGrid non-2xx status: {response.status_code}")
                logger.info(f"Confirmation email sent via SendGrid to {subscriber.email}")
            except Exception as sg_err:
                logger.warning(f"SendGrid failed for {subscriber.email}: {sg_err}. Falling back to SMTP.")
                msg = Message('Confirm your Morning Market Brief subscription',
                              recipients=[subscriber.email], html=html,
                              sender=app.config['MAIL_DEFAULT_SENDER'])
                mail.send(msg)
                logger.info(f"Confirmation email sent via SMTP to {subscriber.email}")
        else:
            msg = Message('Confirm your Morning Market Brief subscription',
                          recipients=[subscriber.email], html=html,
                          sender=app.config['MAIL_DEFAULT_SENDER'])
            mail.send(msg)
            logger.info(f"Confirmation email sent to {subscriber.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending confirmation email to {subscriber.email}: {str(e)}")
        return False

def send_confirmation_email_direct(subscriber):
    """Send confirmation email using direct SendGrid (no Flask context)"""
    try:
        # Generate confirmation token if not already set
        if not subscriber.token:
            subscriber.generate_confirmation_token()
            from app import db
            db.session.commit()
        
        # Get SendGrid key
        sendgrid_key = os.getenv('SENDGRID_KEY')
        if not sendgrid_key:
            logger.error("SENDGRID_KEY not configured")
            return False
        
        # Create confirmation URL directly (no Flask url_for)
        # Use optionsplunge.com as the default domain for production
        server_name = os.getenv('SERVER_NAME', 'optionsplunge.com')
        scheme = os.getenv('PREFERRED_URL_SCHEME', 'https')
        confirm_url = f"{scheme}://{server_name}/confirm/{subscriber.token}"
        
        # Create email HTML directly (no Flask render_template)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Confirm Your Subscription</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">Confirm Your Subscription</h1>
                <p>Hi {subscriber.name},</p>
                <p>Thank you for subscribing to the Morning Market Brief!</p>
                <p>Please click the button below to confirm your subscription:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{confirm_url}" style="background-color: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Confirm Subscription</a>
                </div>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{confirm_url}</p>
                <p>If you didn't request this subscription, you can safely ignore this email.</p>
                <p>Best regards,<br>Options Plunge Team</p>
            </div>
        </body>
        </html>
        """
        
        # Send via SendGrid (direct approach like stock news email)
        sg = SendGridAPIClient(api_key=sendgrid_key)
        from_email = SGEmail("support@optionsplunge.com", "Options Plunge Support")
        to_email = SGTo(subscriber.email)
        subject = 'Confirm your Morning Market Brief subscription'
        content = SGContent("text/html", html_content)
        sg_mail = SGMail(from_email, to_email, subject, content)
        
        response = sg.send(sg_mail)
        if response.status_code in (200, 202):
            logger.info(f"Confirmation email sent via SendGrid to {subscriber.email}")
            return True
        else:
            logger.error(f"SendGrid error: {response.status_code}")
            return False
            
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
            domain = app.config.get('SERVER_NAME', 'optionsplunge.com')
            scheme = app.config.get('PREFERRED_URL_SCHEME', 'https')
            unsubscribe_url = f"{scheme}://{domain}/unsubscribe/{subscriber.email}"
            preferences_url = f"{scheme}://{domain}/market_brief"
            
            # Render the email with the brief content
            email_html = render_template('email/daily_brief.html',
                                       content=brief_html,
                                       date=date_str,
                                       unsubscribe_url=unsubscribe_url,
                                       preferences_url=preferences_url)
            
            sendgrid_key = app.config.get('SENDGRID_KEY') or os.getenv('SENDGRID_KEY')
            if sendgrid_key:
                try:
                    sg = SendGridAPIClient(api_key=sendgrid_key)
                    from_email_name, from_email_addr = app.config.get('MAIL_DEFAULT_SENDER', (None, None))
                    from_email = SGEmail(from_email_addr or 'support@optionsplunge.com', from_email_name or 'Options Plunge Support')
                    to_email = SGTo(subscriber.email)
                    subject = f'Morning Market Brief - {date_str}'
                    content = SGContent("text/html", email_html)
                    sg_mail = SGMail(from_email, to_email, subject, content)
                    resp = sg.send(sg_mail)
                    if resp.status_code not in (200, 202):
                        raise RuntimeError(f"SendGrid non-2xx status: {resp.status_code}")
                except Exception as sg_err:
                    logger.warning(f"SendGrid failed for {subscriber.email}: {sg_err}. Falling back to SMTP.")
                    msg = Message(f'Morning Market Brief - {date_str}',
                                  recipients=[subscriber.email], html=email_html,
                                  sender=app.config['MAIL_DEFAULT_SENDER'])
                    mail.send(msg)
            else:
                msg = Message(f'Morning Market Brief - {date_str}',
                              recipients=[subscriber.email], html=email_html,
                              sender=app.config['MAIL_DEFAULT_SENDER'])
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

def send_daily_brief_direct(brief_html, date_str=None):
    """Send daily brief using direct SendGrid (no Flask context)"""
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
    
    # Get SendGrid key
    sendgrid_key = os.getenv('SENDGRID_KEY')
    if not sendgrid_key:
        logger.error("SENDGRID_KEY not configured")
        return 0
    
    success_count = 0
    
    for subscriber in subscribers:
        try:
            # Create URLs directly (no Flask context)
            server_name = os.getenv('SERVER_NAME', 'optionsplunge.com')
            scheme = os.getenv('PREFERRED_URL_SCHEME', 'https')
            unsubscribe_url = f"{scheme}://{server_name}/unsubscribe/{subscriber.email}"
            preferences_url = f"{scheme}://{server_name}/market_brief"
            
            # Create email HTML directly
            email_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Morning Market Brief</title>
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    {brief_html}
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                    <p style="text-align: center; color: #666; font-size: 12px;">
                        <a href="{unsubscribe_url}">Unsubscribe</a> | 
                        <a href="{preferences_url}">Preferences</a>
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Send via SendGrid (direct approach)
            sg = SendGridAPIClient(api_key=sendgrid_key)
            from_email = SGEmail("support@optionsplunge.com", "Options Plunge Support")
            to_email = SGTo(subscriber.email)
            subject = f'Morning Market Brief - {date_str}'
            content = SGContent("text/html", email_html)
            sg_mail = SGMail(from_email, to_email, subject, content)
            
            response = sg.send(sg_mail)
            if response.status_code in (200, 202):
                # Update last_brief_sent timestamp
                subscriber.last_brief_sent = datetime.utcnow()
                from app import db
                db.session.commit()
                
                success_count += 1
                logger.info(f"Daily brief sent to {subscriber.email}")
            else:
                logger.error(f"SendGrid error for {subscriber.email}: {response.status_code}")
                
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