# Understanding LLM Control Commands in ManusAI

## Overview
This document explains how the ManusAI system uses LLM (Large Language Model) control commands to execute terminal commands and browser actions based on user requests.

## Core Architecture

### 1. Main Flow
- **Entry Point**: `main.py` - Handles user input and initializes the Agent
- **Agent**: `agent.py` - Core orchestrator that processes requests and manages execution
- **Command Parsing**: `command_parser.py` - Extracts executable commands from AI responses
- **AI Integration**: `utils.py` - Handles OpenAI API calls and response processing
- **Execution**: `terminal_executor.py` and `browser_executor.py` - Execute the parsed commands

### 2. LLM Control Command Flow

#### Step 1: User Request Processing
1. User provides a natural language request
2. Agent determines if it's a browser or terminal request
3. System prepares conversation history and context

#### Step 2: AI Response Generation
1. OpenAI API is called with structured system prompts
2. AI generates either:
   - Structured JSON response (for browser actions)
   - Natural language response with embedded commands
   - Direct command suggestions

#### Step 3: Command Extraction
1. `CommandParser` extracts commands from AI responses
2. Supports multiple formats:
   - JSON blocks with structured actions
   - Code blocks with shell commands
   - Inline commands with descriptions
   - Direct URL navigation

#### Step 4: Command Execution
1. Commands are categorized (terminal vs browser)
2. User confirmation is requested for each command
3. Commands are executed with proper error handling

## Key Components

### 1. System Messages
The system uses carefully crafted prompts to guide the LLM:

```python
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
"""
```

### 2. Command Extraction Patterns
The system recognizes multiple command formats:

- **JSON Blocks**: ````json { "action": "..." } ````
- **Code Blocks**: ````bash command ````
- **Inline Commands**: `command`
- **Numbered Lists**: `1. command - description`

### 3. Browser Action Types
Supported browser actions include:
- `search`: Search for content on websites
- `navigate`: Navigate to specific URLs
- `click`: Click on page elements
- `input`: Fill form fields
- `scroll`: Scroll the page
- `wait`: Wait for specified duration

### 4. Adaptive Navigation
The system uses AI to analyze web pages and determine next actions:
- Captures page state (URL, title, visible elements)
- Analyzes content using AI
- Suggests next actions based on user goals
- Adapts the plan dynamically

## Example Workflow

### User Request: "Find rental apartments in NYC under $3000"

1. **Request Processing**:
   ```python
   # Agent detects browser keywords and creates direct navigation
   direct_navigation = {
       "name": "Redfin", 
       "url": "https://www.redfin.com/city/30749/NY/New-York/apartments-for-rent"
   }
   ```

2. **AI Response**:
   ```json
   {
     "browser_action": {
       "action_type": "navigate",
       "url": "https://www.redfin.com/city/30749/NY/New-York/apartments-for-rent",
       "description": "Navigate to Redfin to search for NYC apartments"
     }
   }
   ```

3. **Command Execution**:
   - Browser opens and navigates to Redfin
   - AI analyzes the page and suggests next actions
   - System adapts based on page content
   - Results are summarized for the user

## Safety Features

1. **User Confirmation**: All commands require user approval
2. **Error Handling**: Comprehensive try-catch blocks
3. **Timeout Protection**: API calls have 30-second timeouts
4. **Fallback Actions**: Default actions when AI analysis fails
5. **Command Validation**: Checks for valid shell commands

## Key Benefits

1. **Natural Language Interface**: Users can describe tasks in plain English
2. **Adaptive Execution**: System learns and adapts during execution
3. **Multi-Modal Support**: Handles both terminal and browser actions
4. **Structured Output**: JSON responses ensure consistent parsing
5. **Error Recovery**: Graceful handling of failures and timeouts

## Technical Implementation

### Command Parsing Logic
```python
def parse_commands(self, ai_response):
    # Extract from code blocks
    code_blocks = re.findall(self.command_block_pattern, content)
    
    # Extract from JSON blocks
    if isinstance(response, dict):
        if "browser_action" in response:
            commands.append({"type": "browser", "action": response["browser_action"]})
    
    # Extract from inline commands
    inline_commands = re.findall(self.command_line_pattern, content)
    
    return commands
```

