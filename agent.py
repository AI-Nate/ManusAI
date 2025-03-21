"""
Agent module for ManusAI
Contains the core logic for the AI agent
"""

import os
import time
import asyncio
import json
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress

from command_parser import CommandParser
from terminal_executor import TerminalExecutor
from browser_parser import BrowserParser
from browser_executor import BrowserExecutor
from utils import get_ai_response, get_search_query, summarize_search_results

console = Console()

class Agent:
    """
    AI Agent that processes user requests and executes terminal commands and browser actions
    """
    
    def __init__(self):
        """Initialize the agent with its components"""
        self.command_parser = CommandParser()
        self.browser_parser = BrowserParser()
        self.terminal_executor = TerminalExecutor()
        self.history = []
        self.current_tool = None  # 'terminal' or 'browser'
        self.browser_executor = None
        console.print("[bold blue]ManusAI:[/bold blue] Agent initialized and ready.")
    
    def process_request(self, user_request):
        """
        Process a user request and generate a response
        
        Args:
            user_request (str): The user's request
            
        Returns:
            str: The agent's response
        """
        console.print("[yellow]Processing request...[/yellow]")
        
        # Add the user's request to the conversation history
        self.history.append({"role": "user", "content": user_request})
        
        # Check if this is a direct browser action request
        direct_browser_request = False
        browser_keywords = ["use browser", "search online", "go ahead", "browser", "search for", "find", "look up", "website"]
        if any(keyword in user_request.lower() for keyword in browser_keywords):
            direct_browser_request = True
            console.print("[yellow]Detected direct browser action request.[/yellow]")
        
        # Check for specific website mentions
        website_mentions = {
            "redfin": {"name": "Redfin", "url": "https://www.redfin.com/city/30749/NY/New-York/apartments-for-rent"},
            "zillow": {"name": "Zillow", "url": "https://www.zillow.com/homes/for_rent/"},
            "apartments.com": {"name": "Apartments.com", "url": "https://www.apartments.com/new-york-ny/"},
            "trulia": {"name": "Trulia", "url": "https://www.trulia.com/for_rent/New_York,NY/"},
            "linkedin": {"name": "LinkedIn", "url": "https://www.linkedin.com/jobs/"},
            "indeed": {"name": "Indeed", "url": "https://www.indeed.com/jobs"},
            "amazon": {"name": "Amazon", "url": "https://www.amazon.com/s"},
            "ebay": {"name": "eBay", "url": "https://www.ebay.com/sch/i.html"}
        }
        
        direct_navigation = None
        for site_keyword, site_info in website_mentions.items():
            if site_keyword in user_request.lower():
                direct_navigation = site_info
                console.print(f"[green]Detected specific mention of {site_info['name']}. Will navigate directly.[/green]")
                break
        
        # Get AI response
        console.print("[yellow]Getting AI response...[/yellow]")
        try:
            # Use JSON mode for direct browser requests to get structured output
            use_json_mode = direct_browser_request
            response = get_ai_response(user_request, self.history, use_json_mode)
            console.print("[green]AI response received.[/green]")
        except Exception as e:
            console.print(f"[bold red]Error getting AI response:[/bold red] {str(e)}")
            import traceback
            console.print(traceback.format_exc())
            return f"I encountered an error: {str(e)}"
        
        # If we have a direct navigation target, create a navigation command
        commands = []
        if direct_navigation:
            commands.append({
                "type": "browser",
                "action": {
                    "action_type": "navigate",
                    "url": direct_navigation["url"],
                    "description": f"Navigate directly to {direct_navigation['name']} for {user_request}"
                }
            })
            console.print(f"[green]Created direct navigation command to {direct_navigation['name']}.[/green]")
        else:
            # Extract commands from the response
            console.print("[yellow]Extracting commands...[/yellow]")
            commands = self._extract_commands(response)
        
        # If no commands were found and this is a direct browser request, create a generic search command
        if not commands and direct_browser_request:
            console.print("[yellow]No commands found in response. Creating a generic search command.[/yellow]")
            
            # Extract a search query from the user request
            search_query = user_request
            import re
            
            # Try to extract a more specific search query
            search_patterns = [
                r'search for ["\']?([^"\']+)["\']?',
                r'find ["\']?([^"\']+)["\']?',
                r'look up ["\']?([^"\']+)["\']?',
                r'browse ["\']?([^"\']+)["\']?',
                r'search ["\']?([^"\']+)["\']?'
            ]
            
            for pattern in search_patterns:
                match = re.search(pattern, user_request.lower())
                if match:
                    search_query = match.group(1).strip()
                    break
            
            # Determine the appropriate website based on the user query
            website_info = self._determine_search_website(user_request, search_query)
            
            # Create a browser action using the determined website
            # Use direct navigation if available, otherwise use search
            if "direct_url" in website_info and website_info["direct_url"]:
                commands.append({
                    "type": "browser",
                    "action": {
                        "action_type": "navigate",
                        "url": website_info["direct_url"],
                        "description": f"Navigate to {website_info['name']} to find '{search_query}'"
                    }
                })
                console.print(f"[green]Created direct navigation command to {website_info['name']}.[/green]")
            else:
                commands.append({
                    "type": "browser",
                    "action": {
                        "action_type": "search",
                        "query": search_query,  # Use the refined search query from _determine_search_website
                        "website": website_info,
                        "description": f"Search for '{search_query}' on {website_info['name']}"
                    }
                })
                console.print(f"[green]Created generic search command for '{search_query}'.[/green]")
        
        # Execute any commands found in the response
        if commands:
            console.print(f"[green]Found {len(commands)} commands to execute.[/green]")
            
            # Check for browser actions
            browser_actions = self._extract_browser_actions(commands)
            
            # Display and execute browser actions
            if browser_actions:
                console.print(f"[green]Found {len(browser_actions)} browser actions to execute.[/green]")
                
                # Execute the browser plan
                self._display_browser_plan(browser_actions, user_request)
                
                # Return a response to the user
                if isinstance(response, str):
                    # If the response is a string, use it as the base response
                    # The search results summary is already displayed in the console by _execute_browser_actions
                    return response + "\n\nBrowser automation completed. See the search results summary above."
                else:
                    # If the response is a JSON object, create a new response
                    return "I've completed the browser automation task. You can see the search results summary above or continue browsing manually."
            else:
                console.print("[bold blue]ManusAI:[/bold blue] I couldn't determine any browser actions to execute.")
            
            # Check for terminal commands
            terminal_commands = self._extract_terminal_commands(commands)
            
            # Display and execute terminal commands
            if terminal_commands:
                console.print(f"[green]Found {len(terminal_commands)} terminal commands to execute.[/green]")
                self._display_terminal_plan(terminal_commands)
        
        # If the response is a dictionary (from JSON mode), convert it to a string
        if isinstance(response, dict):
            # Create a user-friendly response
            if "browser_action" in response:
                return "I've completed the browser automation task. You can see the search results summary above or continue browsing manually."
            else:
                return "I've processed your request. Is there anything else you'd like me to help with?"
        
        # Add the AI's response to the conversation history
        self.history.append({"role": "assistant", "content": response})
        
        return response
    
    def _determine_tool(self, user_request):
        """
        Determine whether to use browser or terminal based on the user request
        
        Args:
            user_request (str): The user's request
        """
        browser_keywords = ['browser', 'web', 'website', 'url', 'http', 'https', 'visit', 'navigate', 
                           'search online', 'open site', 'chrome', 'firefox', 'safari', 'internet',
                           'click', 'form', 'button', 'link', 'webpage', 'zillow', 'redfin', 'rental',
                           'property', 'properties', 'apartment', 'house', 'condo', 'real estate']
        
        # Check if any browser keywords are in the request
        if any(keyword in user_request.lower() for keyword in browser_keywords):
            self.current_tool = 'browser'
            console.print("[bold blue]ManusAI:[/bold blue] Using browser tool for this request.")
        else:
            self.current_tool = 'terminal'
            console.print("[bold blue]ManusAI:[/bold blue] Using terminal tool for this request.")
    
    def _display_terminal_plan(self, commands):
        """
        Display the terminal execution plan to the user
        
        Args:
            commands (list): List of command dictionaries
            
        Returns:
            bool: True if the user confirms execution, False otherwise
        """
        if not commands:
            return False
            
        plan_text = "# Execution Plan\n\n"
        for i, cmd in enumerate(commands, 1):
            plan_text += f"{i}. `{cmd['command']}`"
            if cmd.get('description'):
                plan_text += f" - {cmd['description']}"
            plan_text += "\n"
        
        console.print(Panel(Markdown(plan_text), title="Command Plan", border_style="green"))
        
        # Ask for confirmation
        confirm = console.input("[bold yellow]Execute this plan? (y/n):[/bold yellow] ")
        if confirm.lower() != 'y':
            console.print("[bold blue]ManusAI:[/bold blue] Plan execution cancelled.")
            return False
        
        return True
    
    def _display_browser_plan(self, browser_plan, goal_description):
        """
        Display the browser plan and execute it with AI-based adaptive navigation
        
        Args:
            browser_plan (list): List of browser actions to execute
            goal_description (str): Description of what the user is trying to achieve
            
        Returns:
            str: Result of the browser actions
        """
        if not browser_plan:
            return "No browser actions to execute."
        
        console.print("\n[bold blue]Browser Automation Plan:[/bold blue]")
        
        # Display the initial plan
        for i, action in enumerate(browser_plan):
            action_type = action.get('action_type', 'unknown')
            description = action.get('description', 'No description')
            console.print(f"[bold cyan]Step {i+1}:[/bold cyan] {action_type} - {description}")
        
        console.print("\n[bold yellow]Note: This is the initial plan. The AI will analyze each page after an action and may adapt the plan accordingly.[/bold yellow]")
        
        # Ask for confirmation before executing
        confirmation = console.input("\n[bold yellow]Execute this plan? (y/n):[/bold yellow] ")
        
        if confirmation.lower() != 'y':
            return "Browser automation cancelled."
        
        console.print("\n[bold blue]Starting adaptive browser automation...[/bold blue]")
        console.print("[yellow]The AI will analyze each page and determine the next steps automatically.[/yellow]")
        
        # Execute the browser actions with AI-based adaptive navigation
        import asyncio
        try:
            # Create a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Execute the browser actions
            result = loop.run_until_complete(self._execute_browser_actions(browser_plan, goal_description))
            
            # Close the loop
            loop.close()
        except Exception as e:
            console.print(f"[bold red]Error executing browser actions:[/bold red] {str(e)}")
            import traceback
            console.print(traceback.format_exc())
            result = f"Error executing browser actions: {str(e)}"
        
        return result
    
    def _execute_terminal_commands(self, commands):
        """
        Execute terminal commands
        
        Args:
            commands (list): List of terminal command strings
        """
        if not commands:
            return
        
        console.print("\n[bold blue]Executing Terminal Commands:[/bold blue]")
        
        for i, command in enumerate(commands):
            console.print(f"\n[bold cyan]Command {i+1}:[/bold cyan] {command}")
            
            # Ask for confirmation before executing
            confirm = console.input("[bold yellow]Execute this command? (y/n):[/bold yellow] ")
            
            if confirm.lower() == 'y':
                try:
                    # Execute the command
                    import subprocess
                    result = subprocess.run(command, shell=True, capture_output=True, text=True)
                    
                    # Display the result
                    if result.returncode == 0:
                        console.print(f"[green]Command executed successfully:[/green]\n{result.stdout}")
                    else:
                        console.print(f"[bold red]Command failed with error code {result.returncode}:[/bold red]\n{result.stderr}")
                        
                except Exception as e:
                    console.print(f"[bold red]Error executing command:[/bold red] {str(e)}")
            else:
                console.print("[yellow]Command execution skipped.[/yellow]")
        
        console.print("\n[bold blue]ManusAI:[/bold blue] All commands have been executed.")
    
    async def _execute_browser_actions(self, browser_plan, goal_description):
        """
        Execute browser actions one by one, analyzing the page after each action to determine next steps
        
        Args:
            browser_plan (list): Initial list of browser actions to execute
            goal_description (str): Description of what the user is trying to achieve
            
        Returns:
            str: Result of the browser actions
        """
        if not browser_plan:
            return "No browser actions to execute."
        
        # Initialize browser executor if not already initialized
        if not self.browser_executor:
            self.browser_executor = BrowserExecutor()
            if not await self.browser_executor.initialize():
                return "Failed to initialize browser."
        
        results = []
        executed_actions = []
        
        try:
            # Execute the first action from the plan
            initial_action = browser_plan[0]
            action_type = initial_action.get('action_type', '')
            
            # Display information about the action
            self._display_action_info(1, action_type, initial_action)
            
            # Execute the action
            result = await self.browser_executor.execute_action(initial_action)
            results.append(result)
            executed_actions.append(initial_action)
            
            console.print(f"[green]Action 1 completed. Analyzing page for next action...[/green]")
            
            # Now enter the adaptive loop
            action_count = 1
            max_actions = 20  # Safety limit to prevent infinite loops
            
            while action_count < max_actions:
                # Capture the current page state
                page_state = await self.browser_executor.capture_page_state()
                
                if not page_state:
                    console.print("[bold red]Error capturing page state. Stopping execution.[/bold red]")
                    break
                
                # Analyze the page to determine the next action
                next_action = await self.browser_executor.analyze_page_for_next_action(goal_description)
                
                if not next_action:
                    console.print("[bold yellow]No further actions suggested. Stopping execution.[/bold yellow]")
                    break
                
                # Check if we've completed the goal
                if self._check_goal_completion(executed_actions, goal_description):
                    console.print("[bold green]Goal appears to be completed. Stopping execution.[/bold green]")
                    break
                
                # Display information about the next action
                action_count += 1
                action_type = next_action.get('action_type', '')
                
                # Display the next action
                self._display_action_info(action_count, action_type, next_action)
                
                # Execute the next action
                result = await self.browser_executor.execute_action(next_action)
                results.append(result)
                executed_actions.append(next_action)
                
                console.print(f"[green]Action {action_count} completed. Analyzing page for next action...[/green]")
                
                # Add a small delay between actions to avoid overwhelming the website
                await asyncio.sleep(1)
            
            if action_count >= max_actions:
                console.print("[bold yellow]Reached maximum number of actions. Stopping execution.[/bold yellow]")
            
            # Capture final page state
            final_state = await self.browser_executor.capture_page_state()
            
            # Format the results
            actions_summary = "\n".join([f"- {action.get('description', 'No description')}" for action in executed_actions])
            
            # Extract key information from the final page state
            page_info = ""
            if final_state:
                page_info = f"Final URL: {final_state['url']}\nPage Title: {final_state['title']}\n\n"
                
                # Generate a summary of the search results
                search_summary = summarize_search_results(final_state, goal_description)
                
                # Display the summary to the user
                console.print("\n[bold blue]Search Results Summary:[/bold blue]")
                console.print(f"[cyan]{search_summary}[/cyan]")
                
                # Add the summary to the page info
                page_info += f"Search Results Summary:\n{search_summary}\n\n"
                
                # Check if we're on a real estate search results page
                if any(domain in final_state['url'] for domain in ["redfin.com", "zillow.com", "apartments.com", "trulia.com"]):
                    # Try to extract property listings
                    try:
                        import re
                        
                        # Extract property information
                        property_info = []
                        
                        # Look for price patterns
                        prices = re.findall(r'\$[\d,]+(?:,\d+)?', ' '.join([item['text'] for item in final_state['visible_elements']]))
                        
                        # Look for bedroom/bathroom patterns
                        beds_baths = []
                        for item in final_state['visible_elements']:
                            match = re.search(r'(\d+)\s*beds?.*?(\d+(?:\.\d+)?)\s*baths?', item['text'])
                            if match:
                                beds_baths.append(f"{match.group(1)} beds, {match.group(2)} baths")
                        
                        # Look for addresses
                        addresses = []
                        for item in final_state['visible_elements']:
                            if re.search(r'\d+\s+[A-Za-z\s]+(?:St|Ave|Blvd|Dr|Ln|Rd|Way|Place|Plaza|Court|Terrace)', item['text']):
                                addresses.append(item['text'])
                        
                        # Combine the information
                        page_info += "Property Listings Found:\n"
                        for i in range(min(len(prices), 5)):  # Limit to 5 listings for summary
                            listing_info = f"- {prices[i] if i < len(prices) else 'Price unknown'}"
                            if i < len(beds_baths):
                                listing_info += f", {beds_baths[i]}"
                            if i < len(addresses):
                                listing_info += f", {addresses[i]}"
                            property_info.append(listing_info)
                        
                        page_info += "\n".join(property_info) + "\n\n"
                        
                    except Exception as e:
                        console.print(f"[yellow]Error extracting property listings: {str(e)}[/yellow]")
                        # We already have the AI-generated summary, so no need for a fallback here
                else:
                    # We already have the AI-generated summary, so no need for additional text extraction
                    pass
            
            # Ask if the user wants to keep the browser open
            keep_open = console.input("\n[bold yellow]Keep the browser open? (y/n):[/bold yellow] ")
            
            if keep_open.lower() != 'y':
                await self.browser_executor.close()
                console.print("[bold blue]Browser closed.[/bold blue]")
            else:
                console.print("[bold blue]Browser left open for manual browsing.[/bold blue]")
            
            return f"""
Browser Automation Results:

Actions Executed:
{actions_summary}

{page_info}

Results:
{' '.join(results)}
"""
        except Exception as e:
            console.print(f"[bold red]Error executing browser actions:[/bold red] {str(e)}")
            import traceback
            console.print(traceback.format_exc())
            
            # Try to close the browser if there was an error
            try:
                if self.browser_executor and self.browser_executor.is_initialized:
                    await self.browser_executor.close()
                    console.print("[bold blue]Browser closed after error.[/bold blue]")
            except Exception as close_error:
                console.print(f"[bold red]Error closing browser:[/bold red] {str(close_error)}")
            
            return f"Error executing browser actions: {str(e)}"
    
    def _check_goal_completion(self, executed_actions, goal_description):
        """
        Check if the goal has been completed based on executed actions
        
        Args:
            executed_actions (list): List of actions that have been executed
            goal_description (str): Description of what the user is trying to achieve
            
        Returns:
            bool: True if the goal appears to be completed, False otherwise
        """
        # This is a simple heuristic - in a real implementation, you would use AI to determine if the goal is complete
        
        # If we've executed at least 5 actions, check if we're likely done
        if len(executed_actions) >= 5:
            # Check if we've performed actions that suggest completion
            action_types = [action.get('action_type') for action in executed_actions]
            
            # If we've clicked multiple items and then captured state, we might be done
            if action_types.count('click') >= 2 and action_types[-1] == 'capture_state':
                return True
            
            # If we've scrolled multiple times without finding anything to click, we might be done
            if action_types.count('scroll') >= 3 and 'click' not in action_types[-3:]:
                return True
        
        return False

    def _display_action_info(self, step_number, action_type, action):
        """
        Display detailed information about an action
        
        Args:
            step_number (int): The step number
            action_type (str): The type of action
            action (dict): The action dictionary
        """
        if action_type == 'navigate':
            url = action.get('url', '')
            if "redfin.com" in url or "zillow.com" in url or "apartments.com" in url or "trulia.com" in url:
                console.print(f"\n[bold blue]Step {step_number}:[/bold blue] Navigating directly to real estate website: {url}")
            elif "linkedin.com" in url or "indeed.com" in url or "glassdoor.com" in url:
                console.print(f"\n[bold blue]Step {step_number}:[/bold blue] Navigating directly to job search website: {url}")
            elif "amazon.com" in url or "ebay.com" in url or "walmart.com" in url:
                console.print(f"\n[bold blue]Step {step_number}:[/bold blue] Navigating directly to shopping website: {url}")
            else:
                console.print(f"\n[bold blue]Step {step_number}:[/bold blue] Navigating to {url}")
        elif action_type == 'search':
            console.print(f"\n[bold blue]Step {step_number}:[/bold blue] Searching for '{action.get('query')}'")
        elif action_type == 'search_redfin':
            console.print(f"\n[bold blue]Step {step_number}:[/bold blue] Searching Redfin for '{action.get('location')}'")
        elif action_type == 'click':
            console.print(f"\n[bold blue]Step {step_number}:[/bold blue] Clicking on '{action.get('description')}'")
        elif action_type == 'fill_form':
            console.print(f"\n[bold blue]Step {step_number}:[/bold blue] Filling form fields")
        elif action_type == 'extract_text':
            console.print(f"\n[bold blue]Step {step_number}:[/bold blue] Extracting text from '{action.get('selector')}'")
        elif action_type == 'scroll':
            console.print(f"\n[bold blue]Step {step_number}:[/bold blue] Scrolling {action.get('direction', 'down')} by {action.get('distance', 500)} pixels")
        elif action_type == 'wait':
            console.print(f"\n[bold blue]Step {step_number}:[/bold blue] Waiting for {action.get('duration', 2)} seconds")
        elif action_type == 'input':
            console.print(f"\n[bold blue]Step {step_number}:[/bold blue] Entering '{action.get('value')}' into {action.get('description', 'input field')}")
        else:
            console.print(f"\n[bold blue]Step {step_number}:[/bold blue] {action.get('description', 'No description')}")

    def _extract_commands(self, response):
        """
        Extract commands from the AI response
        
        Args:
            response (str or dict): The AI's response, either as text or parsed JSON
            
        Returns:
            list: List of command dictionaries
        """
        commands = []
        
        # If the response is already a dictionary (from JSON mode), process it directly
        if isinstance(response, dict):
            console.print("[green]Processing structured JSON response.[/green]")
            
            # Check if the response contains a browser action
            if "browser_action" in response:
                browser_action = response["browser_action"]
                
                # Check if this is a search action for a specific website
                if browser_action.get('action_type') == 'search' and 'query' in browser_action:
                    query = browser_action.get('query', '')
                    
                    # Check for specific website mentions in the query
                    website_mentions = {
                        "redfin": {"name": "Redfin", "url": "https://www.redfin.com/city/30749/NY/New-York/apartments-for-rent"},
                        "zillow": {"name": "Zillow", "url": "https://www.zillow.com/homes/for_rent/"},
                        "apartments.com": {"name": "Apartments.com", "url": "https://www.apartments.com/new-york-ny/"},
                        "trulia": {"name": "Trulia", "url": "https://www.trulia.com/for_rent/New_York,NY/"}
                    }
                    
                    direct_navigation = None
                    for site_keyword, site_info in website_mentions.items():
                        if site_keyword in query.lower():
                            direct_navigation = site_info
                            console.print(f"[green]Detected specific mention of {site_info['name']} in search query. Will navigate directly.[/green]")
                            break
                    
                    if direct_navigation:
                        # Create a direct navigation action instead of search
                        commands.append({
                            "type": "browser",
                            "action": {
                                "action_type": "navigate",
                                "url": direct_navigation["url"],
                                "description": f"Navigate directly to {direct_navigation['name']} to find '{query}'"
                            }
                        })
                        console.print(f"[green]Created direct navigation command to {direct_navigation['name']}.[/green]")
                    else:
                        # Use the original search action
                        if isinstance(browser_action, dict) and "action_type" in browser_action:
                            commands.append({
                                "type": "browser",
                                "action": browser_action
                            })
                            console.print(f"[green]Found browser action: {browser_action['action_type']}[/green]")
                elif isinstance(browser_action, dict) and "action_type" in browser_action:
                    commands.append({
                        "type": "browser",
                        "action": browser_action
                    })
                    console.print(f"[green]Found browser action: {browser_action['action_type']}[/green]")
                elif isinstance(browser_action, list):
                    for action in browser_action:
                        if isinstance(action, dict) and "action_type" in action:
                            commands.append({
                                "type": "browser",
                                "action": action
                            })
                            console.print(f"[green]Found browser action: {action['action_type']}[/green]")
            
            # Check if the response contains terminal commands
            if "terminal_commands" in response:
                terminal_commands = response["terminal_commands"]
                if isinstance(terminal_commands, list):
                    for cmd in terminal_commands:
                        if isinstance(cmd, str):
                            commands.append({
                                "type": "terminal",
                                "command": cmd
                            })
                            console.print(f"[green]Found terminal command: {cmd}[/green]")
                elif isinstance(terminal_commands, str):
                    commands.append({
                        "type": "terminal",
                        "command": terminal_commands
                    })
                    console.print(f"[green]Found terminal command: {terminal_commands}[/green]")
            
            return commands
        
        # If the response is a string, use the existing parsing logic
        # Check if the response contains command blocks
        import re
        command_blocks = re.findall(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
        
        if command_blocks:
            console.print("[green]Found command blocks in the response.[/green]")
            
            for block in command_blocks:
                try:
                    # Try to parse the block as JSON
                    import json
                    command = json.loads(block)
                    commands.append(command)
                except json.JSONDecodeError:
                    # If it's not valid JSON, check if it's a terminal command
                    if block.strip().startswith('$'):
                        command_text = block.strip().lstrip('$').strip()
                        commands.append({
                            "type": "terminal",
                            "command": command_text
                        })
            
            return commands
        
        # Check if the response contains URLs
        urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*(?:\?[/\w\.-=&]*)?', response)
        
        if urls:
            console.print("[green]Found URLs in the response.[/green]")
            
            for url in urls:
                commands.append({
                    "type": "browser",
                    "action": {
                        "action_type": "navigate",
                        "url": url,
                        "description": f"Navigate to {url}"
                    }
                })
            
            return commands
        
        # Check if the response contains browser action keywords
        browser_keywords = ["search", "browse", "navigate", "go to", "open", "visit", "find", "look up"]
        
        for keyword in browser_keywords:
            if keyword in response.lower():
                console.print("[green]Found browser action keywords. Creating browser search command.[/green]")
                
                # Extract a search query from the response
                search_query = response
                
                # Try to extract a more specific search query
                search_patterns = [
                    r'search for ["\']?([^"\']+)["\']?',
                    r'find ["\']?([^"\']+)["\']?',
                    r'look up ["\']?([^"\']+)["\']?',
                    r'browse ["\']?([^"\']+)["\']?',
                    r'search ["\']?([^"\']+)["\']?'
                ]
                
                for pattern in search_patterns:
                    match = re.search(pattern, response.lower())
                    if match:
                        search_query = match.group(1).strip()
                        break
                
                # Check for specific website mentions in the search query
                website_mentions = {
                    "redfin": {"name": "Redfin", "url": "https://www.redfin.com/city/30749/NY/New-York/apartments-for-rent"},
                    "zillow": {"name": "Zillow", "url": "https://www.zillow.com/homes/for_rent/"},
                    "apartments.com": {"name": "Apartments.com", "url": "https://www.apartments.com/new-york-ny/"},
                    "trulia": {"name": "Trulia", "url": "https://www.trulia.com/for_rent/New_York,NY/"}
                }
                
                direct_navigation = None
                for site_keyword, site_info in website_mentions.items():
                    if site_keyword in search_query.lower():
                        direct_navigation = site_info
                        console.print(f"[green]Detected specific mention of {site_info['name']} in search query. Will navigate directly.[/green]")
                        break
                
                if direct_navigation:
                    # Create a direct navigation action instead of search
                    commands.append({
                        "type": "browser",
                        "action": {
                            "action_type": "navigate",
                            "url": direct_navigation["url"],
                            "description": f"Navigate directly to {direct_navigation['name']} to find '{search_query}'"
                        }
                    })
                    console.print(f"[green]Created direct navigation command to {direct_navigation['name']}.[/green]")
                else:
                    # Determine the appropriate website based on the user query
                    website_info = self._determine_search_website(search_query, search_query)
                    
                    # Create a browser action using the determined website
                    # Use direct navigation if available, otherwise use search
                    if "direct_url" in website_info and website_info["direct_url"]:
                        commands.append({
                            "type": "browser",
                            "action": {
                                "action_type": "navigate",
                                "url": website_info["direct_url"],
                                "description": f"Navigate to {website_info['name']} to find '{search_query}'"
                            }
                        })
                        console.print(f"[green]Created direct navigation command to {website_info['name']}.[/green]")
                    else:
                        commands.append({
                            "type": "browser",
                            "action": {
                                "action_type": "search",
                                "query": search_query,  # Use the refined search query from _determine_search_website
                                "website": website_info,
                                "description": f"Search for '{search_query}' on {website_info['name']}"
                            }
                        })
                        console.print(f"[green]Created generic search command for '{search_query}'.[/green]")
                
                break
        
        return commands

    def _extract_browser_actions(self, commands):
        """
        Extract browser actions from commands
        
        Args:
            commands (list): List of command dictionaries
            
        Returns:
            list: List of browser action dictionaries
        """
        browser_actions = []
        
        for command in commands:
            # Check if this is a browser action
            if isinstance(command, dict) and command.get("type") in ["browser", "web"]:
                # Extract the action
                action = command.get("action", {})
                if action and isinstance(action, dict) and "action_type" in action:
                    browser_actions.append(action)
                elif "actions" in command and isinstance(command["actions"], list):
                    # Handle case where multiple actions are specified
                    for action in command["actions"]:
                        if isinstance(action, dict) and "action_type" in action:
                            browser_actions.append(action)
        
        return browser_actions

    def _extract_terminal_commands(self, commands):
        """
        Extract terminal commands from commands
        
        Args:
            commands (list): List of command dictionaries
            
        Returns:
            list: List of terminal command strings
        """
        terminal_commands = []
        
        for command in commands:
            # Check if this is a terminal command
            if isinstance(command, dict) and command.get("type") in ["terminal", "command"]:
                # Extract the command
                cmd = command.get("command")
                if cmd and isinstance(cmd, str):
                    terminal_commands.append(cmd)
                elif "commands" in command and isinstance(command["commands"], list):
                    # Handle case where multiple commands are specified
                    for cmd in command["commands"]:
                        if isinstance(cmd, str):
                            terminal_commands.append(cmd)
        
        return terminal_commands

    def _determine_search_website(self, user_request, search_query):
        """
        Determine the appropriate website based on the user query
        
        Args:
            user_request (str): The user's request
            search_query (str): The search query
            
        Returns:
            dict: Information about the determined website
        """
        from utils import get_search_query
        
        # Get a structured search query from the AI
        result = get_search_query(user_request, search_query)
        
        # Extract the refined search query and website category
        refined_search_query = result.get("search_query", search_query)
        website_category = result.get("website_category", "general")
        
        # Update the search query with the refined version
        search_query = refined_search_query
        
        # Define website categories and their associated websites with direct navigation URLs
        website_categories = {
            "real_estate": [
                {"name": "Redfin", "url": "https://www.redfin.com", "direct_url": "https://www.redfin.com/city/30749/NY/New-York/apartments-for-rent"},
                {"name": "Apartments.com", "url": "https://www.apartments.com", "direct_url": "https://www.apartments.com/new-york-ny/"},
                {"name": "Trulia", "url": "https://www.trulia.com", "direct_url": "https://www.trulia.com/for_rent/New_York,NY/"}
            ],
            "jobs": [
                {"name": "LinkedIn", "url": "https://www.linkedin.com", "direct_url": "https://www.linkedin.com/jobs/"},
                {"name": "Indeed", "url": "https://www.indeed.com", "direct_url": "https://www.indeed.com/jobs"},
                {"name": "Glassdoor", "url": "https://www.glassdoor.com", "direct_url": "https://www.glassdoor.com/Job/index.htm"}
            ],
            "shopping": [
                {"name": "Amazon", "url": "https://www.amazon.com", "direct_url": "https://www.amazon.com/s"},
                {"name": "eBay", "url": "https://www.ebay.com", "direct_url": "https://www.ebay.com/sch/i.html"},
                {"name": "Walmart", "url": "https://www.walmart.com", "direct_url": "https://www.walmart.com/search/"}
            ],
            "travel": [
                {"name": "Expedia", "url": "https://www.expedia.com", "direct_url": "https://www.expedia.com/Hotels"},
                {"name": "Booking.com", "url": "https://www.booking.com", "direct_url": "https://www.booking.com/index.html"},
                {"name": "Airbnb", "url": "https://www.airbnb.com", "direct_url": "https://www.airbnb.com/s/homes"}
            ],
            "food": [
                {"name": "Yelp", "url": "https://www.yelp.com", "direct_url": "https://www.yelp.com/search"},
                {"name": "DoorDash", "url": "https://www.doordash.com", "direct_url": "https://www.doordash.com/food-delivery/"},
                {"name": "UberEats", "url": "https://www.ubereats.com", "direct_url": "https://www.ubereats.com/"}
            ],
            "general": [
                {"name": "Google", "url": "https://www.google.com", "direct_url": "https://www.google.com/search"},
                {"name": "Bing", "url": "https://www.bing.com", "direct_url": "https://www.bing.com/search"},
                {"name": "DuckDuckGo", "url": "https://www.duckduckgo.com", "direct_url": "https://duckduckgo.com/"}
            ]
        }
        
        # Check if the category exists in our mapping
        if website_category in website_categories:
            # Return the first website in the category
            return website_categories[website_category][0]
        
        # Default to Google if no specific category is matched
        console.print("[yellow]No specific category detected. Using Google as default search engine.[/yellow]")
        return {
            "name": "Google",
            "url": "https://www.google.com",
            "direct_url": "https://www.google.com/search"
        }

    def _display_search_website(self, website):
        """
        Display information about the determined website to the user
        
        Args:
            website (dict): Information about the determined website
        """
        console.print("\n[bold blue]ManusAI:[/bold blue] I've determined that the best website to search for your query is:")
        console.print(f"[bold cyan]{website['name']}[/bold cyan]")
        console.print(f"[bold blue]URL:[/bold blue] {website['url']}")
        console.print("\n[bold yellow]Note: This is a suggested website. You can still search on other websites if you prefer.[/bold yellow]")
        console.print("\n[bold yellow]Would you like to proceed with this website? (y/n):[/bold yellow]")
        
        confirm = console.input()
        if confirm.lower() != 'y':
            console.print("[bold blue]ManusAI:[/bold blue] Proceeding with a different website.")
            return False
        return True 