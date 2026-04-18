"""
Utility to install the CCTV Agent to Windows Startup.
Creates a shortcut in the user's Startup folder.
"""

import os
import sys
import subprocess
from pathlib import Path

def install_to_startup():
    project_root = Path(__file__).resolve().parent.parent
    bat_file = project_root / "run_cctv_service.bat"
    
    if not bat_file.exists():
        print(f"Error: {bat_file} not found.")
        return False

    startup_folder = Path(os.getenv("APPDATA")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    shortcut_path = startup_folder / "CCTVAgent.lnk"
    
    # PowerShell command to create shortcut
    # We use a VBS-style shortcut to run it minimized or hidden if possible, 
    # but for now, a standard shortcut to the .bat is safest.
    powershell_cmd = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
    $Shortcut.TargetPath = "{bat_file}"
    $Shortcut.WorkingDirectory = "{project_root}"
    $Shortcut.IconLocation = "powershell.exe"
    $Shortcut.Save()
    """
    
    try:
        subprocess.run(["powershell", "-Command", powershell_cmd], check=True)
        print(f"Successfully installed shortcut to: {shortcut_path}")
        return True
    except Exception as e:
        print(f"Failed to create shortcut: {e}")
        return False

if __name__ == "__main__":
    install_to_startup()