### AI Integration
```python
def get_ai_response(user_request, conversation_history, use_json_mode=False):
    messages = [{"role": "system", "content": SYSTEM_MESSAGE}]
    messages.extend(conversation_history)
    
    kwargs = {
        "model": "gpt-4o-2024-11-20",
        "messages": messages,
        "temperature": 0.1,
    }
    
    if use_json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content
```

## Command Execution Process

### 1. Terminal Command Execution

Terminal commands are executed through the `TerminalExecutor` class with the following process:

#### Safety Checks
```python
def _is_dangerous(self, command):
    # Check for dangerous command prefixes
    dangerous_commands = {
        'rm', 'rmdir', 'del', 'format', 'shutdown', 'reboot',
        'mkfs', 'dd', ':(){:|:&};:', '> /dev/sda', 'chmod -R 777 /'
    }
    
    # Check for rm -rf or similar destructive patterns
    if 'rm -rf' in command_lower or 'rm -r -f' in command_lower:
        return True
```

#### Execution Process
1. **Command Validation**: Check if command is potentially dangerous
2. **User Confirmation**: Request user approval for dangerous commands
3. **Platform Detection**: Handle Windows vs Unix command differences
4. **Subprocess Execution**: Use `subprocess.Popen` with proper security settings
5. **Output Capture**: Capture stdout/stderr with timeout protection
6. **Error Handling**: Return structured success/failure responses

#### Example Execution Flow
```python
def execute(self, command):
    # Safety check
    if self._is_dangerous(command):
        confirm = console.input(f"Warning: Command may be destructive. Proceed? (y/n): ")
        if confirm.lower() != 'y':
            return False, "Command execution cancelled for safety reasons."
    
    # Execute with subprocess
    process = subprocess.Popen(
        ['/bin/sh', '-c', command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=self.current_dir
    )
    
    # Capture output with timeout
    stdout, stderr = process.communicate(timeout=60)
    
    return process.returncode == 0, stdout or stderr
```

### 2. Browser Command Execution

Browser commands are executed through the `BrowserExecutor` class using Playwright:

#### Browser Initialization
```python
async def initialize(self):
    # Launch browser with stealth settings
    self.browser = await self.playwright.chromium.launch(
        headless=False,
        args=browser_args  # Anti-detection arguments
    )
    
    # Create context with human-like settings
    self.context = await self.browser.new_context(
        user_agent=user_agent,
        viewport=viewport,
        locale="en-US",
        timezone_id="America/New_York"
    )
    
    # Add anti-detection JavaScript
    await self.context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
```

#### Action Types and Execution

##### Navigation
```python
async def navigate(self, url):
    await self.page.goto(url)
    current_url = self.page.url
    screenshot_path = await self._take_screenshot("navigate")
    return True
```

##### Search
```python
async def search(self, query, selector="input[type='search']"):
    # Multiple approaches for finding search boxes
    # 1. Use provided selector
    # 2. Site-specific selectors
    # 3. Generic search patterns
    # 4. Direct URL navigation
    
    # Human-like interaction
    await self._human_like_move(search_input)
    await self._human_like_type(search_input, query)
    await search_input.press("Enter")
```

##### Clicking
```python
async def click(self, selector, selector_type="css"):
    # Human-like mouse movement with bezier curves
    control_points = generate_bezier_curve(
        current_x, current_y, target_x, target_y
    )
    
    # Move mouse along curve
    for point in control_points:
        await self.page.mouse.move(point[0], point[1])
        await asyncio.sleep(random.uniform(0.01, 0.03))
    
    # Click with random delay
    await asyncio.sleep(random.uniform(0.1, 0.3))
    await element.click()
```

##### Form Filling
```python
async def fill_input(self, selector, value):
    # Click to focus
    await element.click()
    
    # Clear existing content
    await element.fill("")
    
    # Type with human-like delays
    for char in value:
        await element.type(char, delay=random.uniform(50, 150))
        await asyncio.sleep(random.uniform(0.01, 0.05))
```

#### Adaptive Execution with AI Analysis
```python
async def analyze_page_for_next_action(self, goal_description):
    # Capture current page state
    page_state = await self.capture_page_state()
    
    # Send to AI for analysis
    next_action = get_ai_page_analysis(page_state, goal_description)
    
    # Execute suggested action
    return await self.execute_action(next_action)
```

### 3. Execution Orchestration

The `Agent` class orchestrates the execution process:

