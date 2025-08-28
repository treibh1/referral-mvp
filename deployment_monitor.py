#!/usr/bin/env python3
"""
Automated Deployment Monitor
Checks Render deployment status every 5 minutes and automatically fixes build failures.
"""

import os
import time
import requests
import json
import subprocess
import sys
from datetime import datetime, timedelta

# Configuration
RENDER_API_KEY = os.environ.get('RENDER_API_KEY', 'rnd_xTZfFXY3Qa1f0VDqE4pAf6LhQ77X')
SERVICE_ID = 'srv-d2nb6bm3jp1c73ceqitg'
CHECK_INTERVAL = 300  # 5 minutes in seconds
MAX_RETRIES = 3

class DeploymentMonitor:
    def __init__(self):
        self.api_key = RENDER_API_KEY
        self.service_id = SERVICE_ID
        self.base_url = "https://api.render.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.last_check = None
        self.failure_count = 0
        
    def log(self, message):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def get_latest_deploy(self):
        """Get the latest deployment status"""
        try:
            url = f"{self.base_url}/services/{self.service_id}/deploys"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            deploys = response.json()
            if deploys:
                return deploys[0]  # Latest deployment
            return None
        except Exception as e:
            self.log(f"Error getting deployment status: {e}")
            return None
    
    def get_deploy_logs(self, deploy_id):
        """Get deployment logs to identify the issue"""
        try:
            url = f"{self.base_url}/services/{self.service_id}/deploys/{deploy_id}/log"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.log(f"Error getting deployment logs: {e}")
            return None
    
    def analyze_failure(self, logs):
        """Analyze logs to determine the cause of failure"""
        if not logs:
            return "unknown"
            
        logs_lower = logs.lower()
        
        # Common failure patterns
        if "no matching distribution found" in logs_lower:
            return "dependency_version"
        elif "import error" in logs_lower or "module not found" in logs_lower:
            return "missing_module"
        elif "syntax error" in logs_lower:
            return "syntax_error"
        elif "timeout" in logs_lower:
            return "timeout"
        elif "memory" in logs_lower and "error" in logs_lower:
            return "memory_error"
        else:
            return "unknown"
    
    def fix_dependency_version(self):
        """Fix dependency version issues"""
        self.log("Attempting to fix dependency version issue...")
        
        try:
            # Read current requirements.txt
            with open('requirements.txt', 'r') as f:
                content = f.read()
            
            # Common fixes for dependency issues
            fixes = {
                'rapidfuzz==3.3.2': 'rapidfuzz==3.14.0',
                'pandas==2.0.3': 'pandas==2.0.3',
                'beautifulsoup4==4.12.2': 'beautifulsoup4==4.12.2',
                'requests==2.31.0': 'requests==2.31.0'
            }
            
            # Apply fixes
            for old_version, new_version in fixes.items():
                if old_version in content:
                    content = content.replace(old_version, new_version)
                    self.log(f"Updated {old_version} to {new_version}")
            
            # Write back
            with open('requirements.txt', 'w') as f:
                f.write(content)
            
            return True
        except Exception as e:
            self.log(f"Error fixing dependencies: {e}")
            return False
    
    def fix_missing_module(self):
        """Fix missing module issues"""
        self.log("Attempting to fix missing module issue...")
        
        try:
            # Add commonly missing modules
            with open('requirements.txt', 'r') as f:
                content = f.read()
            
            missing_modules = [
                'unidecode==1.3.6',
                'python-dotenv==1.0.0'
            ]
            
            for module in missing_modules:
                if module not in content:
                    content += f"\n{module}"
                    self.log(f"Added missing module: {module}")
            
            with open('requirements.txt', 'w') as f:
                f.write(content)
            
            return True
        except Exception as e:
            self.log(f"Error fixing missing modules: {e}")
            return False
    
    def commit_and_push_fix(self, fix_type):
        """Commit and push the fix"""
        try:
            # Git operations
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', f'AUTO-FIX: {fix_type} issue'], check=True)
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)
            
            self.log(f"Successfully pushed fix for {fix_type}")
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"Error pushing fix: {e}")
            return False
    
    def should_check(self):
        """Determine if we should check deployment status"""
        if self.last_check is None:
            return True
        
        time_since_check = datetime.now() - self.last_check
        return time_since_check.total_seconds() >= CHECK_INTERVAL
    
    def run(self):
        """Main monitoring loop"""
        self.log("🚀 Starting automated deployment monitor...")
        self.log(f"Monitoring service: {self.service_id}")
        self.log(f"Check interval: {CHECK_INTERVAL} seconds")
        
        while True:
            try:
                if not self.should_check():
                    time.sleep(60)  # Sleep for 1 minute before checking again
                    continue
                
                self.last_check = datetime.now()
                self.log("🔍 Checking deployment status...")
                
                deploy = self.get_latest_deploy()
                if not deploy:
                    self.log("⚠️  Could not get deployment status")
                    continue
                
                status = deploy.get('status')
                deploy_id = deploy.get('id')
                
                self.log(f"📊 Deployment status: {status}")
                
                if status == 'build_failed':
                    self.log("❌ Build failed detected! Analyzing...")
                    
                    # Get logs to analyze the failure
                    logs = self.get_deploy_logs(deploy_id)
                    failure_type = self.analyze_failure(logs)
                    
                    self.log(f"🔍 Failure type: {failure_type}")
                    
                    # Attempt to fix based on failure type
                    fix_success = False
                    
                    if failure_type == 'dependency_version':
                        if self.fix_dependency_version():
                            fix_success = self.commit_and_push_fix('dependency_version')
                    elif failure_type == 'missing_module':
                        if self.fix_missing_module():
                            fix_success = self.commit_and_push_fix('missing_module')
                    else:
                        self.log(f"⚠️  Unknown failure type: {failure_type}")
                    
                    if fix_success:
                        self.log("✅ Fix applied and pushed! New deployment should start...")
                        self.failure_count = 0
                    else:
                        self.failure_count += 1
                        self.log(f"⚠️  Failed to apply fix. Attempt {self.failure_count}/{MAX_RETRIES}")
                        
                        if self.failure_count >= MAX_RETRIES:
                            self.log("🚨 Maximum retry attempts reached. Manual intervention needed.")
                            break
                
                elif status == 'live':
                    self.log("✅ Deployment successful!")
                    self.failure_count = 0
                
                elif status == 'build_in_progress':
                    self.log("⏳ Build in progress...")
                
                else:
                    self.log(f"ℹ️  Status: {status}")
                
            except KeyboardInterrupt:
                self.log("🛑 Monitoring stopped by user")
                break
            except Exception as e:
                self.log(f"❌ Unexpected error: {e}")
                time.sleep(60)
            
            # Wait before next check
            time.sleep(60)

if __name__ == "__main__":
    monitor = DeploymentMonitor()
    monitor.run()
