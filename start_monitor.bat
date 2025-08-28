@echo off
echo Starting Automated Deployment Monitor...
echo This will check for build failures every 5 minutes and auto-fix them.
echo Press Ctrl+C to stop the monitor.
echo.

python deployment_monitor.py

pause