#### Command Categorization
```python
def _extract_browser_actions(self, commands):
    browser_actions = []
    for command in commands:
        if command.get("type") in ["browser", "web"]:
            action = command.get("action", {})
            if action and "action_type" in action:
                browser_actions.append(action)
    return browser_actions

def _extract_terminal_commands(self, commands):
    terminal_commands = []
    for command in commands:
        if command.get("type") in ["terminal", "command"]:
            cmd = command.get("command")
            if cmd:
                terminal_commands.append(cmd)
    return terminal_commands
```

#### Execution Flow
```python
def process_request(self, user_request):
    # 1. Get AI response
    response = get_ai_response(user_request, self.history, use_json_mode)
    
    # 2. Extract commands
    commands = self._extract_commands(response)
    
    # 3. Categorize and execute
    browser_actions = self._extract_browser_actions(commands)
    terminal_commands = self._extract_terminal_commands(commands)
    
    # 4. Execute with user confirmation
    if browser_actions:
        self._display_browser_plan(browser_actions, user_request)
    
    if terminal_commands:
        self._display_terminal_plan(terminal_commands)
```

### 4. Safety and Error Handling

#### Timeout Protection
```python
# Terminal commands: 60-second timeout
stdout, stderr = process.communicate(timeout=60)

# Browser actions: 15-second timeout for page loads
await self.page.wait_for_load_state("networkidle", timeout=15000)
```

#### Error Recovery
```python
try:
    result = await self.browser_executor.execute_action(action)
except Exception as e:
    # Fallback to simple scroll action
    return {
        'action_type': 'scroll',
        'direction': 'down',
        'distance': 500,
        'description': "Scroll down to see more content (fallback action)"
    }
```

#### User Confirmation
```python
# All commands require user approval
confirm = console.input("[bold yellow]Execute this plan? (y/n):[/bold yellow] ")
if confirm.lower() != 'y':
    console.print("[bold blue]Plan execution cancelled.[/bold blue]")
    return False
```

## Modules Used and Open Source Alternatives

### Current Modules in ManusAI

#### 1. **Terminal Command Execution**
- **Custom Implementation**: `terminal_executor.py`
- **Core Dependencies**: 
  - `subprocess` (Python standard library)
  - `platform` (Python standard library)
  - `shlex` (Python standard library)
  - `pexpect` (for interactive commands)

#### 2. **Browser Automation**
- **Primary**: `playwright` (Microsoft)
- **Secondary**: `selenium` (backup option)
- **Custom Implementation**: `browser_executor.py`

#### 3. **AI Integration**
- **Primary**: `openai` (OpenAI API client)
- **Custom Implementation**: `utils.py` for prompt engineering

#### 4. **User Interface**
- **Primary**: `rich` (text formatting and UI)
- **Secondary**: `colorama` (cross-platform colored output)
- **Input**: `prompt_toolkit` (advanced input handling)

### Open Source Alternatives

#### 1. **Terminal Command Execution**

**Current**: Custom `TerminalExecutor` class
**Alternatives**:
- **`sh`**: Python library for shell command execution
  ```bash
  pip install sh
  ```
  ```python
  import sh
  result = sh.ls('-la')  # Execute ls -la
  ```

- **`plumbum`**: Shell-like syntax for Python
  ```bash
  pip install plumbum
  ```
  ```python
  from plumbum import local
  ls = local['ls']
  result = ls['-la']()
  ```

- **`fabric`**: High-level SSH library with command execution
  ```bash
  pip install fabric
  ```
  ```python
  from fabric import Connection
  with Connection('hostname') as c:
      result = c.run('ls -la')
  ```

#### 2. **Browser Automation**

**Current**: `playwright` + custom `BrowserExecutor`
**Alternatives**:

- **`selenium`**: Most popular web automation library
  ```bash
  pip install selenium
  ```
  ```python
  from selenium import webdriver
  from selenium.webdriver.common.by import By
  driver = webdriver.Chrome()
  driver.get("https://www.example.com")
  ```

- **`requests-html`**: HTML parsing with JavaScript support
  ```bash
  pip install requests-html
  ```
  ```python
  from requests_html import HTMLSession
  session = HTMLSession()
  r = session.get('https://www.example.com')
  r.html.render()  # Execute JavaScript
  ```

- **`scrapy`**: Web scraping framework
  ```bash
  pip install scrapy
  ```
  ```python
  import scrapy
  class MySpider(scrapy.Spider):
      name = 'example'
      start_urls = ['https://www.example.com']
  ```

