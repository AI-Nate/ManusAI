# ManusAI - Terminal Command and Browser Automation Agent

ManusAI is an AI agent that can execute terminal commands and browser actions step by step, similar to the demo shown in the introduction video. This agent can:

1. Parse user requests
2. Break down tasks into executable terminal commands or browser actions
3. Execute commands and actions sequentially
4. Provide feedback on execution
5. Create and manage files, directories, and browser interactions

## Project Structure

- `agent.py`: Core agent logic
- `terminal_executor.py`: Terminal command execution module
- `command_parser.py`: Terminal command parsing module
- `browser_executor.py`: Browser automation module
- `browser_parser.py`: Browser action parsing module
- `utils.py`: Utility functions
- `main.py`: Entry point for the application

## Setup

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Install browser automation dependencies:
   - For Playwright: `playwright install chromium`
4. Create a `.env` file with your OpenAI API key (see `.env.example`)
5. Run the agent: `python main.py`

## Usage

Once the agent is running, you can provide natural language requests like:

### Terminal Commands
- "Create a directory for my project and initialize a git repository"
- "Search for files containing a specific text"
- "Download data from a URL and save it to a file"

### Browser Actions
- "Open the Redfin website and search for properties in New York"
- "Go to Google and search for the weather in San Francisco"
- "Visit GitHub and create a new repository"

The agent will automatically detect whether to use terminal commands or browser actions based on your request, break down the task into executable steps, and execute them sequentially.

## Browser Automation Features

The browser automation module supports the following actions:

- **Navigate**: Open a website URL
- **Search**: Enter a search query and submit
- **Click**: Click on buttons, links, or other elements
- **Fill Form**: Enter text into form fields
- **Extract Text**: Extract text content from elements

Screenshots are automatically taken after each browser action and saved to the `screenshots` directory. 