"""
Utilities module for ManusAI
Contains helper functions for the AI agent
"""

import os
import json
import asyncio
import httpx
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console

console = Console()
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    console.print("[bold red]Error: OPENAI_API_KEY environment variable is not set.[/bold red]")
else:
    # Print first 5 and last 5 characters of the API key for debugging
    masked_key = api_key[:5] + "..." + api_key[-5:]
    console.print(f"[bold green]API Key loaded:[/bold green] {masked_key}")

# Create a simple client
client = OpenAI(api_key=api_key)

# System message for the agent
SYSTEM_MESSAGE = """You are ManusAI, an AI assistant that can help users with various tasks including browsing the web.

You can execute terminal commands and browser actions to help users accomplish their goals.

When the user asks you to perform a browser action like searching or navigating to a website, you should respond with a structured JSON object that contains the necessary information to execute the action.

For browser actions, use the following JSON structure:
{
  "browser_action": {
    "action_type": "search",
    "query": "essential search keywords only",
    "description": "Brief description of the search"
  }
}

Valid action_types include:
- "search": Search for something on a website
- "navigate": Navigate to a specific URL
- "click": Click on an element on the page
- "input": Enter text into a form field
- "scroll": Scroll the page
- "wait": Wait for a specified duration

For terminal commands, use the following JSON structure:
{
  "terminal_commands": ["command1", "command2"]
}

When responding to a search request:
1. Extract ONLY the essential keywords needed for an effective search
2. Do not include any explanations, reasoning, or additional text in the search query
3. Keep the search query concise and focused

For example:
- If the user says "I need to find rental apartments in New York City under $3000", the search query should be "rental apartments New York City $3000"
- If the user says "Help me search for a job as a software engineer in Seattle", the search query should be "software engineer jobs Seattle"

After completing a search, I will automatically generate a concise summary of the search results to help the user understand what was found. This summary will highlight the most relevant information based on their search goal.

IMPORTANT: When in JSON mode, your ENTIRE response must be a valid JSON object. Do not include any explanatory text outside the JSON structure. The system will parse your response as JSON, so any text outside the JSON structure will cause an error.

When not using JSON mode, provide helpful, concise responses to the user's questions.
"""

# Page analysis system message
PAGE_ANALYSIS_SYSTEM_MESSAGE = """You are a web page analysis expert. Your task is to analyze the current state of a web page
and determine the most appropriate next action to take based on the user's goal.

You will receive information about the current page including:
- URL and title
- Domain name
- Visible text elements
- Clickable elements (buttons, links, etc.)
- Form inputs

Based on this information and the user's goal, suggest the next action to take.
Your response must be a valid JSON object with the following structure:

For clicking elements:
{
  "action_type": "click",
  "element_description": "Sign In button",
  "selector_strategy": "text",  // Can be: text, id, class, xpath
  "selector_value": "Sign In",
  "description": "Click the Sign In button to access account"
}

For form inputs:
{
  "action_type": "input",
  "element_description": "Search box",
  "selector_strategy": "id",  // Can be: id, name, placeholder, label
  "selector_value": "search-input",
  "input_value": "search query",
  "description": "Enter search query in the search box"
}

For scrolling:
{
  "action_type": "scroll",
  "direction": "down",  // Can be: up, down
  "distance": 500,  // Pixels to scroll
  "description": "Scroll down to see more content"
}

For waiting:
{
  "action_type": "wait",
  "duration": 2,  // Seconds to wait
  "description": "Wait for page to load completely"
}

For navigation:
{
  "action_type": "navigate",
  "url": "https://example.com/page",
  "description": "Navigate to specific page"
}

Choose the action that will make the most progress toward the user's goal.
If you're unsure, suggest scrolling or waiting to gather more information.

Important guidelines:
1. Always prioritize actions that directly help achieve the user's goal
2. If you see a search box and the goal involves finding information, suggest using it
3. If you see pagination and need to see more results, suggest clicking the next page
4. If you see a form that needs to be filled out, suggest filling each field one by one
5. If you see a login form and the goal requires being logged in, suggest filling the credentials
6. If you see a list of results, suggest clicking on the most relevant one
7. If you're on a homepage or landing page, look for navigation elements to the relevant section
8. If the page is still loading, suggest waiting
9. If you've scrolled multiple times without finding relevant content, suggest trying a different approach
"""

def get_system_message():
    """Get the system message for the agent"""
    return SYSTEM_MESSAGE

