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
    
    def send_team_invitation_email(self, employee_name: str, employee_email: str, 
                                 role: str, company_name: str, inviter_name: str) -> Dict:
        """Send team invitation email to new team member."""
        
        try:
            # Email subject
            subject = f"You've been invited to join {company_name} on Referral System"
            
            # Email body (HTML)
            html_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2c3e50;">Welcome to {company_name}!</h2>
                
                <p>Hi {employee_name},</p>
                
                <p><strong>{inviter_name}</strong> has invited you to join <strong>{company_name}</strong> on our Referral System as a <strong>{role.title()}</strong>.</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #2c3e50; margin-top: 0;">What you can do as a {role.title()}:</h3>
                    <ul style="color: #555;">
                        {self._get_role_permissions_html(role)}
                    </ul>
                </div>
                
                <div style="background-color: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <h3 style="color: #155724; margin-top: 0;">🚀 Get Started</h3>
                    <p style="margin-bottom: 15px;">To join your team, simply:</p>
                    <ol style="color: #155724;">
                        <li>Go to: <strong>https://web-production-2d975.up.railway.app/login</strong></li>
                        <li>Enter your email: <strong>{employee_email}</strong></li>
                        <li>Enter your name: <strong>{employee_name}</strong></li>
                        <li>Click "Login" to access your dashboard</li>
                    </ol>
                </div>
                
                <div style="background-color: #e7f3ff; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #007bff;">
                    <h3 style="color: #004085; margin-top: 0;">💡 Need Help?</h3>
                    <p style="color: #004085; margin-bottom: 0;">If you have any questions, feel free to reach out to {inviter_name} or contact our support team.</p>
                </div>
                
                <p>Welcome to the team!</p>
                <p><strong>The {company_name} Team</strong></p>
            </div>
            """
            
            # Email body (plain text)
            text_body = f"""Welcome to {company_name}!

Hi {employee_name},

{inviter_name} has invited you to join {company_name} on our Referral System as a {role.title()}.

What you can do as a {role.title()}:{self._get_role_permissions_text(role)}

🚀 Get Started:
To join your team, simply:
1. Go to: https://web-production-2d975.up.railway.app/login
2. Enter your email: {employee_email}
3. Enter your name: {employee_name}
4. Click "Login" to access your dashboard

💡 Need Help?
If you have any questions, feel free to reach out to {inviter_name} or contact our support team.

Welcome to the team!
The {company_name} Team"""
            
            # Create email
            from_email = Email(self.from_email, self.from_name)
            to_email_obj = To(employee_email, employee_name)
            html_content = HtmlContent(html_body)
            text_content = Content("text/plain", text_body)
            
            mail = Mail(from_email, to_email_obj, subject, text_content)
            mail.add_content(html_content)
            
            # Send email if API key is available
            if self.api_key:
                sg = SendGridAPIClient(api_key=self.api_key)
                response = sg.send(mail)
                
                return {
                    'success': True,
                    'employee': employee_name,
                    'email': employee_email,
                    'role': role,
                    'status_code': response.status_code,
                    'message': f"Invitation email sent to {employee_name} ({employee_email})"
                }
            else:
                # Log email content for testing
                print(f"📧 TEST INVITATION EMAIL - Would send to {employee_name} ({employee_email}):")
                print(f"   Subject: {subject}")
                print(f"   Role: {role}")
                print(f"   Company: {company_name}")
                
                return {
                    'success': True,
                    'employee': employee_name,
                    'email': employee_email,
                    'role': role,
                    'status_code': 200,
                    'message': f"TEST MODE: Invitation email logged for {employee_name} ({employee_email})"
                }
                
        except Exception as e:
            return {
                'success': False,
                'employee': employee_name,
                'email': employee_email,
                'error': str(e),
                'message': f"Failed to send invitation email to {employee_name}: {str(e)}"
            }
    
    def _get_role_permissions_html(self, role: str) -> str:
        """Get role permissions as HTML list items."""
        permissions = {
            'admin': [
                '<li>Invite team members (employees, recruiters, admins)</li>',
                '<li>Search all company contacts</li>',
                '<li>Use bulk email features</li>',
                '<li>Manage company settings</li>',
                '<li>View company dashboard and analytics</li>'
            ],
            'recruiter': [
                '<li>Search all company contacts</li>',
                '<li>Use bulk email features</li>',
                '<li>Request referrals from employees</li>',
                '<li>View job matching results</li>',
                '<li>Access referral management tools</li>'
            ],
            'employee': [
                '<li>Upload your own contacts</li>',
                '<li>Search only your contacts</li>',
                '<li>Request referrals for your contacts</li>',
                '<li>Respond to referral requests</li>',
                '<li>View your referral activity</li>'
            ]
        }
        return ''.join(permissions.get(role, ['<li>Access basic features</li>']))
    
    def _get_role_permissions_text(self, role: str) -> str:
        """Get role permissions as plain text."""
        permissions = {
            'admin': [
                '• Invite team members (employees, recruiters, admins)',
                '• Search all company contacts',
                '• Use bulk email features',
                '• Manage company settings',
                '• View company dashboard and analytics'
            ],
            'recruiter': [
                '• Search all company contacts',
                '• Use bulk email features',
                '• Request referrals from employees',
                '• View job matching results',
                '• Access referral management tools'
            ],
            'employee': [
                '• Upload your own contacts',
                '• Search only your contacts',
                '• Request referrals for your contacts',
                '• Respond to referral requests',
                '• View your referral activity'
            ]
        }
        return '\n' + '\n'.join(permissions.get(role, ['• Access basic features']))

