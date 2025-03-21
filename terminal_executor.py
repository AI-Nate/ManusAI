"""
Terminal Executor module for ManusAI
Executes terminal commands and captures their output
"""

import os
import subprocess
import platform
import shlex
from rich.console import Console

console = Console()

class TerminalExecutor:
    """
    Executes terminal commands and captures their output
    """
    
    def __init__(self):
        """Initialize the terminal executor"""
        self.is_windows = platform.system() == "Windows"
        self.current_dir = os.getcwd()
        
        # Set of potentially dangerous commands that require confirmation
        self.dangerous_commands = {
            'rm', 'rmdir', 'del', 'format', 'shutdown', 'reboot',
            'mkfs', 'dd', ':(){:|:&};:', '> /dev/sda', 'chmod -R 777 /'
        }
    
    def execute(self, command):
        """
        Execute a terminal command and return its output
        
        Args:
            command (str): The command to execute
            
        Returns:
            tuple: (success, output) where success is a boolean and output is a string
        """
        # Check if command is potentially dangerous
        if self._is_dangerous(command):
            confirm = console.input(f"[bold red]Warning:[/bold red] The command '{command}' may be destructive. Proceed? (y/n): ")
            if confirm.lower() != 'y':
                return False, "Command execution cancelled for safety reasons."
        
        # Handle cd commands specially
        if command.strip().startswith('cd '):
            return self._handle_cd_command(command)
        
        try:
            # Prepare the command for execution
            if self.is_windows:
                # On Windows, use shell=True for commands that use shell features
                if any(char in command for char in '|&><'):
                    process = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=self.current_dir
                    )
                else:
                    # For simple commands, avoid shell=True for security
                    args = shlex.split(command)
                    process = subprocess.Popen(
                        args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=self.current_dir
                    )
            else:
                # On Unix-like systems, use a list of arguments
                process = subprocess.Popen(
                    ['/bin/sh', '-c', command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=self.current_dir
                )
            
            # Capture output with timeout
            stdout, stderr = process.communicate(timeout=60)
            
            # Check if the command was successful
            if process.returncode == 0:
                return True, stdout
            else:
                return False, f"Error (code {process.returncode}):\n{stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Command timed out after 60 seconds."
        except Exception as e:
            return False, f"Failed to execute command: {str(e)}"
    
    def _handle_cd_command(self, command):
        """
        Handle cd commands by changing the current directory
        
        Args:
            command (str): The cd command
            
        Returns:
            tuple: (success, output) where success is a boolean and output is a string
        """
        try:
            # Extract the directory path from the command
            parts = command.split(' ', 1)
            if len(parts) < 2:
                return False, "No directory specified for cd command."
                
            directory = parts[1].strip()
            
            # Handle special case for quoted paths
            if (directory.startswith('"') and directory.endswith('"')) or \
               (directory.startswith("'") and directory.endswith("'")):
                directory = directory[1:-1]
            
            # Handle relative paths
            if not os.path.isabs(directory):
                directory = os.path.join(self.current_dir, directory)
            
            # Normalize the path
            directory = os.path.normpath(directory)
            
            # Check if the directory exists
            if not os.path.exists(directory):
                return False, f"Directory not found: {directory}"
            
            if not os.path.isdir(directory):
                return False, f"Not a directory: {directory}"
            
            # Change the current directory
            self.current_dir = directory
            os.chdir(directory)
            
            return True, f"Changed directory to {directory}"
            
        except Exception as e:
            return False, f"Failed to change directory: {str(e)}"
    
    def _is_dangerous(self, command):
        """
        Check if a command is potentially dangerous
        
        Args:
            command (str): The command to check
            
        Returns:
            bool: True if the command is potentially dangerous, False otherwise
        """
        command_lower = command.lower()
        
        # Check for dangerous command prefixes
        for dangerous_cmd in self.dangerous_commands:
            if command_lower.startswith(dangerous_cmd + ' ') or command_lower == dangerous_cmd:
                return True
        
        # Check for rm -rf or similar
        if 'rm -rf' in command_lower or 'rm -r -f' in command_lower:
            return True
            
        # Check for commands with sudo that are also in the dangerous list
        if command_lower.startswith('sudo '):
            sudo_command = command_lower[5:].strip()
            for dangerous_cmd in self.dangerous_commands:
                if sudo_command.startswith(dangerous_cmd + ' ') or sudo_command == dangerous_cmd:
                    return True
        
        return False 