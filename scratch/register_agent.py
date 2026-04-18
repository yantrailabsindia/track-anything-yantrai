import httpx
import json
from pathlib import Path

def register_agent():
    # Org ID from the user info in config.json
    org_id = "724bd06a-d244-46af-a716-60def5d1c022"
    agent_name = "site-01"
    
    # Register agent
    try:
        response = httpx.post(
            "http://localhost:8765/api/cctv/agent/register",
            json={
                "org_id": org_id,
                "agent_name": agent_name
            }
        )
        if response.status_code == 200:
            data = response.json()
            api_key = data["api_key"]
            agent_id = data["agent_id"]
            print(f"Agent registered! API Key: {api_key}, Agent ID: {agent_id}")
            
            # Update config.json
            config_path = Path.home() / "CCTVAgent" / "config.json"
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)
                
                config["cloud"]["api_key"] = api_key
                config["cloud"]["agent_id"] = agent_id
                
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=4)
                print(f"Updated config.json at {config_path}")
                return True
            else:
                print(f"Config file not found at {config_path}")
        else:
            print(f"Registration failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    return False

if __name__ == "__main__":
    register_agent()
