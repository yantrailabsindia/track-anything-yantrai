"""
Logout dialog — password-protected logout confirmation
Uses native Windows MessageBox API to avoid event loop conflicts with pystray
"""
import ctypes
import threading
from desktop.auth import verify_password

def show_message_box(title, message, msg_type=0):
    """
    Show a native Windows message box.
    msg_type: 0=OK, 1=OK/Cancel, 4=Yes/No, 5=Yes/No/Cancel
    Returns: button pressed (1=OK, 2=Cancel, 6=Yes, 7=No)
    """
    return ctypes.windll.user32.MessageBoxW(0, message, title, msg_type)

def show_input_dialog(title, prompt):
    """
    Show a password input dialog using a native Windows approach.
    Returns the input text or None if cancelled.
    """
    import tkinter as tk
    from tkinter import simpledialog

    # Create a minimal root window just for the dialog
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.update_idletasks()
    root.withdraw()

    try:
        password = simpledialog.askstring(title, prompt, show="•")
        return password
    finally:
        try:
            root.destroy()
        except:
            pass

def require_logout_confirmation(username):
    """
    Show logout confirmation using native Windows MessageBox.
    Returns True if user confirms logout, False otherwise.

    This uses pure Windows API dialogs which don't conflict with pystray.
    """
    print(f"Showing logout confirmation for {username}")

    # Step 1: Confirm logout action (using native Windows MessageBox)
    # MB_YESNO = 4, MB_ICONQUESTION = 32, MB_TOPMOST = 0x40000
    msg_type = 4 | 32 | 0x40000
    result = show_message_box(
        "Confirm Logout",
        f"Are you sure you want to log out?\n\nUser: {username}",
        msg_type
    )

    # 6 = Yes, 7 = No
    if result != 6:
        print("Logout cancelled by user")
        return False

    # Step 2: Password verification loop
    max_attempts = 3
    attempt = 0

    while attempt < max_attempts:
        attempt += 1
        print(f"Password verification attempt {attempt}...")

        password = show_input_dialog(
            "Verify Password",
            "Enter your password to confirm logout:"
        )

        if password is None:
            # User clicked Cancel
            print("Password entry cancelled by user")
            return False

        if not password:
            show_message_box(
                "Error",
                "Please enter your password",
                0x10  # MB_ICONHAND (error icon)
            )
            continue

        # Verify password with backend
        print(f"Verifying password for logout...")
        if verify_password(username, password):
            print("Password verified, confirming logout")
            show_message_box(
                "Success",
                "Logout confirmed.\nAgent will restart on login.",
                0x40  # MB_ICONINFORMATION
            )
            return True
        else:
            remaining = max_attempts - attempt
            if remaining > 0:
                show_message_box(
                    "Failed",
                    f"Incorrect password.\n\nAttempts remaining: {remaining}",
                    0x30  # MB_ICONWARNING
                )
            else:
                show_message_box(
                    "Failed",
                    "Incorrect password. Maximum attempts exceeded.\n\nLogout cancelled.",
                    0x10  # MB_ICONHAND
                )
                return False

    return False