- **`mechanicalsoup`**: Python library for automating interaction with websites
  ```bash
  pip install mechanicalsoup
  ```
  ```python
  import mechanicalsoup
  browser = mechanicalsoup.Browser()
  page = browser.get("https://www.example.com")
  ```

#### 3. **AI Integration**

**Current**: `openai` + custom prompt engineering
**Alternatives**:

- **`langchain`**: Framework for developing applications with LLMs
  ```bash
  pip install langchain
  ```
  ```python
  from langchain.llms import OpenAI
  from langchain.chains import LLMChain
  llm = OpenAI()
  chain = LLMChain(llm=llm, prompt=prompt)
  ```

- **`transformers`**: Hugging Face transformers library
  ```bash
  pip install transformers
  ```
  ```python
  from transformers import pipeline
  generator = pipeline('text-generation', model='gpt2')
  ```

- **`anthropic`**: Claude API client
  ```bash
  pip install anthropic
  ```
  ```python
  import anthropic
  client = anthropic.Anthropic()
  message = client.messages.create(...)
  ```

#### 4. **Command Parsing**

**Current**: Custom `CommandParser` class
**Alternatives**:

- **`click`**: Command line interface creation kit
  ```bash
  pip install click
  ```
  ```python
  import click
  @click.command()
  @click.option('--name', default='World', help='Name to greet')
  def hello(name):
      click.echo(f'Hello {name}!')
  ```

- **`argparse`**: Python standard library for command-line argument parsing
  ```python
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('command', help='Command to execute')
  args = parser.parse_args()
  ```

#### 5. **Natural Language Processing**

**Current**: Custom prompt engineering
**Alternatives**:

- **`spaCy`**: Industrial-strength NLP library
  ```bash
  pip install spacy
  ```
  ```python
  import spacy
  nlp = spacy.load("en_core_web_sm")
  doc = nlp("find houses in belmont ca")
  ```

- **`nltk`**: Natural Language Toolkit
  ```bash
  pip install nltk
  ```
  ```python
  import nltk
  from nltk.tokenize import word_tokenize
  tokens = word_tokenize("find houses in belmont ca")
  ```

### Recommended Open Source Stack

For a fully open-source alternative to ManusAI, you could use:

```python
# Terminal Execution
import sh  # or plumbum

# Browser Automation
from selenium import webdriver
from selenium.webdriver.common.by import By

# AI Integration
from langchain.llms import OpenAI
from langchain.chains import LLMChain

# Command Parsing
import click

# Natural Language Processing
import spacy

# User Interface
from rich.console import Console
from rich.panel import Panel
```

### Comparison: Custom vs Open Source

| Component | Custom Implementation | Open Source Alternative | Pros | Cons |
|-----------|---------------------|------------------------|------|------|
| **Terminal Executor** | Custom safety checks, platform detection | `sh`, `plumbum` | More control, specific features | More maintenance, less tested |
| **Browser Executor** | Custom stealth, human-like behavior | `selenium`, `playwright` | Battle-tested, well-documented | Less customization, may need adaptation |
| **AI Integration** | Custom prompts, structured output | `langchain`, `transformers` | Framework features, community support | Learning curve, less control |
| **Command Parsing** | Custom regex patterns | `click`, `argparse` | Standard patterns, robust | Less flexible for AI-generated commands |

### Migration Strategy

To migrate from custom implementation to open source:

1. **Start with Browser Automation**: Replace custom `BrowserExecutor` with `selenium` or keep `playwright`
2. **Add LangChain**: Integrate `langchain` for better AI prompt management
3. **Enhance with spaCy**: Add NLP capabilities for better command understanding
4. **Keep Custom Parts**: Maintain custom safety checks and user confirmation logic

## Summary

The ManusAI system uses LLM control commands to bridge the gap between natural language requests and executable actions. The key innovation is the combination of:

1. **Structured AI prompts** that guide the LLM to generate parseable responses
2. **Flexible command extraction** that handles multiple response formats
3. **Adaptive execution** that uses AI to analyze and respond to changing conditions
4. **Safety mechanisms** that ensure user control and error recovery
5. **Human-like interaction** that mimics real user behavior to avoid detection
6. **Robust error handling** with fallback actions and timeout protection

This creates a powerful system where users can describe complex tasks in natural language, and the AI translates these into executable commands while maintaining safety and user control. 