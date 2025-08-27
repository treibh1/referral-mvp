#!/usr/bin/env python3
"""
Email notification system for referral requests.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
import os

class EmailNotifier:
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = os.environ.get('EMAIL_USER', 'your-email@gmail.com')
        self.sender_password = os.environ.get('EMAIL_PASSWORD', 'your-app-password')
    
    def send_referral_notification(self, user_email: str, user_name: str, 
                                 contact_details: List[Dict], job_description: str, 
                                 company: str, referral_id: str):
        """Send notification to user that their contacts have been selected."""
        
        subject = f"🎯 Your contacts have been selected for referral at {company}!"
        
        # Build contact list
        contact_list = ""
        for i, contact in enumerate(contact_details, 1):
            contact_list += f"""
{i}. {contact['First Name']} {contact['Last Name']}
   Position: {contact['Position']}
   Company: {contact['Company']}
   Match Score: {contact['match_score']}
"""
        
        # Create email body
        body = f"""
Hi {user_name},

Great news! Your LinkedIn contacts have been selected as potential candidates for a role at {company}.

📋 **Job Details:**
Company: {company}
Role: {job_description[:200]}{'...' if len(job_description) > 200 else ''}

👥 **Selected Contacts:**
{contact_list}

🎯 **Next Steps:**
1. Review the selected candidates
2. Consider if you'd like to make the referral
3. Click the link below to accept or decline the referral request

🔗 **Action Required:**
Please visit your dashboard to review and respond to this referral request:
https://your-app-url.com/referrals/{referral_id}

If you have any questions, please don't hesitate to reach out.

Best regards,
The Referral Team
"""
        
        # Send email
        self._send_email(user_email, subject, body)
    
    def send_referral_reminder(self, user_email: str, user_name: str, 
                             pending_referrals: List[Dict]):
        """Send reminder for pending referral requests."""
        
        subject = f"⏰ Reminder: You have {len(pending_referrals)} pending referral requests"
        
        body = f"""
Hi {user_name},

You have {len(pending_referrals)} pending referral request(s) that require your attention:

"""
        
        for i, referral in enumerate(pending_referrals, 1):
            body += f"""
{i}. Company: {referral['company']}
   Requested: {referral['requested_at'][:10]}
   Candidates: {len(referral['contact_ids'])} contacts
   Link: https://your-app-url.com/referrals/{referral['referral_id']}
"""
        
        body += """

Please review and respond to these requests to help your network find great opportunities!

Best regards,
The Referral Team
"""
        
        self._send_email(user_email, subject, body)
    
    def _send_email(self, recipient_email: str, subject: str, body: str):
        """Send email using SMTP."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            text = msg.as_string()
            server.sendmail(self.sender_email, recipient_email, text)
            server.quit()
            
            print(f"✅ Email sent to {recipient_email}")
            
        except Exception as e:
            print(f"❌ Failed to send email to {recipient_email}: {str(e)}")
    
    def send_welcome_email(self, user_email: str, user_name: str):
        """Send welcome email to new users."""
        subject = "🎉 Welcome to the Referral Network!"
        
        body = f"""
Hi {user_name},

Welcome to our referral network! We're excited to have you on board.

🚀 **What's Next:**
1. Upload your LinkedIn contacts
2. Your contacts will be automatically tagged and matched to job opportunities
3. You'll be notified when your contacts are selected for referrals
4. Earn rewards for successful referrals

📊 **Getting Started:**
- Visit your dashboard: https://your-app-url.com/dashboard
- Upload your LinkedIn contacts: https://your-app-url.com/import
- Check out available job opportunities: https://your-app-url.com/jobs

If you have any questions, feel free to reach out to our support team.

Best regards,
The Referral Team
"""
        
        self._send_email(user_email, subject, body)



