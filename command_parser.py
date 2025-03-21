"""
Command Parser module for ManusAI
Parses AI responses into executable commands
"""

import re
from rich.console import Console

console = Console()

class CommandParser:
    """
    Parser that extracts commands from AI responses
    """
    
    def __init__(self):
        """Initialize the command parser"""
        # Regex patterns for command extraction
        self.command_block_pattern = r"```(?:bash|shell|sh)?\s*([\s\S]*?)```"
        self.command_line_pattern = r"`(.*?)`"
        self.numbered_command_pattern = r"(\d+)\.\s*(?:`(.*?)`|(?:Execute |Run |Type )(?:the command )?[`\"](.*?)[`\"])"
    
    def parse_commands(self, ai_response):
        """
        Parse commands from an AI response
        
        Args:
            ai_response (dict): The AI response containing the command plan
            
        Returns:
            list: List of command dictionaries with 'command' and 'description' keys
        """
        if not ai_response or not isinstance(ai_response, dict) or 'content' not in ai_response:
            console.print("[bold red]Error:[/bold red] Invalid AI response format.")
            return []
            
        content = ai_response['content']
        commands = []
        
        # Try to extract commands from code blocks first
        code_blocks = re.findall(self.command_block_pattern, content)
        if code_blocks:
            for block in code_blocks:
                # Split the block into lines and filter out comments and empty lines
                lines = [line.strip() for line in block.split('\n') if line.strip() and not line.strip().startswith('#')]
                
                for line in lines:
                    commands.append({
                        'command': line,
                        'description': self._extract_description_for_command(line, content)
                    })
        
        # If no commands found in code blocks, try to find inline commands
        if not commands:
            # Try to find numbered commands with descriptions
            numbered_commands = re.findall(self.numbered_command_pattern, content)
            if numbered_commands:
                for match in numbered_commands:
                    number = match[0]
                    command = match[1] if match[1] else match[2]
                    if command:
                        # Find the description by looking for text after the command
                        description = self._extract_description_for_command(command, content)
                        commands.append({
                            'command': command,
                            'description': description
                        })
            
            # If still no commands, try to find any inline code
            if not commands:
                inline_commands = re.findall(self.command_line_pattern, content)
                for cmd in inline_commands:
                    if self._is_valid_command(cmd):
                        commands.append({
                            'command': cmd,
                            'description': self._extract_description_for_command(cmd, content)
                        })
        
        return commands
    
    def _extract_description_for_command(self, command, content):
        """
        Extract a description for a command from the content
        
        Args:
            command (str): The command to find a description for
            content (str): The full content to search in
            
        Returns:
            str: The description or an empty string if none found
        """
        # Escape special regex characters in the command
        escaped_command = re.escape(command)
        
        # Try to find a description after the command
        after_command_pattern = f"{escaped_command}[`\"]*\\s*[-:]?\\s*(.*?)(?:\\.\\s|\\n|$)"
        after_matches = re.search(after_command_pattern, content)
        
        if after_matches and after_matches.group(1).strip():
            return after_matches.group(1).strip()
        
        # Try to find a description before the command
        before_command_pattern = r"(.*?)\s*[:-]?\s*[`\"]?" + escaped_command
        before_matches = re.search(before_command_pattern, content)
        
        if before_matches and before_matches.group(1).strip():
            # Extract the last sentence if there are multiple
            sentences = before_matches.group(1).split('.')
            return sentences[-1].strip()
        
        return ""
    
    def _is_valid_command(self, text):
        """
        Check if a text is likely to be a valid shell command
        
        Args:
            text (str): The text to check
            
        Returns:
            bool: True if the text is likely a command, False otherwise
        """
        # Common command prefixes
        common_commands = ['ls', 'cd', 'mkdir', 'touch', 'rm', 'cp', 'mv', 'cat', 'echo', 
                          'grep', 'find', 'curl', 'wget', 'git', 'python', 'pip', 'npm']
        
        # Check if the text starts with a common command
        for cmd in common_commands:
            if text.strip().startswith(cmd + ' ') or text.strip() == cmd:
                return True
        
        # Check for command patterns like 'sudo apt-get'
        if re.match(r'^(sudo|apt|apt-get|yum|brew|npm|yarn|docker|kubectl)\s', text.strip()):
            return True
            
        return False 