#!/usr/bin/env python3
"""
Simple script to push changes to Railway deployment
"""
import subprocess
import sys

def run_command(cmd):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"Command: {cmd}")
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Exception: {e}")
        return False

def main():
    print("🚀 Pushing changes to Railway...")
    
    # Add all files
    if not run_command("git add ."):
        print("❌ Failed to add files")
        return
    
    # Commit changes
    if not run_command('git commit -m "Add contact data for Railway deployment"'):
        print("❌ Failed to commit")
        return
    
    # Push to GitHub (Railway will auto-deploy)
    if not run_command("git push origin main"):
        print("❌ Failed to push")
        return
    
    print("✅ Successfully pushed to Railway!")
    print("🌐 Your app will be available at: https://web-production-2d975.up.railway.app/")

if __name__ == "__main__":
    main()
