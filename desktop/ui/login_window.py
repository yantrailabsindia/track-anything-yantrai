"""
Login window for the desktop agent — asks for credentials on first run
"""
import sys
import tkinter as tk
from tkinter import simpledialog, messagebox
from desktop.auth import login, is_authenticated

class LoginWindow:
    def __init__(self):
        try:
            self.root = tk.Tk()
            self.root.title("ProMe Agent - Login")
            self.root.geometry("400x250")
            self.root.resizable(False, False)

            # Make window stay on top
            self.root.attributes('-topmost', True)

            # Center window
            self.root.update_idletasks()
            x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
            y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
            self.root.geometry(f"+{x}+{y}")

            self.result = (None, None, None)
            self.setup_ui()
            print("Login window created successfully")
        except Exception as e:
            print(f"Error creating login window: {e}")
            self.root = None

    def setup_ui(self):
        # Title
        title = tk.Label(self.root, text="ProMe Agent Login", font=("Arial", 14, "bold"))
        title.pack(pady=10)

        # Username
        tk.Label(self.root, text="Username:").pack(anchor=tk.W, padx=20, pady=(10, 0))
        self.username_entry = tk.Entry(self.root, width=30)
        self.username_entry.pack(padx=20, pady=5)
        self.username_entry.focus()

        # Password
        tk.Label(self.root, text="Password:").pack(anchor=tk.W, padx=20, pady=(10, 0))
        self.password_entry = tk.Entry(self.root, width=30, show="•")
        self.password_entry.pack(padx=20, pady=5)

        # Server URL (Advanced)
        tk.Label(self.root, text="Server URL:", font=("Arial", 8)).pack(anchor=tk.W, padx=20, pady=(10, 0))
        from desktop.config import API_URL
        from desktop.auth import load_auth_token
        _, _, _, saved_server = load_auth_token()
        default_server = saved_server or API_URL
        
        self.server_entry = tk.Entry(self.root, width=30, font=("Arial", 9))
        self.server_entry.insert(0, default_server)
        self.server_entry.pack(padx=20, pady=2)

        # Buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Login", width=10, command=self.on_login).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Exit", width=10, command=self.on_exit).pack(side=tk.LEFT, padx=5)

        # Bind Enter key
        self.password_entry.bind('<Return>', lambda e: self.on_login())

        # Info text
        info = tk.Label(self.root, text="Use the same credentials as ProMe webapp",
                       font=("Arial", 8), fg="gray")
        info.pack(pady=2)

    def on_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        server_url = self.server_entry.get().strip()

        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password")
            return

        print(f"Logging in as: {username} to {server_url}")
        # Disable buttons during login
        self.root.config(cursor="wait")
        self.root.update()

        try:
            token, user_id, username = login(username, password, server_url=server_url)
            self.root.config(cursor="")

            if token:
                print(f"Login successful for {username}")
                messagebox.showinfo("Success", f"Logged in as {username}\n\nAgent will now start tracking.")
                self.result = (token, user_id, username)
                self.root.destroy()
            else:
                messagebox.showerror("Login Failed", 
                    "Invalid username or password.\n\n"
                    "If credentials are correct, please check the Server URL.")
                self.password_entry.delete(0, tk.END)
                self.password_entry.focus()
        except Exception as e:
            self.root.config(cursor="")
            messagebox.showerror("Connection Error", 
                f"Could not connect to server:\n{server_url}\n\nError: {e}")

    def on_exit(self):
        print("User cancelled login")
        self.root.destroy()

    def show(self):
        """Show the login window and return (token, user_id, username)"""
        if self.root:
            self.root.mainloop()
        return self.result

def require_login():
    """Show login dialog if not authenticated. Returns (token, user_id, username)"""
    print("Checking authentication status...")
    if is_authenticated():
        print("User already authenticated, loading saved credentials")
        from desktop.auth import load_auth_token
        token, user_id, username, server_url = load_auth_token()
        print(f"Loaded credentials for: {username} on {server_url}")
        return token, user_id, username

    print("No saved authentication found, showing login dialog")
    window = LoginWindow()
    result = window.show()
    print(f"Login result: {result[2] if result[0] else 'Failed'}")
    return result
