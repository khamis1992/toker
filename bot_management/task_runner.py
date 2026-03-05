"""
Background task runner for starting bot sessions.
This module handles starting bot processes in the background.
"""
import subprocess
import sys
import os
from pathlib import Path
from django.conf import settings

# Store running processes
running_processes = {}


def start_bot_session(session_id: str, config_id: int = None):
    """
    Start a bot session as a background process.
    
    Args:
        session_id: The session ID to use
        config_id: Optional configuration ID
    
    Returns:
        bool: True if process started successfully, False otherwise
    """
    # Get the project root directory
    project_root = Path(settings.BASE_DIR)
    
    # Build the command to run the bot
    cmd = [
        sys.executable,  # Python executable
        str(project_root / 'manage.py'),
        'run_tiktok_bot',
        '--session-id', session_id,
    ]
    
    if config_id:
        cmd.extend(['--config-id', str(config_id)])
    
    try:
        # Start the process in the background
        # Use DETACHED_PROCESS on Windows to truly detach
        if sys.platform == 'win32':
            process = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            process = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        
        # Store the process reference
        running_processes[session_id] = process
        
        return True
        
    except Exception as e:
        print(f"Failed to start bot session: {e}")
        return False


def stop_bot_session(session_id: str):
    """
    Stop a running bot session.
    
    Args:
        session_id: The session ID to stop
    
    Returns:
        bool: True if stopped successfully, False otherwise
    """
    process = running_processes.get(session_id)
    
    if process:
        try:
            if sys.platform == 'win32':
                # On Windows, send CTRL_BREAK_EVENT
                process.send_signal(subprocess.signal.CTRL_BREAK_EVENT)
            else:
                # On Unix, send SIGTERM
                process.terminate()
            
            # Wait for process to finish
            process.wait(timeout=5)
            
            # Remove from running processes
            del running_processes[session_id]
            return True
            
        except subprocess.TimeoutExpired:
            # Force kill if it doesn't terminate
            process.kill()
            del running_processes[session_id]
            return True
        except Exception as e:
            print(f"Failed to stop bot session: {e}")
            return False
    
    return False


def is_session_running(session_id: str) -> bool:
    """
    Check if a bot session is currently running.
    
    Args:
        session_id: The session ID to check
    
    Returns:
        bool: True if running, False otherwise
    """
    process = running_processes.get(session_id)
    
    if process:
        # Check if process is still alive
        return process.poll() is None
    
    return False


def get_running_sessions():
    """
    Get a list of all running session IDs.
    
    Returns:
        list: List of session IDs that are currently running
    """
    running = []
    
    for session_id, process in list(running_processes.items()):
        if process.poll() is None:
            running.append(session_id)
        else:
            # Clean up finished processes
            del running_processes[session_id]
    
    return running
