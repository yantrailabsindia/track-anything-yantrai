"""
ProMe & CCTV Agent Auto-Build Watcher
Monitors Python files and rebuilds executables when changes are detected
"""
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import os
import time
import sys

class AgentChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_build = {}
        self.build_delay = 2  # Wait 2 seconds after last change before building
        self.is_building = False

    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            # Determine which agent needs rebuilding
            norm_path = os.path.normpath(event.src_path)
            
            target = None
            if 'desktop' in norm_path:
                target = 'ProMe'
            elif 'cctv_agent' in norm_path:
                target = 'CCTVAgent'
            
            if not target:
                return

            current_time = time.time()
            last = self.last_build.get(target, 0)
            
            if (current_time - last > self.build_delay) and not self.is_building:
                self.last_build[target] = current_time
                print(f'\n[CHANGE DETECTED] {target} component: {os.path.basename(event.src_path)}')
                self.rebuild_exe(target)

    def rebuild_exe(self, target):
        self.is_building = True
        print(f'[REBUILDING] {target}.exe...')
        try:
            if target == 'ProMe':
                cmd = ['pyinstaller', 'ProMe.spec', '--noconfirm']
                cwd = os.getcwd()
            else:
                # CCTVAgent build is inside its directory
                cmd = ['pyinstaller', 'build.spec', '--noconfirm']
                cwd = os.path.join(os.getcwd(), 'cctv_agent')

            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                print(f'[SUCCESS] {target}.exe rebuilt!')
                # For CCTVAgent, we might need to copy it to root dist if spec doesn't
                if target == 'CCTVAgent':
                    src = os.path.join(cwd, 'dist', 'CCTVAgent.exe')
                    dest = os.path.join(os.getcwd(), 'dist', 'CCTVAgent.exe')
                    if os.path.exists(src):
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        import shutil
                        shutil.copy2(src, dest)
                        print(f'[COPIED] CCTVAgent.exe -> dist/CCTVAgent.exe')
            else:
                print(f'[ERROR] {target} build failed:')
                if result.stderr:
                    print(result.stderr[-500:])
        except subprocess.TimeoutExpired:
            print(f'[ERROR] {target} build timed out')
        except Exception as e:
            print(f'[ERROR] {target} build error: {e}')
        finally:
            self.is_building = False

# Change to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Create observer
observer = Observer()
handler = AgentChangeHandler()
observer.schedule(handler, path='desktop', recursive=True)
observer.schedule(handler, path='cctv_agent', recursive=True)
observer.start()

print('=' * 50)
print('  ProMe & CCTV Auto-Build Watcher')
print('=' * 50)
print()
print('Watching for changes in:')
print('  - desktop\\**\\*.py    -> Rebuilds ProMe.exe')
print('  - cctv_agent\\**\\*.py -> Rebuilds CCTVAgent.exe')
print()
print('PyInstaller will rebuild automatically when files change.')
print('Press Ctrl+C to stop.')
print()
print('[READY] Watching for Python file changes...')

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print('\n[STOPPED] Stopping watcher...')
    observer.stop()
    observer.join()
    print('[STOPPED] Watcher stopped.')
    sys.exit(0)
