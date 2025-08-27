# Multi-Tenant Referral System - Deployment Guide

## 🚀 Overview

This guide will help you deploy your multi-tenant referral system to Render using the MCP (Model Context Protocol) tools. The system includes:

- **PostgreSQL Database** - Multi-tenant data storage
- **Flask Web Service** - Main application
- **Background Worker** - Location enrichment and data processing
- **Cron Jobs** - Scheduled maintenance tasks

## 📋 Prerequisites

1. **Render Account** - You already have this (treibh1@gmail.com)
2. **API Keys** - You've provided the Bright Data API key
3. **GitHub Repository** - We'll create this during deployment
4. **MCP Configuration** - Already set up in your Cursor

## 🔧 Step-by-Step Deployment

### Step 1: Create GitHub Repository

First, we need to create a GitHub repository for your code:

1. Go to [GitHub](https://github.com) and create a new repository
2. Name it `referral-mvp` or similar
3. Make it public (for Render deployment)
4. Don't initialize with README (we'll push existing code)

### Step 2: Push Code to GitHub

```bash
# Initialize git repository
git init

# Add all files
git add .

# Commit changes
git commit -m "Initial commit - Multi-tenant referral system"

# Add remote repository (replace with your GitHub URL)
git remote add origin https://github.com/your-username/referral-mvp.git

# Push to GitHub
git push -u origin main
```

### Step 3: Deploy to Render

The MCP tools will handle the deployment automatically. Here's what will be created:

#### 3.1 PostgreSQL Database
- **Name**: `referral-system-db`
- **Plan**: Free
- **Region**: Frankfurt
- **Version**: PostgreSQL 16

#### 3.2 Web Service
- **Name**: `referral-system-web`
- **Runtime**: Python
- **Plan**: Starter
- **Region**: Frankfurt
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2`

#### 3.3 Background Worker
- **Name**: `referral-system-worker`
- **Runtime**: Python
- **Plan**: Starter
- **Region**: Frankfurt
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python worker.py`

#### 3.4 Cron Jobs
- **Name**: `referral-system-cron`
- **Runtime**: Python
- **Plan**: Starter
- **Region**: Frankfurt
- **Schedule**: Daily at 2 AM
- **Command**: `python cron_jobs.py`

### Step 4: Environment Variables

The following environment variables will be set automatically:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# API Keys
BRIGHT_DATA_API_KEY=0f2277aa02ffa91c417591552ae2c56efc9b6d3aef29ea9746ea4c594f581a08
SENDGRID_API_KEY=your_sendgrid_key_here
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
STRIPE_SECRET_KEY=your_stripe_secret_key_here
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key_here

# Flask
FLASK_SECRET_KEY=your-super-secret-flask-key-change-this-in-production
```

### Step 5: Database Setup

After deployment, the database will need to be initialized:

1. **Create Tables**: The `database_schema.sql` file will be executed
2. **Migrate Data**: The `migrate_csv_to_db.py` script will move your CSV data
3. **Create Demo Organization**: A demo organization will be created for testing

## 🎯 Multi-Tenant Architecture

### Data Isolation

The system ensures strict data isolation between organizations:

- **Universal Data**: Contacts, core job roles (shared across all organizations)
- **Organization-Specific Data**: Users, employees, custom job roles, job descriptions
- **Relationship Data**: Employee contacts (who knows whom)

### Key Tables

1. **organisations** - Multi-tenant isolation
2. **users** - Organization-specific users
3. **contacts** - Universal contact database
4. **employees** - Organization employees
5. **employee_contacts** - Professional relationships
6. **core_job_roles** - Universal job roles
7. **custom_job_roles** - Organization-specific roles
8. **job_descriptions** - Organization job postings

## 🔄 Background Processes

### Location Enrichment Worker

- **Purpose**: Enriches missing contact locations using Bright Data SERP API
- **Frequency**: Every 5 minutes
- **Limit**: 10 enrichments per run (to control API costs)
- **Logging**: All activities logged to database

### Cron Jobs

- **Data Cleanup**: Removes old search history and logs
- **Statistics Update**: Updates contact statistics for organizations
- **Health Checks**: Monitors database health
- **Reports**: Generates daily system reports

## 🧪 Testing the Deployment

### 1. Health Check

Visit your web service URL and check:
- Database connectivity
- API endpoints
- Background worker status

### 2. Demo Data

The migration script creates:
- Demo organization
- Admin user (admin@demo.com)
- All your existing contacts
- Sample job roles

### 3. Test Features

1. **Job Search**: Test the main matching functionality
2. **Location Enrichment**: Verify Bright Data integration
3. **Multi-Tenant**: Test data isolation between organizations
4. **Adaptive Matching**: Test the new role-based matching

## 📊 Monitoring

### Render Dashboard

Monitor your services at: https://dashboard.render.com

- **Web Service**: Check logs and performance
- **Database**: Monitor connections and queries
- **Worker**: Check background task execution
- **Cron**: Verify scheduled job execution

### Logs

- **Application Logs**: Flask application logs
- **Worker Logs**: Background worker activities
- **Cron Logs**: Scheduled task execution
- **Database Logs**: Query performance and errors

## 🔧 Configuration

### API Keys

You'll need to add these API keys to your environment variables:

1. **SendGrid** - For email notifications
2. **Google OAuth** - For user authentication
3. **Stripe** - For payment processing

### Customization

1. **Branding**: Update organization names and domains
2. **Pricing**: Configure subscription plans
3. **Features**: Enable/disable specific features per organization
4. **Limits**: Set usage limits for free/paid plans

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection**: Check DATABASE_URL environment variable
2. **API Keys**: Verify all required API keys are set
3. **Worker Issues**: Check worker logs for background task errors
4. **Migration Errors**: Verify CSV file format and data integrity

### Support

- **Render Support**: For deployment and infrastructure issues
- **Application Logs**: For application-specific errors
- **Database Logs**: For data and query issues

## 🎉 Success!

Once deployed, your multi-tenant referral system will be:

- ✅ **Scalable**: Multi-tenant architecture supports multiple organizations
- ✅ **Secure**: Data isolation between organizations
- ✅ **Automated**: Background workers handle data enrichment
- ✅ **Monitored**: Comprehensive logging and health checks
- ✅ **Maintained**: Automated cleanup and maintenance tasks

Your system will be available at: `https://referral-system-web.onrender.com`

## 📈 Next Steps

1. **Add Real API Keys**: Replace placeholder API keys with real ones
2. **Customize Branding**: Update organization names and styling
3. **Add More Organizations**: Onboard additional clients
4. **Monitor Performance**: Track usage and optimize as needed
5. **Scale Up**: Upgrade plans as your user base grows

