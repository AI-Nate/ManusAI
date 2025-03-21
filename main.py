#!/usr/bin/env python3
"""
ManusAI - Terminal Command Execution Agent
Main entry point for the application
"""

import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from agent import Agent

# Load environment variables
load_dotenv()

console = Console()

def display_welcome():
    """Display welcome message"""
    welcome_text = """
    # Welcome to ManusAI Terminal Agent
    
    I can help you execute terminal commands and browser actions step by step.
    Just tell me what you want to do, and I'll break it down into executable steps.
    
    For web browsing, I now use AI to analyze each page and determine the next actions.
    
    Type 'exit' or 'quit' to end the session.
    """
    console.print(Panel(Markdown(welcome_text), title="ManusAI", border_style="blue"))

def main():
    """Main function to run the agent"""
    display_welcome()
    
    # Check if API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[bold red]Error:[/bold red] OPENAI_API_KEY environment variable is not set.")
        console.print("Please set it in a .env file or export it in your terminal.")
        sys.exit(1)
    else:
        # Print first 5 and last 5 characters of the API key for debugging
        masked_key = api_key[:5] + "..." + api_key[-5:]
        console.print(f"[bold green]API Key loaded:[/bold green] {masked_key}")
    
    # Ensure screenshots directory exists
    screenshots_dir = "screenshots"
    if not os.path.exists(screenshots_dir):
        os.makedirs(screenshots_dir)
        console.print(f"[bold green]Created screenshots directory:[/bold green] {screenshots_dir}")
    
    # Initialize agent
    agent = Agent()
    
    # Main interaction loop
    while True:
        try:
            user_input = console.input("\n[bold green]You:[/bold green] ")
            
            if user_input.lower() in ('exit', 'quit'):
                console.print("[bold blue]ManusAI:[/bold blue] Goodbye!")
                break
                
            # Process user request
            response = agent.process_request(user_input)
            
        except KeyboardInterrupt:
            console.print("\n[bold blue]ManusAI:[/bold blue] Session terminated.")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            import traceback
            console.print(traceback.format_exc())

if __name__ == "__main__":
    main() 