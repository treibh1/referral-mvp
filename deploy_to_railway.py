#!/usr/bin/env python3
"""
Deploy to Railway using the API key
"""
import requests
import json
import os
from datetime import datetime

# Railway API key
RAILWAY_API_KEY = "23dcb296-681f-47ed-a9b8-76a7157891fd"

# Railway API endpoints
RAILWAY_API_BASE = "https://backboard.railway.app/graphql/v2"

def deploy_to_railway():
    """Deploy the app to Railway"""
    
    headers = {
        "Authorization": f"Bearer {RAILWAY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    print("🚀 Starting Railway deployment...")
    print(f"⏰ Time: {datetime.now()}")
    print()
    
    try:
        # First, let's get the user's projects
        print("🔍 Getting Railway projects...")
        
        # Create a new project
        create_project_query = """
        mutation CreateProject($name: String!) {
            projectCreate(input: { name: $name }) {
                project {
                    id
                    name
                }
            }
        }
        """
        
        create_project_vars = {
            "name": "referral-mvp-system"
        }
        
        response = requests.post(
            RAILWAY_API_BASE,
            headers=headers,
            json={
                "query": create_project_query,
                "variables": create_project_vars
            },
            timeout=30
        )
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📊 Response: {json.dumps(result, indent=2)}")
            
            if "data" in result and result["data"] and "projectCreate" in result["data"]:
                project_id = result["data"]["projectCreate"]["project"]["id"]
                print(f"✅ Project created successfully!")
                print(f"   Project ID: {project_id}")
                print(f"   Project Name: referral-mvp-system")
                
                # Now let's create a service
                print(f"\n🔧 Creating service...")
                
                create_service_query = """
                mutation CreateService($projectId: String!, $name: String!) {
                    serviceCreate(input: { projectId: $projectId, name: $name }) {
                        service {
                            id
                            name
                        }
                    }
                }
                """
                
                create_service_vars = {
                    "projectId": project_id,
                    "name": "referral-web-app"
                }
                
                service_response = requests.post(
                    RAILWAY_API_BASE,
                    headers=headers,
                    json={
                        "query": create_service_query,
                        "variables": create_service_vars
                    },
                    timeout=30
                )
                
                print(f"📡 Service response status: {service_response.status_code}")
                
                if service_response.status_code == 200:
                    service_result = service_response.json()
                    print(f"📊 Service response: {json.dumps(service_result, indent=2)}")
                    
                    if "data" in service_result and service_result["data"] and "serviceCreate" in service_result["data"]:
                        service_id = service_result["data"]["serviceCreate"]["service"]["id"]
                        print(f"✅ Service created successfully!")
                        print(f"   Service ID: {service_id}")
                        print(f"   Service Name: referral-web-app")
                        
                        print(f"\n🎯 Next steps:")
                        print(f"   1. Connect your GitHub repo to Railway")
                        print(f"   2. Railway will auto-deploy from your main branch")
                        print(f"   3. Your app will be available at: https://referral-web-app-production.up.railway.app")
                        
                    else:
                        print("❌ Failed to create service")
                        print(f"Response: {service_result}")
                else:
                    print(f"❌ Service creation failed: {service_response.status_code}")
                    print(f"Response: {service_response.text}")
            else:
                print("❌ Failed to create project")
                print(f"Response: {result}")
        else:
            print(f"❌ Project creation failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_to_railway()
