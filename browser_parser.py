"""
Browser Parser module for ManusAI
Parses AI responses into executable browser actions
"""

import re
import json
from rich.console import Console

console = Console()

class BrowserParser:
    """
    Parser that extracts browser actions from AI responses
    """
    
    def __init__(self):
        """Initialize the browser parser"""
        # Regex patterns for browser action extraction
        self.action_block_pattern = r"```(?:json|browser)?\s*([\s\S]*?)```"
        self.action_line_pattern = r"`(.*?)`"
        self.numbered_action_pattern = r"(\d+)\.\s*(?:Browser action|Web action|Browser command):\s*(.+?)(?:\n|$)"
    
    def parse_actions(self, ai_response):
        """
        Parse browser actions from an AI response
        
        Args:
            ai_response (dict): The AI response containing the browser actions
            
        Returns:
            list: List of action dictionaries with 'action_type' and other parameters
        """
        if not ai_response or not isinstance(ai_response, dict) or 'content' not in ai_response:
            console.print("[bold red]Error:[/bold red] Invalid AI response format.")
            return []
            
        content = ai_response['content']
        actions = []
        
        # Try to extract JSON blocks first (preferred format)
        json_blocks = re.findall(self.action_block_pattern, content)
        for block in json_blocks:
            try:
                # Try to parse as JSON
                action_data = json.loads(block)
                
                # Handle both single action and list of actions
                if isinstance(action_data, list):
                    for action in action_data:
                        if isinstance(action, dict) and 'action_type' in action:
                            actions.append(action)
                elif isinstance(action_data, dict) and 'action_type' in action_data:
                    actions.append(action_data)
            except json.JSONDecodeError:
                # If not valid JSON, try to parse as text
                actions.extend(self._parse_text_actions(block))
        
        # If no actions found in JSON blocks, try to find numbered actions
        if not actions:
            numbered_actions = re.findall(self.numbered_action_pattern, content)
            for _, action_text in numbered_actions:
                parsed_action = self._parse_action_text(action_text)
                if parsed_action:
                    actions.append(parsed_action)
        
        # Ensure each action has a unique action_type that's not duplicated in the kwargs
        cleaned_actions = []
        for action in actions:
            if 'action_type' in action:
                action_type = action['action_type']
                action_copy = action.copy()
                # Remove action_type from the copy to avoid duplication
                if 'action_type' in action_copy:
                    del action_copy['action_type']
                # Add the action with separated action_type
                cleaned_actions.append({'action_type': action_type, **action_copy})
        
        return cleaned_actions
    
    def _parse_text_actions(self, text):
        """
        Parse actions from text format
        
        Args:
            text (str): Text containing browser actions
            
        Returns:
            list: List of action dictionaries
        """
        actions = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            parsed_action = self._parse_action_text(line)
            if parsed_action:
                actions.append(parsed_action)
        
        return actions
    
    def _parse_action_text(self, text):
        """
        Parse a single action from text
        
        Args:
            text (str): Text describing a browser action
            
        Returns:
            dict: Action dictionary or None if parsing failed
        """
        # Common action patterns
        navigate_pattern = r"(?:navigate|go|open|visit)\s+(?:to|url)?\s*[\"']?(https?://[^\s\"']+)[\"']?"
        search_pattern = r"(?:search|query|look up|find)\s+(?:for)?\s*[\"']([^\"']+)[\"']"
        click_pattern = r"(?:click|press|select)\s+(?:on)?\s*[\"']([^\"']+)[\"']|(?:click|press|select)\s+(?:on)?\s*(?:the|a|an)?\s*([^\"'\n]+)"
        fill_pattern = r"(?:fill|enter|type|input)\s+[\"']([^\"']+)[\"']\s+(?:in|into|to)\s+[\"']([^\"']+)[\"']|(?:fill|enter|type|input)\s+(?:the|a|an)?\s*([^\"'\n]+)\s+(?:with|as)\s+[\"']([^\"']+)[\"']"
        select_pattern = r"(?:select|choose)\s+[\"']([^\"']+)[\"']\s+(?:from|in)\s+[\"']([^\"']+)[\"']|(?:select|choose)\s+(?:the|a|an)?\s*([^\"'\n]+)\s+(?:from|in)\s+(?:the|a|an)?\s*([^\"'\n]+)"
        scroll_pattern = r"(?:scroll)\s+(?:down|up|to)\s*(?:the|a|an)?\s*([^\"'\n]+)"
        
        # Try to match navigate action
        navigate_match = re.search(navigate_pattern, text, re.IGNORECASE)
        if navigate_match:
            url = navigate_match.group(1)
            return {
                'action_type': 'navigate',
                'url': url
            }
        
        # Try to match search action
        search_match = re.search(search_pattern, text, re.IGNORECASE)
        if search_match:
            query = search_match.group(1)
            return {
                'action_type': 'search',
                'query': query
            }
        
        # Try to match click action
        click_match = re.search(click_pattern, text, re.IGNORECASE)
        if click_match:
            element = click_match.group(1) or click_match.group(2)
            # Convert element description to a likely CSS selector
            selector = self._element_to_selector(element)
            return {
                'action_type': 'click',
                'selector': selector,
                'description': element
            }
        
        # Try to match fill action
        fill_match = re.search(fill_pattern, text, re.IGNORECASE)
        if fill_match:
            if fill_match.group(1) and fill_match.group(2):
                value = fill_match.group(1)
                field = fill_match.group(2)
            else:
                field = fill_match.group(3)
                value = fill_match.group(4)
            
            # Convert field description to a likely CSS selector
            selector = self._element_to_selector(field)
            return {
                'action_type': 'fill_form',
                'form_data': {selector: value}
            }
        
        # Try to match select action
        select_match = re.search(select_pattern, text, re.IGNORECASE)
        if select_match:
            if select_match.group(1) and select_match.group(2):
                option = select_match.group(1)
                dropdown = select_match.group(2)
            else:
                option = select_match.group(3)
                dropdown = select_match.group(4)
            
            # Convert dropdown description to a likely CSS selector
            dropdown_selector = self._element_to_selector(dropdown)
            return {
                'action_type': 'click',  # We'll use click for select actions
                'selector': f"{dropdown_selector} option[value*='{option}' i], {dropdown_selector} option:has-text('{option}')",
                'description': f"Select '{option}' from '{dropdown}'"
            }
        
        # Try to match scroll action
        scroll_match = re.search(scroll_pattern, text, re.IGNORECASE)
        if scroll_match:
            target = scroll_match.group(1) if scroll_match.group(1) else "page"
            return {
                'action_type': 'click',  # We'll use click for scroll actions (to click somewhere on the page)
                'selector': 'body',  # Default to body for scrolling
                'description': f"Scroll to {target}"
            }
        
        # If no patterns match, try to extract JSON-like format
        try:
            # Check if the text looks like JSON (starts with { and ends with })
            if text.strip().startswith('{') and text.strip().endswith('}'):
                action_data = json.loads(text)
                if 'action_type' in action_data:
                    return action_data
        except:
            pass
        
        return None
    
    def _element_to_selector(self, element_description):
        """
        Convert an element description to a likely CSS selector
        
        Args:
            element_description (str): Description of the element
            
        Returns:
            str: A CSS selector that might match the element
        """
        element_description = element_description.strip().lower()
        
        # Common elements and their likely selectors
        if 'search' in element_description:
            return "input[type='search'], input[name='q'], input[placeholder*='search' i]"
        elif 'button' in element_description:
            text = element_description.replace('button', '').strip()
            if text:
                return f"button:has-text('{text}'), input[type='button'][value*='{text}' i], a.btn:has-text('{text}')"
            else:
                return "button, input[type='button']"
        elif 'link' in element_description:
            text = element_description.replace('link', '').strip()
            if text:
                return f"a:has-text('{text}')"
            else:
                return "a"
        elif 'input' in element_description or 'field' in element_description or 'box' in element_description:
            for field_type in ['email', 'password', 'text', 'number', 'tel']:
                if field_type in element_description:
                    return f"input[type='{field_type}']"
            return "input"
        elif 'checkbox' in element_description:
            return "input[type='checkbox']"
        elif 'radio' in element_description:
            return "input[type='radio']"
        elif 'dropdown' in element_description or 'select' in element_description:
            return "select"
        elif 'submit' in element_description:
            return "input[type='submit'], button[type='submit']"
        
        # If no specific pattern, create a text-based selector
        words = element_description.split()
        if len(words) <= 3:  # Only use short phrases for text matching
            return f"*:has-text('{element_description}')"
        
        # Default to a generic selector
        return f"*[id*='{element_description.replace(' ', '-')}' i], *[class*='{element_description.replace(' ', '-')}' i], *[name*='{element_description.replace(' ', '-')}' i]" 