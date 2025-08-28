#!/usr/bin/env python3
"""
Simple Flask web application for the referral matching system.
Demonstrates how to integrate the unified matcher into a web interface.
"""

from flask import Flask, render_template, request, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)

# Simple in-memory storage for demo
job_descriptions = []
contacts = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/job-descriptions')
def job_descriptions_page():
    return render_template('job_descriptions.html')

@app.route('/referrals')
def referrals_page():
    return render_template('referrals.html')

@app.route('/api/job-descriptions', methods=['GET', 'POST'])
def api_job_descriptions():
    if request.method == 'POST':
        data = request.get_json()
        job_desc = {
            'id': len(job_descriptions) + 1,
            'title': data.get('title', ''),
            'company': data.get('company', ''),
            'location': data.get('location', ''),
            'description': data.get('description', ''),
            'created_at': datetime.now().isoformat()
        }
        job_descriptions.append(job_desc)
        return jsonify(job_desc), 201
    else:
        return jsonify(job_descriptions)

@app.route('/api/job-descriptions/<int:job_id>', methods=['GET', 'PUT', 'DELETE'])
def api_job_description(job_id):
    job = next((j for j in job_descriptions if j['id'] == job_id), None)
    if not job:
        return jsonify({'error': 'Job description not found'}), 404
    
    if request.method == 'GET':
        return jsonify(job)
    elif request.method == 'PUT':
        data = request.get_json()
        job.update(data)
        return jsonify(job)
    elif request.method == 'DELETE':
        job_descriptions.remove(job)
        return '', 204

@app.route('/api/match', methods=['POST'])
def api_match():
    data = request.get_json()
    job_description = data.get('job_description', '')
    
    # Simple mock matching logic
    mock_candidates = [
        {
            'name': 'John Smith',
            'position': 'Software Engineer',
            'company': 'Tech Corp',
            'location': 'San Francisco, CA',
            'score': 85,
            'skills': ['Python', 'React', 'AWS']
        },
        {
            'name': 'Jane Doe',
            'position': 'Senior Developer',
            'company': 'Startup Inc',
            'location': 'New York, NY',
            'score': 78,
            'skills': ['JavaScript', 'Node.js', 'MongoDB']
        }
    ]
    
    return jsonify({
        'candidates': mock_candidates,
        'job_description': job_description,
        'total_candidates': len(mock_candidates)
    })

@app.route('/api/referrals')
def api_referrals():
    # Mock referrals data
    mock_referrals = [
        {
            'job_title': 'Software Engineer',
            'candidates': [
                {'name': 'Alice Johnson', 'score': 92, 'location': 'Remote'},
                {'name': 'Bob Wilson', 'score': 88, 'location': 'London, UK'}
            ]
        }
    ]
    return jsonify(mock_referrals)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
