@echo off
echo Syncing built agent artifacts to VM...

:: Set VM Details
set VM_IP=34.63.62.95
set SSH_KEY=C:\Users\namem\.ssh\google_compute_engine
set REMOTE_PATH=/home/namem/prome_app/dist/

:: Ensure dist exists on VM
ssh -i %SSH_KEY% -o StrictHostKeyChecking=no namem@%VM_IP% "mkdir -p %REMOTE_PATH%"

:: Copy built agents
scp -i %SSH_KEY% -o StrictHostKeyChecking=no dist/ProMe.exe namem@%VM_IP%:%REMOTE_PATH%
scp -i %SSH_KEY% -o StrictHostKeyChecking=no dist/CCTVAgent.exe namem@%VM_IP%:%REMOTE_PATH%

echo.
echo Agent sync complete! You can now run the deployment script on the VM.
pause