def get_ai_page_analysis(page_state, goal_description):
    """
    Use AI to analyze the page state and suggest the next action
    
    Args:
        page_state (str): String representation of the current page state
        goal_description (str): Description of what the user is trying to achieve
        
    Returns:
        dict: Suggested next action in the format expected by browser_executor
    """
    try:
        # Create a prompt that includes the page state and goal
        user_message = f"""
Goal: {goal_description}

Current page state:
{page_state}

Based on the current page state and the goal, what should be the next action?
Respond with a valid JSON object as described in your instructions.
"""

        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-2024-11-20",  # Use an appropriate model
            messages=[
                {"role": "system", "content": PAGE_ANALYSIS_SYSTEM_MESSAGE},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,  # Lower temperature for more deterministic responses
            response_format={"type": "json_object"}
        )
        
        # Extract and parse the JSON response
        ai_response = response.choices[0].message.content
        console.print(f"[green]AI response for page analysis:[/green] {ai_response[:100]}...")
        
        try:
            next_action = json.loads(ai_response)
            
            # Convert the AI response format to the format expected by browser_executor
            converted_action = {
                'action_type': next_action.get('action_type', 'scroll'),
                'description': next_action.get('description', 'No description provided')
            }
            
            # Add action-specific parameters
            if next_action.get('action_type') == 'click':
                # Convert the selector strategy and value to a CSS selector
                selector_strategy = next_action.get('selector_strategy', 'text')
                selector_value = next_action.get('selector_value', '')
                
                if selector_strategy == 'id':
                    converted_action['selector'] = f"#{selector_value}"
                elif selector_strategy == 'class':
                    converted_action['selector'] = f".{selector_value}"
                elif selector_strategy == 'xpath':
                    converted_action['selector'] = selector_value
                    converted_action['selector_type'] = 'xpath'
                else:  # Default to text
                    converted_action['text'] = selector_value
                    
            elif next_action.get('action_type') == 'input':
                selector_strategy = next_action.get('selector_strategy', 'id')
                selector_value = next_action.get('selector_value', '')
                
                if selector_strategy == 'id':
                    converted_action['selector'] = f"#{selector_value}"
                elif selector_strategy == 'name':
                    converted_action['selector'] = f"[name='{selector_value}']"
                elif selector_strategy == 'placeholder':
                    converted_action['selector'] = f"[placeholder='{selector_value}']"
                else:
                    converted_action['selector'] = f"#{selector_value}"
                    
                converted_action['value'] = next_action.get('input_value', '')
                
            elif next_action.get('action_type') == 'scroll':
                converted_action['direction'] = next_action.get('direction', 'down')
                converted_action['distance'] = next_action.get('distance', 500)
                
            elif next_action.get('action_type') == 'wait':
                converted_action['duration'] = next_action.get('duration', 2)
                
            elif next_action.get('action_type') == 'navigate':
                converted_action['url'] = next_action.get('url', '')
            
            return converted_action
            
        except json.JSONDecodeError as e:
            console.print(f"[bold red]Error parsing AI response as JSON:[/bold red] {str(e)}")
            # Provide a fallback action
            return {
                'action_type': 'scroll',
                'direction': 'down',
                'distance': 500,
                'description': "Scroll down to see more content (fallback action after JSON parse error)"
            }
        
    except Exception as e:
        console.print(f"[bold red]Error in AI page analysis:[/bold red] {str(e)}")
        # Provide a fallback action
        return {
            'action_type': 'scroll',
            'direction': 'down',
            'distance': 500,
            'description': "Scroll down to see more content (fallback action after exception)"
        }

def get_ai_response(user_request, conversation_history, use_json_mode=False):
    """
    Get a response from the AI based on the user request and conversation history
    
    Args:
        user_request (str): The user's request
        conversation_history (list): List of conversation history dictionaries
        use_json_mode (bool): Whether to use JSON mode for structured outputs
        
    Returns:
        str or dict: The AI's response as text or parsed JSON
    """
    try:
        console.print("[yellow]Preparing messages for OpenAI API...[/yellow]")
        
        # Format the conversation history for the API
        messages = [{"role": "system", "content": get_system_message()}]
        
        # Add conversation history
        for message in conversation_history:
            messages.append({"role": message["role"], "content": message["content"]})
        
        console.print(f"[yellow]Sending request to OpenAI API with {len(messages)} messages...[/yellow]")
        
        # Import the timeout module
        import signal
        
        # Define a timeout handler
        def timeout_handler(signum, frame):
            raise TimeoutError("OpenAI API call timed out")
        
        # Set a timeout of 30 seconds
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)
        
        try:
            # Call the OpenAI API
            kwargs = {
                "model": "gpt-4o-2024-11-20",  # Use an appropriate model
                "messages": messages,
                "temperature": 0.1,
            }
            
            # Add response_format if using JSON mode
            if use_json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = client.chat.completions.create(**kwargs)
            
            # Cancel the timeout
            signal.alarm(0)
            
            console.print("[green]Response received from OpenAI API.[/green]")
            
            # Extract the response text
            response_text = response.choices[0].message.content
            
            # Parse JSON if in JSON mode
            if use_json_mode:
                try:
                    import json
                    return json.loads(response_text)
                except json.JSONDecodeError as je:
                    console.print(f"[bold red]Error parsing JSON response:[/bold red] {str(je)}")
                    console.print(f"Raw response: {response_text}")
                    return {"error": "Failed to parse JSON response"}
            
            return response_text
            
        except TimeoutError as te:
            console.print(f"[bold red]OpenAI API call timed out:[/bold red] {str(te)}")
            return "I'm sorry, but the request timed out. Please try again with a simpler request."
        
    except Exception as e:
        console.print(f"[bold red]Error getting AI response:[/bold red] {str(e)}")
        import traceback
        console.print(traceback.format_exc())
        return f"I encountered an error: {str(e)}"

