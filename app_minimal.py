#!/usr/bin/env python3
"""
Minimal Working Version - Deploy First, Add Features Later
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    raise ValueError("SECRET_KEY environment variable must be set for security")

# Mock data for minimal version
mock_job_descriptions = [
    {
        'id': 1,
        'title': 'Software Engineer',
        'company': 'Tech Corp',
        'location': 'Remote',
        'description': 'Full-stack development role'
    }
]

mock_contacts = [
    {
        'id': 1,
        'name': 'John Doe',
        'title': 'Senior Developer',
        'company': 'Tech Corp',
        'location': 'San Francisco'
    }
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/job-descriptions')
def job_descriptions():
    return render_template('job_descriptions.html', job_descriptions=mock_job_descriptions)

@app.route('/referrals')
def referrals():
    return render_template('referrals.html', contacts=mock_contacts)

@app.route('/api/job-descriptions')
def api_job_descriptions():
    return jsonify(mock_job_descriptions)

@app.route('/api/contacts')
def api_contacts():
    return jsonify(mock_contacts)

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'message': 'Minimal version deployed successfully!'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
