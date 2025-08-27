#!/usr/bin/env python3
"""
Deployment helper script for Referral MVP
"""

import os
import sys
import subprocess
import json

def check_requirements():
    """Check if all required files exist."""
    required_files = [
        'app.py',
        'requirements.txt',
        'Procfile',
        'runtime.txt',
        'enhanced_tagged_contacts.csv',
        'email_service.py',
        'unified_matcher.py',
        'referral_api.py',
        'location_hierarchy.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ All required files found")
    return True

def check_environment():
    """Check environment variables."""
    required_env_vars = [
        'SENDGRID_API_KEY',
        'FROM_EMAIL',
        'FROM_NAME'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️  Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 These can be set later in your deployment platform")
    else:
        print("✅ All environment variables set")
    
    return True

def check_dependencies():
    """Check if all Python dependencies are available."""
    try:
        import flask
        import pandas
        import rapidfuzz
        import requests
        import sendgrid
        import gunicorn
        print("✅ All Python dependencies available")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False

def create_gitignore():
    """Create .gitignore file if it doesn't exist."""
    gitignore_content = """
# Environment variables
.env
.env.local
.env.production

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Temporary files
*.tmp
*.temp
"""
    
    if not os.path.exists('.gitignore'):
        with open('.gitignore', 'w') as f:
            f.write(gitignore_content.strip())
        print("✅ Created .gitignore file")
    else:
        print("✅ .gitignore file exists")

def main():
    """Main deployment check function."""
    print("🚀 Referral MVP Deployment Check")
    print("=" * 40)
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Deployment check failed - missing files")
        sys.exit(1)
    
    # Check environment
    check_environment()
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Deployment check failed - missing dependencies")
        sys.exit(1)
    
    # Create gitignore
    create_gitignore()
    
    print("\n" + "=" * 40)
    print("✅ Deployment check passed!")
    print("\n📋 Next steps:")
    print("1. Set up your deployment platform (Heroku/Railway/Render)")
    print("2. Configure environment variables")
    print("3. Deploy your application")
    print("\n📖 See DEPLOYMENT_GUIDE.md for detailed instructions")

if __name__ == "__main__":
    main()

