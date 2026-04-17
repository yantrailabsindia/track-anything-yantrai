# Final Deployment Guide — ProMe GCE

This guide explains how to deploy the entire ProMe stack on your `yantrai-mohit` instance.

## 1. Prerequisites (Run these on the VM)
SSH into your instance and install Docker:
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
# Log out and log back in
```

## 2. Code & Files Transfer
Transfer the current project folder to the VM (e.g., to `/opt/prome`).
Ensure the following are present:
- `dist/ProMe.exe`
- `dist/CCTVAgent.exe`
- `data/prome.db` (The 63MB database)
- `.env` (Create this from `.env.production.example`)
- `credentials/service-account.json` (Your GCS key)

## 3. Launch
Navigate to the directory on the VM and run:
```bash
docker compose up -d --build
```

## 4. Verification
- Access the dashboard at: `http://<YOUR-VM-IP>`
- Verify API at: `http://<YOUR-VM-IP>/api/`
- Download agents via the dashboard "Download" buttons.

## 5. Security Note
- Port 80 and 8765 must be open in your GCP console firewall rules for this to work.
- `SECRET_KEY` in `.env` should be unique.