def save_conversation(conversation_history, filename="conversation_history.json"):
    """
    Save the conversation history to a file
    
    Args:
        conversation_history (list): The conversation history
        filename (str): The filename to save to
    """
    try:
        with open(filename, 'w') as f:
            json.dump(conversation_history, f, indent=2)
        return True
    except Exception as e:
        console.print(f"[bold red]Error saving conversation:[/bold red] {str(e)}")
        return False

def load_conversation(filename="conversation_history.json"):
    """
    Load the conversation history from a file
    
    Args:
        filename (str): The filename to load from
        
    Returns:
        list: The conversation history
    """
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        console.print(f"[bold red]Error loading conversation:[/bold red] {str(e)}")
        return []

def get_search_query(user_request, original_query):
    """
    Get a structured search query from the AI
    
    Args:
        user_request (str): The user's full request
        original_query (str): The extracted query from the user request
        
    Returns:
        dict: Structured search query information
    """
    try:
        # Create a system message specifically for search queries
        search_system_message = """You are a search query extraction assistant. Your job is to extract the most relevant search keywords from a user request.

You will receive a user request and an initially extracted query. Your task is to:
1. Analyze the user request to understand their search intent
2. Extract ONLY the essential keywords needed for an effective search
3. Return a JSON object with the following structure:

{
  "search_query": "the essential search keywords only",
  "website_category": "the category that best matches the search intent (real_estate, jobs, shopping, travel, food, or general)"
}

DO NOT include any explanations, reasoning, or additional text in the search query. The search query should be ONLY the keywords that would be typed into a search box.

IMPORTANT RULES FOR SEARCH QUERIES:
1. Keep the query short and focused (typically 2-7 words)
2. Include only essential keywords that would be typed into a search box
3. Remove all unnecessary words like "I want", "please", "help me", etc.
4. Include specific parameters like price ranges, locations, or other constraints
5. Do not include any punctuation except when necessary (like $ for prices)
6. Do not include any explanatory text or instructions

For example:
- If the user says "I need to find rental apartments in New York City under $3000", the search query should be "rental apartments New York City $3000"
- If the user says "Help me search for a job as a software engineer in Seattle", the search query should be "software engineer jobs Seattle"
- If the user says "I want to buy a used Toyota Camry 2018 for less than $20000", the search query should be "used Toyota Camry 2018 under $20000"

Keep the search query concise, focused, and free of any unnecessary words or punctuation.
"""

        # Create the user message
        user_message = f"""
User request: {user_request}
Initially extracted query: {original_query}

Extract the essential search keywords and determine the appropriate website category.
"""

        # Call the OpenAI API with JSON mode
        response = client.chat.completions.create(
            model="gpt-4o-2024-11-20",
            messages=[
                {"role": "system", "content": search_system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON response
        import json
        result = json.loads(response.choices[0].message.content)
        
        console.print(f"[green]Extracted search query:[/green] {result.get('search_query', 'N/A')}")
        console.print(f"[green]Detected website category:[/green] {result.get('website_category', 'general')}")
        
        return result
        
    except Exception as e:
        console.print(f"[bold red]Error extracting search query:[/bold red] {str(e)}")
        # Return a fallback result
        return {
            "search_query": original_query,
            "website_category": "general"
        }

def summarize_search_results(page_state, goal_description):
    """
    Generate a summary of search results using AI
    
    Args:
        page_state (dict): The current page state with visible elements
        goal_description (str): Description of what the user is trying to achieve
        
    Returns:
        str: A summary of the search results
    """
    try:
        # Extract visible text from the page
        visible_text = [item['text'] for item in page_state['visible_elements'] if item['text'].strip()]
        
        # Create a prompt for the AI
        system_message = """You are a search results summarizer. Your task is to analyze the content from a web page and provide a concise, helpful summary of the search results.

Focus on extracting the most relevant information based on the user's goal. For real estate searches, highlight:
1. Price ranges
2. Number of available properties
3. Locations
4. Key features (bedrooms, bathrooms, amenities)
5. Any special deals or opportunities

Keep your summary clear, informative, and under 200 words. Use bullet points where appropriate.
"""

        user_message = f"""
User's goal: {goal_description}

Current page content:
{' '.join(visible_text[:100])}  # Limit to first 100 elements to avoid token limits

Based on this content, provide a concise summary of the search results that would be most helpful to the user.
"""

        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-2024-11-20",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,  # Lower temperature for more factual responses
        )
        
        # Extract the summary
        summary = response.choices[0].message.content
        
        console.print("[green]Generated search results summary.[/green]")
        return summary
        
    except Exception as e:
        console.print(f"[bold red]Error generating summary:[/bold red] {str(e)}")
        return "I couldn't generate a summary of the search results. Please review the page content manually."
