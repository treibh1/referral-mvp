#!/usr/bin/env python3
"""
Email service for sending referral requests using SendGrid.
"""

import os
from typing import List, Dict, Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent
import json

class ReferralEmailService:
    """Service for sending referral request emails via SendGrid."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the email service."""
        self.api_key = api_key or os.getenv('SENDGRID_API_KEY')
        self.from_email = os.getenv('FROM_EMAIL', 'recruiting@company.com')
        self.from_name = os.getenv('FROM_NAME', 'Recruiting Team')
        
        # Employee email mapping for testing
        self.employee_emails = {
            'Aaron Adams': 'treibh1@gmail.com',
            'Belinda Bell': 'treibh1@gmail.com', 
            'Charles Cole': 'treibh1@gmail.com',
            'Debbie Doyle': 'treibh1@gmail.com'
        }
        
        if not self.api_key:
            print("⚠️ Warning: SENDGRID_API_KEY not found. Emails will be logged but not sent.")
    
    def get_employee_email(self, employee_name: str) -> str:
        """Get the email address for an employee."""
        return self.employee_emails.get(employee_name, f"{employee_name.lower().replace(' ', '.')}@company.com")
    
    def create_referral_email_content(self, employee_name: str, contacts: List[Dict], 
                                    job_title: str, job_location: str) -> Dict:
        """Create email content for referral request."""
        
        # Create contact list
        contact_list = []
        for contact in contacts:
            contact_info = f"{contact['name']} ({contact['position']} at {contact['company']})"
            contact_list.append(contact_info)
        
        contact_list_html = "<br>".join([f"• {contact}" for contact in contact_list])
        contact_list_text = "\n".join([f"- {contact}" for contact in contact_list])
        
        # Email subject
        subject = f"Referral Request: {len(contacts)} contacts for {job_title}"
        
        # Email body (HTML)
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">Referral Request</h2>
            
            <p>Hi {employee_name},</p>
            
            <p>We found <strong>{len(contacts)} of your contacts</strong> who would be great fits for our <strong>{job_title}</strong> position in <strong>{job_location}</strong>:</p>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                {contact_list_html}
            </div>
            
            <p>Could you please reach out to these contacts and see if they would be interested in you referring them for this role?</p>
            
            <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
                <strong>💰 We have a $5,000 referral bonus for successful placements!</strong>
            </div>
            
            <h3>Template Message You Can Use:</h3>
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; font-style: italic;">
                <p>"Hi [Contact Name],</p>
                <p>I hope you're doing well! I came across an exciting opportunity at our company for a <strong>{job_title}</strong> role that I think would be perfect for your background and experience.</p>
                <p>The position is based in <strong>{job_location}</strong> and offers competitive compensation plus great benefits. Given your experience, I believe you'd be an excellent fit.</p>
                <p>Would you be interested in learning more? I'd be happy to refer you and can provide more details about the role and company.</p>
                <p>Best regards,<br>{employee_name}"</p>
            </div>
            
            <p>Please let me know if you need any additional information or if you'd like me to help with anything else.</p>
            
            <p>Thanks!<br><strong>The Recruiting Team</strong></p>
        </div>
        """
        
        # Email body (plain text)
        text_body = f"""Hi {employee_name},

We found {len(contacts)} of your contacts who would be great fits for our {job_title} position in {job_location}:

{contact_list_text}

Could you please reach out to these contacts and see if they would be interested in you referring them for this role? 

💰 We have a $5,000 referral bonus for successful placements!

Here's a template message you can use:

"Hi [Contact Name],

I hope you're doing well! I came across an exciting opportunity at our company for a {job_title} role that I think would be perfect for your background and experience.

The position is based in {job_location} and offers competitive compensation plus great benefits. Given your experience, I believe you'd be an excellent fit.

Would you be interested in learning more? I'd be happy to refer you and can provide more details about the role and company.

Best regards,
{employee_name}"

Please let me know if you need any additional information or if you'd like me to help with anything else.

Thanks!
The Recruiting Team"""
        
        return {
            'subject': subject,
            'html_body': html_body,
            'text_body': text_body
        }
    
    def send_referral_email(self, employee_name: str, contacts: List[Dict], 
                           job_title: str, job_location: str) -> Dict:
        """Send a referral email to an employee."""
        
        try:
            # Get employee email
            to_email = self.get_employee_email(employee_name)
            
            # Create email content
            email_content = self.create_referral_email_content(
                employee_name, contacts, job_title, job_location
            )
            
            # Create email
            from_email = Email(self.from_email, self.from_name)
            to_email_obj = To(to_email, employee_name)
            subject = email_content['subject']
            html_content = HtmlContent(email_content['html_body'])
            text_content = Content("text/plain", email_content['text_body'])
            
            mail = Mail(from_email, to_email_obj, subject, text_content)
            mail.add_content(html_content)
            
            # Send email if API key is available
            if self.api_key:
                sg = SendGridAPIClient(api_key=self.api_key)
                response = sg.send(mail)
                
                return {
                    'success': True,
                    'employee': employee_name,
                    'email': to_email,
                    'contacts_count': len(contacts),
                    'status_code': response.status_code,
                    'message': f"Email sent to {employee_name} ({to_email})"
                }
            else:
                # Log email content for testing
                print(f"📧 TEST EMAIL - Would send to {employee_name} ({to_email}):")
                print(f"   Subject: {subject}")
                print(f"   Contacts: {len(contacts)}")
                print(f"   Content: {email_content['text_body'][:200]}...")
                
                return {
                    'success': True,
                    'employee': employee_name,
                    'email': to_email,
                    'contacts_count': len(contacts),
                    'status_code': 200,
                    'message': f"TEST MODE: Email logged for {employee_name} ({to_email})"
                }
                
        except Exception as e:
            return {
                'success': False,
                'employee': employee_name,
                'email': to_email,
                'error': str(e),
                'message': f"Failed to send email to {employee_name}: {str(e)}"
            }
    
    def send_bulk_referral_emails(self, contacts_by_employee: Dict[str, List[Dict]], 
                                 job_title: str, job_location: str) -> Dict:
        """Send bulk referral emails to multiple employees."""
        
        results = []
        total_emails = 0
        successful_emails = 0
        
        print(f"📧 Sending bulk referral emails to {len(contacts_by_employee)} employees...")
        
        for employee_name, contacts in contacts_by_employee.items():
            if contacts:  # Only send if there are contacts
                result = self.send_referral_email(employee_name, contacts, job_title, job_location)
                results.append(result)
                total_emails += 1
                
                if result['success']:
                    successful_emails += 1
                    print(f"   ✅ {result['message']}")
                else:
                    print(f"   ❌ {result['message']}")
        
        return {
            'success': successful_emails > 0,
            'total_emails': total_emails,
            'successful_emails': successful_emails,
            'failed_emails': total_emails - successful_emails,
            'results': results,
            'message': f"Sent {successful_emails}/{total_emails} emails successfully"
        }

