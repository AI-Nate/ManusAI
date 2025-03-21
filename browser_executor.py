"""
Browser Executor module for ManusAI
Executes browser actions and captures screenshots
"""

import os
import time
import asyncio
import random
from playwright.async_api import async_playwright
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

# Helper functions for cookie generation
def new_date_string():
    """Generate a date string for cookies"""
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

def generate_random_id(length):
    """Generate a random ID for cookies"""
    import string
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def generate_bezier_curve(start_x, start_y, end_x, end_y, num_points=5):
    """
    Generate a bezier curve for mouse movement
    
    Args:
        start_x (float): Starting x coordinate
        start_y (float): Starting y coordinate
        end_x (float): Ending x coordinate
        end_y (float): Ending y coordinate
        num_points (int): Number of control points
        
    Returns:
        list: List of (x, y) coordinates along the curve
    """
    # Generate random control points
    control_points = []
    for i in range(num_points):
        # Create points that deviate from a straight line
        t = i / (num_points - 1)
        # Direct line coordinates
        line_x = start_x + t * (end_x - start_x)
        line_y = start_y + t * (end_y - start_y)
        
        # Add some randomness to the control points
        # More randomness in the middle, less at the ends
        randomness = 0.5 * min(abs(end_x - start_x), abs(end_y - start_y))
        randomness_factor = 4 * t * (1 - t)  # Peaks in the middle
        
        random_x = line_x + random.uniform(-randomness, randomness) * randomness_factor
        random_y = line_y + random.uniform(-randomness, randomness) * randomness_factor
        
        control_points.append((random_x, random_y))
    
    # Ensure the first and last points are exactly the start and end
    control_points[0] = (start_x, start_y)
    control_points[-1] = (end_x, end_y)
    
    # Generate more points along the curve for smoother movement
    curve_points = []
    steps = 20  # Number of steps along the curve
    
    for i in range(steps + 1):
        t = i / steps
        point = bezier_point(control_points, t)
        curve_points.append(point)
    
    return curve_points

def bezier_point(control_points, t):
    """
    Calculate a point along a bezier curve
    
    Args:
        control_points (list): List of control points (x, y)
        t (float): Parameter between 0 and 1
        
    Returns:
        tuple: (x, y) coordinates of the point
    """
    n = len(control_points) - 1
    x = 0
    y = 0
    
    for i, point in enumerate(control_points):
        # Bernstein polynomial
        coeff = binomial(n, i) * (t ** i) * ((1 - t) ** (n - i))
        x += coeff * point[0]
        y += coeff * point[1]
    
    return (x, y)

def binomial(n, k):
    """
    Calculate binomial coefficient (n choose k)
    
    Args:
        n (int): Total number of items
        k (int): Number of items to choose
        
    Returns:
        int: Binomial coefficient
    """
    if k < 0 or k > n:
        return 0
    if k == 0 or k == n:
        return 1
    
    result = 1
    for i in range(k):
        result = result * (n - i) // (i + 1)
    
    return result

class BrowserExecutor:
    """
    Executes browser actions and captures screenshots
    """
    
    def __init__(self):
        """Initialize the browser executor"""
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None
        self.is_initialized = False
        self.screenshots_dir = "screenshots"
        
        # Create screenshots directory if it doesn't exist
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
    
    async def initialize(self):
        """Initialize the browser"""
        if not self.is_initialized:
            try:
                self.playwright = await async_playwright().start()
                
                # Define common user agents
                user_agents = [
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
                ]
                
                # Choose a random user agent
                user_agent = random.choice(user_agents)
                
                # Define common viewport sizes
                viewport_sizes = [
                    {"width": 1920, "height": 1080},  # Full HD
                    {"width": 1680, "height": 1050},  # Common laptop size
                    {"width": 1440, "height": 900},   # MacBook Pro 15"
                    {"width": 1366, "height": 768}    # Common laptop size
                ]
                
                # Choose a random viewport size
                viewport = random.choice(viewport_sizes)
                
                # Enhanced browser launch arguments to bypass detection
                browser_args = [
                    '--disable-blink-features=AutomationControlled',  # Hide automation
                    '--disable-features=IsolateOrigins,site-per-process',  # Disable site isolation
                    '--disable-site-isolation-trials',  # Disable site isolation trials
                    '--disable-web-security',  # Disable CORS restrictions
                    '--disable-setuid-sandbox',
                    '--no-sandbox',
                    '--disable-infobars',
                    '--window-size=1920,1080',
                    '--ignore-certificate-errors',
                    '--ignore-certificate-errors-spki-list',
                    '--disable-extensions',
                    '--disable-default-apps',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--disable-notifications',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-breakpad',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-features=TranslateUI,BlinkGenPropertyTrees',
                    '--disable-ipc-flooding-protection',
                    '--disable-renderer-backgrounding',
                    '--enable-features=NetworkService,NetworkServiceInProcess',
                    '--force-color-profile=srgb',
                    '--metrics-recording-only',
                    '--mute-audio',
                    '--hide-scrollbars'
                ]
                
                # Launch browser with enhanced stealth settings
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=browser_args
                )
                
                # Create context with custom settings
                self.context = await self.browser.new_context(
                    user_agent=user_agent,
                    viewport=viewport,
                    locale="en-US",
                    timezone_id="America/New_York",
                    permissions=["geolocation"],
                    geolocation={"latitude": 40.7128, "longitude": -74.0060},  # New York City coordinates
                    color_scheme="no-preference",
                    bypass_csp=True,  # Bypass Content Security Policy
                    extra_http_headers={
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Connection": "keep-alive",
                        "sec-ch-ua": '"Chromium";v="122", "Google Chrome";v="122", "Not:A-Brand";v="99"',
                        "sec-ch-ua-mobile": "?0",
                        "sec-ch-ua-platform": '"macOS"',
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                        "Cache-Control": "max-age=0"
                    }
                )
                
                # Add JavaScript to modify navigator properties to avoid detection
                await self.context.add_init_script("""
                    // Overwrite the 'webdriver' property to make it undefined
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // Add language plugins to appear more like a real browser
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en', 'es']
                    });
                    
                    // Add a fake notification permission
                    if (navigator.permissions) {
                        navigator.permissions.query = (function(originalQuery) {
                            return function(parameters) {
                                if (parameters.name === 'notifications') {
                                    return Promise.resolve({state: "granted", onchange: null});
                                }
                                return originalQuery.call(this, parameters);
                            }
                        })(navigator.permissions.query);
                    }
                    
                    // Modify plugins to appear more like a real browser
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => {
                            return [
                                {
                                    0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                                    name: "PDF Viewer",
                                    filename: "internal-pdf-viewer",
                                    description: "Portable Document Format",
                                    length: 1
                                },
                                {
                                    0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                                    name: "Chrome PDF Viewer",
                                    filename: "internal-pdf-viewer",
                                    description: "Portable Document Format",
                                    length: 1
                                }
                            ];
                        }
                    });
                    
                    // Add a fake user-agent client hints API
                    if (!navigator.userAgentData) {
                        navigator.userAgentData = {
                            brands: [
                                {brand: 'Chromium', version: '122'},
                                {brand: 'Google Chrome', version: '122'},
                                {brand: 'Not:A-Brand', version: '99'}
                            ],
                            mobile: false,
                            platform: 'macOS'
                        };
                        navigator.userAgentData.getHighEntropyValues = function() {
                            return Promise.resolve({
                                architecture: 'x86',
                                bitness: '64',
                                brands: this.brands,
                                mobile: false,
                                model: '',
                                platform: 'macOS',
                                platformVersion: '10.15.7',
                                uaFullVersion: '122.0.0.0'
                            });
                        };
                    }
                    
                    // Override the chrome object to appear more like a real browser
                    if (window.chrome === undefined) {
                        window.chrome = {};
                    }
                    if (!window.chrome.runtime) {
                        window.chrome.runtime = {};
                    }
                    
                    // Add random fingerprint canvas noise
                    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                    HTMLCanvasElement.prototype.toDataURL = function(type) {
                        if (this.width > 16 && this.height > 16) {
                            const context = this.getContext('2d');
                            const imageData = context.getImageData(0, 0, this.width, this.height);
                            const pixels = imageData.data;
                            for (let i = 0; i < pixels.length; i += 4) {
                                // Add slight random noise to pixel data
                                pixels[i] = pixels[i] + (Math.random() < 0.1 ? 1 : 0);
                                pixels[i+1] = pixels[i+1] + (Math.random() < 0.1 ? 1 : 0);
                                pixels[i+2] = pixels[i+2] + (Math.random() < 0.1 ? 1 : 0);
                            }
                            context.putImageData(imageData, 0, 0);
                        }
                        return originalToDataURL.apply(this, arguments);
                    };
                """)
                
                # Create a new page
                self.page = await self.context.new_page()
                
                # Add random mouse movements to simulate human behavior
                await self._add_random_mouse_movements()
                
                # Add cookies to simulate a returning user
                await self._add_common_cookies()
                
                self.is_initialized = True
                console.print(f"[green]Browser initialized successfully with user agent: {user_agent[:30]}...[/green]")
                console.print(f"[green]Viewport size: {viewport['width']}x{viewport['height']}[/green]")
                return True
            except Exception as e:
                console.print(f"[bold red]Error initializing browser:[/bold red] {str(e)}")
                return False
        return True
    
    async def _add_random_mouse_movements(self):
        """Add random mouse movements to simulate human behavior"""
        try:
            # Get the viewport size
            viewport = await self.page.evaluate("""
                () => {
                    return {
                        width: window.innerWidth,
                        height: window.innerHeight
                    }
                }
            """)
            
            # Generate 3-5 random points within the viewport
            num_points = random.randint(3, 5)
            for _ in range(num_points):
                x = random.randint(0, viewport['width'])
                y = random.randint(0, viewport['height'])
                
                # Move to the random point with random steps
                await self.page.mouse.move(x, y, steps=random.randint(3, 8))
                
                # Add a small delay between movements
                await asyncio.sleep(random.uniform(0.1, 0.3))
        except Exception as e:
            console.print(f"[yellow]Error adding random mouse movements: {str(e)}[/yellow]")
            # Non-critical error, so we continue
    
    async def _add_common_cookies(self):
        """Add common cookies to simulate a returning user"""
        try:
            # Add some common cookies
            await self.context.add_cookies([
                {
                    "name": "OptanonAlertBoxClosed",
                    "value": new_date_string(),
                    "domain": ".redfin.com",
                    "path": "/"
                },
                {
                    "name": "OptanonConsent",
                    "value": "isGpcEnabled=0&datestamp=" + new_date_string() + "&version=6.26.0",
                    "domain": ".redfin.com",
                    "path": "/"
                },
                {
                    "name": "RF_BROWSER_ID",
                    "value": generate_random_id(32),
                    "domain": ".redfin.com",
                    "path": "/"
                },
                {
                    "name": "RF_VISITED",
                    "value": "true",
                    "domain": ".redfin.com",
                    "path": "/"
                }
            ])
        except Exception as e:
            console.print(f"[yellow]Error adding cookies: {str(e)}[/yellow]")
            # Non-critical error, so we continue
    
    async def close(self):
        """Close the browser"""
        if self.is_initialized:
            try:
                await self.context.close()
                await self.browser.close()
                await self.playwright.stop()
                self.is_initialized = False
                console.print("[green]Browser closed successfully.[/green]")
            except Exception as e:
                console.print(f"[bold red]Error closing browser:[/bold red] {str(e)}")
    
    async def navigate(self, url):
        """
        Navigate to a URL
        
        Args:
            url (str): The URL to navigate to
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized:
            if not await self.initialize():
                return False
        
        try:
            await self.page.goto(url)
            current_url = self.page.url
            console.print(f"[green]Navigated to:[/green] {current_url}")
            
            # Take a screenshot
            screenshot_path = await self._take_screenshot("navigate")
            if screenshot_path:
                console.print(f"[green]Screenshot saved to:[/green] {screenshot_path}")
            
            return True
        except Exception as e:
            console.print(f"[bold red]Error navigating to {url}:[/bold red] {str(e)}")
            return False
    
    async def search(self, query, selector="input[type='search'], input[name='q'], input[placeholder*='search' i], input[aria-label*='search' i], input.search-input, .search-box input, .searchbox input"):
        """
        Search for a query using the search box
        
        Args:
            query (str): The search query
            selector (str): CSS selector for the search input field
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized:
            if not await self.initialize():
                return False
        
        try:
            console.print(f"[yellow]Looking for search input with selector:[/yellow] {selector}")
            
            # First, take a screenshot to see the current state
            await self._take_screenshot("before_search")
            console.print("[green]Took screenshot of current page before search[/green]")
            
            # Get all input elements on the page for debugging
            all_inputs = await self.page.evaluate("""
                () => {
                    const inputs = document.querySelectorAll('input');
                    return Array.from(inputs).map(input => {
                        return {
                            type: input.type,
                            name: input.name,
                            id: input.id,
                            placeholder: input.placeholder,
                            className: input.className,
                            isVisible: input.offsetWidth > 0 && input.offsetHeight > 0,
                            value: input.value
                        };
                    });
                }
            """)
            
            console.print(f"[yellow]Found {len(all_inputs)} input elements on the page[/yellow]")
            for i, input_el in enumerate(all_inputs):
                if i < 10:  # Limit to first 10 to avoid overwhelming output
                    console.print(f"Input #{i+1}: type={input_el['type']}, name={input_el['name']}, id={input_el['id']}, placeholder={input_el['placeholder']}, visible={input_el['isVisible']}")
            
            # Add a random delay before starting to interact with the page
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            # Try multiple approaches to find and interact with the search bar
            
            # Approach 1: Use the provided selector
            try:
                console.print("[yellow]Approach 1: Using the provided selector[/yellow]")
                await self.page.wait_for_selector(selector, timeout=5000)
                search_input = await self.page.query_selector(selector)
                
                if search_input and await search_input.is_visible():
                    console.print("[green]Found search input using provided selector[/green]")
                    
                    # Move to the element in a human-like manner
                    await self._human_like_move(search_input)
                    
                    # Click the element
                    await search_input.click()
                    
                    # Add a small delay after clicking
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                    
                    # Type the query in a human-like manner
                    await self._human_like_type(search_input, query)
                    
                    # Press Enter
                    await search_input.press("Enter")
                    
                    # Wait for navigation to complete
                    await self.page.wait_for_load_state("networkidle", timeout=15000)
                    
                    # Take a screenshot after search
                    await self._take_screenshot("after_search_approach1")
                    console.print(f"[green]Searched for:[/green] {query} (Approach 1)")
                    return True
                else:
                    console.print("[yellow]Search input found but not visible or interactive[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Approach 1 failed: {str(e)}[/yellow]")
            
            # Approach 2: Look for search-related elements
            try:
                console.print("[yellow]Approach 2: Looking for search-related elements[/yellow]")
                
                # Common search selectors for popular websites
                site_specific_selectors = {
                    "zillow.com": [
                        "input[placeholder*='Address, School, City, Zip or Neighborhood']",
                        "input[placeholder*='Enter an address, neighborhood, city, or ZIP code']",
                        "input[data-testid='search-box-input']",
                        "input[id*='search']",
                        ".search-input",
                        "[data-testid='search-box-input']"
                    ],
                    "redfin.com": [
                        "input[placeholder*='City, Address, School, Agent, ZIP']",
                        "input[placeholder*='Address, City, School, Agent, ZIP']",
                        "input[data-testid='search-input']",
                        "input[id='search-box-input']",
                        ".search-input-box"
                    ],
                    "google.com": [
                        "input[name='q']",
                        "textarea[name='q']",
                        "input[title='Search']"
                    ]
                }
                
                # Determine which site we're on
                current_url = self.page.url
                site_selectors = []
                for site, selectors in site_specific_selectors.items():
                    if site in current_url:
                        site_selectors = selectors
                        console.print(f"[green]Detected site: {site}[/green]")
                        break
                
                # If we have site-specific selectors, try them
                if site_selectors:
                    for site_selector in site_selectors:
                        try:
                            console.print(f"[yellow]Trying site-specific selector: {site_selector}[/yellow]")
                            search_input = await self.page.query_selector(site_selector)
                            
                            if search_input and await search_input.is_visible():
                                console.print(f"[green]Found search input using site-specific selector: {site_selector}[/green]")
                                
                                # Move to the element in a human-like manner
                                await self._human_like_move(search_input)
                                
                                # Click the element
                                await search_input.click()
                                
                                # Add a small delay after clicking
                                await asyncio.sleep(random.uniform(0.3, 0.8))
                                
                                # Type the query in a human-like manner
                                await self._human_like_type(search_input, query)
                                
                                # Press Enter
                                await search_input.press("Enter")
                                
                                # Wait for navigation to complete
                                await self.page.wait_for_load_state("networkidle", timeout=15000)
                                
                                # Take a screenshot after search
                                await self._take_screenshot("after_search_approach2")
                                console.print(f"[green]Searched for:[/green] {query} (Approach 2)")
                                return True
                        except Exception as e:
                            console.print(f"[yellow]Site-specific selector failed: {str(e)}[/yellow]")
                
                # If site-specific selectors didn't work, try generic approach
                search_related_elements = await self.page.query_selector_all("input[type='search'], input[type='text'], input:not([type]), .search, .searchbox, .search-box, .search-input, [role='search'] input")
                
                for element in search_related_elements:
                    try:
                        if await element.is_visible():
                            console.print("[green]Found visible search-related element[/green]")
                            await element.click()
                            await element.fill("")
                            await element.type(query, delay=100)
                            await element.press("Enter")
                            
                            # Wait for navigation to complete
                            await self.page.wait_for_load_state("networkidle", timeout=15000)
                            
                            # Take a screenshot after search
                            await self._take_screenshot("after_search_approach2_generic")
                            console.print(f"[green]Searched for:[/green] {query} (Approach 2 - generic)")
                            return True
                    except Exception as e:
                        console.print(f"[yellow]Generic search element interaction failed: {str(e)}[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Approach 2 failed: {str(e)}[/yellow]")
            
            # Approach 3: Look for search buttons first, then find related input
            try:
                console.print("[yellow]Approach 3: Looking for search buttons first[/yellow]")
                search_buttons = await self.page.query_selector_all("button[aria-label*='search' i], button.search-button, button.searchButton, [data-testid='search-button'], .search-icon")
                
                for button in search_buttons:
                    try:
                        if await button.is_visible():
                            console.print("[green]Found visible search button[/green]")
                            
                            # Move to the button in a human-like manner
                            await self._human_like_move(button)
                            
                            # Click the search button to activate the search box
                            await button.click()
                            
                            # Wait a moment for any animations to complete
                            await asyncio.sleep(random.uniform(1.0, 1.5))
                            
                            # Look for input elements that might have appeared
                            search_inputs = await self.page.query_selector_all("input[type='search'], input[type='text'], input:not([type])")
                            
                            for input_el in search_inputs:
                                try:
                                    if await input_el.is_visible():
                                        console.print("[green]Found visible input after clicking search button[/green]")
                                        
                                        # Move to the input in a human-like manner
                                        await self._human_like_move(input_el)
                                        
                                        # Type the query in a human-like manner
                                        await self._human_like_type(input_el, query)
                                        
                                        # Press Enter
                                        await input_el.press("Enter")
                                        
                                        # Wait for navigation to complete
                                        await self.page.wait_for_load_state("networkidle", timeout=15000)
                                        
                                        # Take a screenshot after search
                                        await self._take_screenshot("after_search_approach3")
                                        console.print(f"[green]Searched for:[/green] {query} (Approach 3)")
                                        return True
                                except Exception as e:
                                    console.print(f"[yellow]Input interaction after button click failed: {str(e)}[/yellow]")
                    except Exception as e:
                        console.print(f"[yellow]Search button interaction failed: {str(e)}[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Approach 3 failed: {str(e)}[/yellow]")
            
            # Approach 4: Try direct URL navigation with search query
            try:
                console.print("[yellow]Approach 4: Using direct URL navigation with search query[/yellow]")
                current_url = self.page.url
                search_query_encoded = query.replace(" ", "+")
                
                # Construct search URL based on the current site
                search_url = None
                if "zillow.com" in current_url:
                    search_url = f"https://www.zillow.com/homes/{search_query_encoded}_rb/"
                elif "redfin.com" in current_url:
                    search_url = f"https://www.redfin.com/city/{search_query_encoded}"
                elif "google.com" in current_url:
                    search_url = f"https://www.google.com/search?q={search_query_encoded}"
                
                if search_url:
                    # Add a random delay before navigation
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    
                    console.print(f"[yellow]Navigating directly to search URL: {search_url}[/yellow]")
                    await self.page.goto(search_url)
                    
                    # Wait for navigation to complete
                    await self.page.wait_for_load_state("networkidle", timeout=15000)
                    
                    # Take a screenshot after direct navigation
                    await self._take_screenshot("after_search_approach4")
                    console.print(f"[green]Navigated to search URL for:[/green] {query} (Approach 4)")
                    return True
                else:
                    console.print("[yellow]Could not construct a search URL for this site[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Approach 4 failed: {str(e)}[/yellow]")
            
            # If all approaches failed, return failure
            console.print(f"[bold red]All search approaches failed for query: {query}[/bold red]")
            return False
            
        except Exception as e:
            console.print(f"[bold red]Error searching for {query}:[/bold red] {str(e)}")
            return False
    
    async def click(self, selector, selector_type="css"):
        """
        Click on an element
        
        Args:
            selector (str): CSS selector or XPath
            selector_type (str): Type of selector ('css' or 'xpath')
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized:
            if not await self.initialize():
                return False
        
        try:
            # Add a small random delay before clicking (human-like behavior)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Find the element
            if selector_type.lower() == "xpath":
                element = await self.page.wait_for_selector(selector, state="visible", timeout=5000)
            else:
                element = await self.page.wait_for_selector(selector, state="visible", timeout=5000)
            
            if not element:
                console.print(f"[bold yellow]Element not found:[/bold yellow] {selector}")
                return False
            
            # Get element position for mouse movement
            bounding_box = await element.bounding_box()
            if not bounding_box:
                console.print(f"[bold yellow]Could not get element position:[/bold yellow] {selector}")
                return False
            
            # Calculate target position (center of element)
            target_x = bounding_box["x"] + bounding_box["width"] / 2
            target_y = bounding_box["y"] + bounding_box["height"] / 2
            
            # Get current mouse position (or use a default if not available)
            current_x, current_y = 0, 0  # Default starting position
            
            # Generate random control points for a curved mouse movement
            control_points = generate_bezier_curve(
                current_x, current_y, target_x, target_y, 
                random.randint(3, 6)  # Random number of control points
            )
            
            # Move mouse along the curve
            for point in control_points:
                await self.page.mouse.move(point[0], point[1])
                await asyncio.sleep(random.uniform(0.01, 0.03))  # Small random delay between movements
            
            # Add a small delay before clicking (human-like behavior)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Click the element
            await element.click()
            
            # Wait for navigation or network idle
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            
            console.print(f"[green]Clicked element:[/green] {selector}")
            return True
            
        except Exception as e:
            console.print(f"[bold red]Error clicking element:[/bold red] {str(e)}")
            return False

    async def click_element_by_text(self, text):
        """
        Click on an element containing specific text
        
        Args:
            text (str): Text to search for
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized:
            if not await self.initialize():
                return False
        
        try:
            # Create an XPath selector that looks for elements containing the text
            xpath = f"//*[contains(text(), '{text}')]"
            
            # Find the element
            element = await self.page.wait_for_selector(xpath, state="visible", timeout=5000)
            
            if not element:
                console.print(f"[bold yellow]Element with text not found:[/bold yellow] {text}")
                return False
            
            # Add a small random delay before clicking (human-like behavior)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Click the element
            await element.click()
            
            # Wait for navigation or network idle
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            
            console.print(f"[green]Clicked element with text:[/green] {text}")
            return True
            
        except Exception as e:
            console.print(f"[bold red]Error clicking element with text:[/bold red] {str(e)}")
            return False

    async def fill_input(self, selector, value, selector_type="css"):
        """
        Fill an input field
        
        Args:
            selector (str): CSS selector or XPath
            value (str): Value to fill
            selector_type (str): Type of selector ('css' or 'xpath')
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized:
            if not await self.initialize():
                return False
        
        try:
            # Find the element
            if selector_type.lower() == "xpath":
                element = await self.page.wait_for_selector(selector, state="visible", timeout=5000)
            else:
                element = await self.page.wait_for_selector(selector, state="visible", timeout=5000)
            
            if not element:
                console.print(f"[bold yellow]Input element not found:[/bold yellow] {selector}")
                return False
            
            # Click the input first (to focus it)
            await element.click()
            
            # Clear the input
            await element.fill("")
            
            # Type the value with random delays between keystrokes (human-like behavior)
            for char in value:
                await element.type(char, delay=random.uniform(50, 150))
                await asyncio.sleep(random.uniform(0.01, 0.05))
            
            # Take a screenshot after filling
            try:
                await self._take_screenshot("after_fill")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not take screenshot after filling: {str(e)}[/yellow]")
            
            console.print(f"[green]Filled input:[/green] {selector} with value: {value}")
            return True
            
        except Exception as e:
            console.print(f"[bold red]Error filling input:[/bold red] {str(e)}")
            return False

    async def capture_page_state(self):
        """
        Capture the current state of the page
        
        Returns:
            dict: Page state information
        """
        if not self.is_initialized:
            if not await self.initialize():
                return None
        
        try:
            # Take a screenshot (optional)
            try:
                screenshot_path = await self._take_screenshot("page_state")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not take screenshot: {str(e)}[/yellow]")
                screenshot_path = None
            
            # Get the current URL and title
            url = self.page.url
            title = await self.page.title()
            
            # Extract visible text elements
            visible_elements = await self.page.evaluate("""
                () => {
                    const textElements = [];
                    const elements = document.querySelectorAll('h1, h2, h3, h4, h5, h6, p, span, a, button, label, div');
                    
                    elements.forEach(el => {
                        const text = el.innerText || el.textContent;
                        if (text && text.trim() && el.offsetParent !== null) {
                            textElements.push({
                                tagName: el.tagName.toLowerCase(),
                                text: text.trim(),
                                id: el.id,
                                classes: el.className
                            });
                        }
                    });
                    
                    return textElements;
                }
            """)
            
            # Extract clickable elements
            clickable_elements = await self.page.evaluate("""
                () => {
                    const clickableElements = [];
                    const elements = document.querySelectorAll('a, button, [role="button"], [onclick], input[type="submit"], input[type="button"]');
                    
                    elements.forEach(el => {
                        const text = el.innerText || el.textContent || el.value;
                        if (el.offsetParent !== null) {
                            clickableElements.push({
                                tagName: el.tagName.toLowerCase(),
                                text: text ? text.trim() : '',
                                id: el.id,
                                classes: el.className,
                                href: el.href || ''
                            });
                        }
                    });
                    
                    return clickableElements;
                }
            """)
            
            # Extract form elements
            form_elements = await self.page.evaluate("""
                () => {
                    const forms = [];
                    const formElements = document.querySelectorAll('form');
                    
                    formElements.forEach(form => {
                        const inputs = [];
                        const formInputs = form.querySelectorAll('input, select, textarea');
                        
                        formInputs.forEach(input => {
                            if (input.offsetParent !== null) {
                                inputs.push({
                                    type: input.type || 'text',
                                    name: input.name,
                                    id: input.id,
                                    placeholder: input.placeholder || '',
                                    value: input.value || '',
                                    isRequired: input.required
                                });
                            }
                        });
                        
                        if (inputs.length > 0) {
                            forms.push(inputs);
                        }
                    });
                    
                    return forms;
                }
            """)
            
            # Compile the page state
            page_state = {
                'url': url,
                'title': title,
                'screenshot': screenshot_path,
                'visible_elements': visible_elements,
                'clickable_elements': clickable_elements,
                'form_elements': form_elements
            }
            
            console.print(f"[green]Captured page state:[/green] {title} ({url})")
            return page_state
            
        except Exception as e:
            console.print(f"[bold red]Error capturing page state:[/bold red] {str(e)}")
            return None

    async def analyze_page_for_next_action(self, goal_description):
        """
        Analyze the current page and suggest the next action based on the goal using AI
        
        Args:
            goal_description (str): Description of what the user is trying to achieve
            
        Returns:
            dict: Suggested next action
        """
        if not self.is_initialized:
            if not await self.initialize():
                return None
        
        try:
            # Capture the current page state
            page_state = await self.capture_page_state()
            if not page_state:
                return None
            
            # Simplify the page state for analysis
            simplified_state = {
                'url': page_state['url'],
                'title': page_state['title'],
                'visible_text': [item['text'] for item in page_state['visible_elements']],
                'clickable_elements': [
                    {
                        'text': item['text'],
                        'tag': item['tagName'],
                        'id': item['id'],
                        'classes': item['classes'],
                        'href': item.get('href', '')
                    }
                    for item in page_state['clickable_elements']
                ],
                'form_inputs': []
            }
            
            for form in page_state['form_elements']:
                for input_el in form:
                    simplified_state['form_inputs'].append({
                        'type': input_el['type'],
                        'name': input_el['name'],
                        'id': input_el['id'],
                        'placeholder': input_el['placeholder'],
                        'value': input_el['value'],
                        'required': input_el['isRequired']
                    })
            
            # Extract important information based on the current website
            current_url = simplified_state['url']
            current_domain = ""
            import re
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', current_url)
            if domain_match:
                current_domain = domain_match.group(1)
            
            # Format the page state as a string for the AI
            page_state_text = f"""
Current Page Analysis:
URL: {simplified_state['url']}
Title: {simplified_state['title']}
Domain: {current_domain}

"""
            
            # Add general page content
            page_state_text += "Visible Text Elements (first 20):\n"
            page_state_text += ", ".join(simplified_state['visible_text'][:20]) + "\n\n"
            
            page_state_text += "Clickable Elements (first 10):\n"
            page_state_text += ", ".join([f"{el['text']} ({el['tag']})" for el in simplified_state['clickable_elements'][:10]]) + "\n\n"
            
            page_state_text += "Form Inputs (first 5):\n"
            page_state_text += ", ".join([f"{el['type']} {el['id'] or el['name']} - {el['placeholder']}" for el in simplified_state['form_inputs'][:5]]) + "\n\n"
            
            # Import the AI response function from utils
            from utils import get_ai_page_analysis
            
            # Get AI analysis of the page
            console.print("[yellow]Sending page analysis to AI for next action recommendation...[/yellow]")
            
            # Call the function directly (not awaiting it since it's not async)
            next_action = get_ai_page_analysis(page_state_text, goal_description)
            
            if next_action and isinstance(next_action, dict) and 'action_type' in next_action:
                console.print(f"[green]AI suggested next action:[/green] {next_action.get('description', 'No description')}")
                return next_action
            else:
                console.print("[yellow]AI did not provide a valid next action. Using fallback action.[/yellow]")
                # Fallback to a simple scroll action if AI doesn't provide a valid action
                return {
                    'action_type': 'scroll',
                    'direction': 'down',
                    'distance': 500,
                    'description': "Scroll down to see more content (fallback action)"
                }
            
        except Exception as e:
            console.print(f"[bold red]Error analyzing page:[/bold red] {str(e)}")
            import traceback
            console.print(traceback.format_exc())
            # Provide a fallback action
            return {
                'action_type': 'scroll',
                'direction': 'down',
                'distance': 500,
                'description': "Scroll down to see more content (fallback after error)"
            }

    async def _human_like_type(self, element, text, min_delay=50, max_delay=150):
        """
        Type text in a human-like manner with random delays between keystrokes
        
        Args:
            element: The element to type into
            text (str): The text to type
            min_delay (int): Minimum delay in milliseconds between keystrokes
            max_delay (int): Maximum delay in milliseconds between keystrokes
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Clear the input field first
            await element.fill("")
            
            # Type each character with a random delay
            for char in text:
                # Random delay between keystrokes (convert ms to seconds)
                delay = random.randint(min_delay, max_delay) / 1000
                await asyncio.sleep(delay)
                
                # Type the character
                await element.type(char, delay=delay * 1000)
                
                # Occasionally add a longer pause as if thinking
                if random.random() < 0.1:  # 10% chance
                    thinking_delay = random.uniform(0.5, 1.2)  # 500-1200ms pause
                    await asyncio.sleep(thinking_delay)
            
            # Add a small delay before pressing Enter
            await asyncio.sleep(random.uniform(0.3, 0.7))
            
            return True
        except Exception as e:
            console.print(f"[bold red]Error during human-like typing:[/bold red] {str(e)}")
            return False

    async def _human_like_move(self, target_element):
        """
        Move to an element in a human-like manner with slight randomness
        
        Args:
            target_element: The element to move to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the bounding box of the element
            box = await target_element.bounding_box()
            if not box:
                return False
            
            # Calculate a random point within the element
            x = box['x'] + random.uniform(0.3, 0.7) * box['width']
            y = box['y'] + random.uniform(0.3, 0.7) * box['height']
            
            # Move to the element with a human-like motion
            await self.page.mouse.move(x, y, steps=random.randint(5, 10))
            
            # Small delay before clicking
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            return True
        except Exception as e:
            console.print(f"[bold red]Error during human-like mouse movement:[/bold red] {str(e)}")
            return False

    async def scroll(self, direction="down", distance=500):
        """
        Scroll the page
        
        Args:
            direction (str): The direction to scroll ('up', 'down', 'left', 'right')
            distance (int): The distance to scroll in pixels
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized:
            if not await self.initialize():
                return False
        
        try:
            # Determine the scroll direction
            x_scroll = 0
            y_scroll = 0
            
            if direction.lower() == "down":
                y_scroll = distance
            elif direction.lower() == "up":
                y_scroll = -distance
            elif direction.lower() == "right":
                x_scroll = distance
            elif direction.lower() == "left":
                x_scroll = -distance
            
            # Add a random delay before scrolling
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Scroll in a more human-like way - in smaller increments with pauses
            steps = random.randint(3, 6)  # Number of scroll steps
            x_step = x_scroll / steps
            y_step = y_scroll / steps
            
            for i in range(steps):
                # Execute a partial scroll
                await self.page.evaluate(f"window.scrollBy({x_step}, {y_step})")
                
                # Add a small random delay between scroll steps
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # Occasionally pause a bit longer as if reading
                if random.random() < 0.3:  # 30% chance
                    await asyncio.sleep(random.uniform(0.5, 1.0))
            
            console.print(f"[green]Scrolled {direction}:[/green] {distance} pixels")
            return True
            
        except Exception as e:
            console.print(f"[bold red]Error scrolling {direction}:[/bold red] {str(e)}")
            return False

    async def extract_text(self, selector, selector_type="css"):
        """
        Extract text from an element
        
        Args:
            selector (str): CSS selector or XPath
            selector_type (str): Type of selector ('css' or 'xpath')
            
        Returns:
            str: The extracted text or None if unsuccessful
        """
        if not self.is_initialized:
            if not await self.initialize():
                return None
        
        try:
            # Find the element
            if selector_type.lower() == "xpath":
                element = await self.page.wait_for_selector(selector, state="visible", timeout=5000)
            else:
                element = await self.page.wait_for_selector(selector, state="visible", timeout=5000)
            
            if not element:
                console.print(f"[bold yellow]Element not found for text extraction:[/bold yellow] {selector}")
                return None
            
            # Extract the text
            text = await element.text_content()
            
            console.print(f"[green]Extracted text:[/green] {text[:100]}...")
            return text
            
        except Exception as e:
            console.print(f"[bold red]Error extracting text:[/bold red] {str(e)}")
            return None

    async def execute_action(self, action):
        """
        Execute a browser action
        
        Args:
            action (dict): Action dictionary with action_type and parameters
            
        Returns:
            str: Result of the action
        """
        if not self.is_initialized:
            if not await self.initialize():
                return "Failed to initialize browser."
        
        action_type = action.get('action_type', '').lower()
        
        try:
            # Take a screenshot before the action
            try:
                screenshot_name = f"before_{action_type}"
                await self._take_screenshot(screenshot_name)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not take screenshot before action: {str(e)}[/yellow]")
            
            if action_type == 'navigate':
                url = action.get('url', '')
                if url:
                    # Add a message about direct navigation
                    if "redfin.com" in url or "zillow.com" in url or "apartments.com" in url or "trulia.com" in url:
                        console.print(f"[bold green]Directly navigating to {url} for real estate search[/bold green]")
                    elif "linkedin.com" in url or "indeed.com" in url or "glassdoor.com" in url:
                        console.print(f"[bold green]Directly navigating to {url} for job search[/bold green]")
                    elif "amazon.com" in url or "ebay.com" in url or "walmart.com" in url:
                        console.print(f"[bold green]Directly navigating to {url} for shopping search[/bold green]")
                    else:
                        console.print(f"[bold green]Directly navigating to {url}[/bold green]")
                        
                    await self.navigate(url)
                    # Take a screenshot after navigation
                    try:
                        await self._take_screenshot("navigate")
                        console.print(f"Screenshot saved to: screenshots/{time.strftime('%Y%m%d-%H%M%S')}_navigate.png")
                    except Exception as e:
                        console.print(f"[yellow]Warning: Could not take screenshot after navigation: {str(e)}[/yellow]")
                    return f"Navigated to: {url}"
                else:
                    return "Error: No URL provided for navigation"
                
            elif action_type == 'click':
                selector = action.get('selector')
                text = action.get('text')
                selector_type = action.get('selector_type', 'css')
                
                if selector:
                    await self.click(selector, selector_type=selector_type)
                    # Take a screenshot after clicking
                    try:
                        await self._take_screenshot("click")
                    except Exception as e:
                        console.print(f"[yellow]Warning: Could not take screenshot after click: {str(e)}[/yellow]")
                    return f"Clicked element with selector: {selector}"
                elif text:
                    await self.click_element_by_text(text)
                    # Take a screenshot after clicking
                    try:
                        await self._take_screenshot("click_text")
                    except Exception as e:
                        console.print(f"[yellow]Warning: Could not take screenshot after click: {str(e)}[/yellow]")
                    return f"Clicked element with text: {text}"
                else:
                    return "Error: No selector or text provided for click action"
                
            elif action_type == 'input':
                selector = action.get('selector')
                value = action.get('value', '')
                selector_type = action.get('selector_type', 'css')
                
                # Try different selectors for search boxes if no specific selector is provided
                if not selector:
                    console.print("[yellow]No selector provided for input action. Trying common search box selectors...[/yellow]")
                    
                    # Common search box selectors
                    search_selectors = [
                        "input[type='search']",
                        "input[name='search']",
                        "input[placeholder*='search' i]",
                        "input[placeholder*='find' i]",
                        "input[placeholder*='location' i]",
                        "input[placeholder*='address' i]",
                        "input[placeholder*='city' i]",
                        "input[placeholder*='where' i]",
                        "input[aria-label*='search' i]",
                        "input.search-input",
                        ".search-box input",
                        ".searchbox input",
                        "[data-rf-test-id='search-box-input']",
                        "[data-rf-test-name='search-box-input']",
                        "input#search-box-input"
                    ]
                    
                    # Try each selector
                    for search_selector in search_selectors:
                        try:
                            console.print(f"[yellow]Trying selector: {search_selector}[/yellow]")
                            element = await self.page.wait_for_selector(search_selector, state="visible", timeout=1000)
                            if element:
                                console.print(f"[green]Found search box with selector: {search_selector}[/green]")
                                await self.fill_input(search_selector, value)
                                
                                # Try to press Enter after filling the input
                                try:
                                    await self.page.keyboard.press("Enter")
                                    console.print("[green]Pressed Enter after filling search box[/green]")
                                except Exception as e:
                                    console.print(f"[yellow]Error pressing Enter: {str(e)}[/yellow]")
                                
                                # Take a screenshot after filling input
                                try:
                                    await self._take_screenshot("input_search")
                                except Exception as e:
                                    console.print(f"[yellow]Warning: Could not take screenshot after input: {str(e)}[/yellow]")
                                
                                return f"Filled search box with value: {value}"
                        except Exception as e:
                            console.print(f"[yellow]Selector {search_selector} not found: {str(e)}[/yellow]")
                    
                    # If we get here, none of the selectors worked
                    return f"Error: Could not find a search box to fill with value: {value}"
                
                # If a specific selector is provided, use it
                if selector:
                    await self.fill_input(selector, value, selector_type=selector_type)
                    
                    # Try to press Enter after filling the input
                    try:
                        await self.page.keyboard.press("Enter")
                        console.print("[green]Pressed Enter after filling input[/green]")
                    except Exception as e:
                        console.print(f"[yellow]Error pressing Enter: {str(e)}[/yellow]")
                    
                    # Take a screenshot after filling input
                    try:
                        await self._take_screenshot("input_selector")
                    except Exception as e:
                        console.print(f"[yellow]Warning: Could not take screenshot after input: {str(e)}[/yellow]")
                    
                    return f"Filled input {selector} with value: {value}"
                else:
                    return "Error: No selector provided for input action"
                
            elif action_type == 'scroll':
                direction = action.get('direction', 'down')
                distance = action.get('distance', 500)
                
                await self.scroll(direction, distance)
                
                # Take a screenshot after scrolling
                try:
                    await self._take_screenshot("scroll")
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not take screenshot after scroll: {str(e)}[/yellow]")
                
                return f"Scrolled {direction} by {distance} pixels"
                
            elif action_type == 'wait':
                duration = action.get('duration', 2)
                
                await asyncio.sleep(duration)
                return f"Waited for {duration} seconds"
                
            elif action_type == 'search':
                query = action.get('query', '')
                selector = action.get('selector', '')
                selector_type = action.get('selector_type', 'css')
                website = action.get('website', None)
                
                # Clean up the query to ensure it only contains search keywords
                # Remove any explanatory text, instructions, or other non-search content
                query = self._clean_search_query(query)
                console.print(f"[green]Using cleaned search query:[/green] '{query}'")
                
                # If a specific website is provided in the action, use it
                if website and isinstance(website, dict) and 'url' in website:
                    # First navigate to the website
                    await self.navigate(website['url'])
                    console.print(f"[green]Navigated to {website['name']} ({website['url']}) for search[/green]")
                    
                    # Then search using the website's search functionality
                    await self.search(query)
                    
                    # Take a screenshot after search
                    try:
                        await self._take_screenshot("search_website")
                    except Exception as e:
                        console.print(f"[yellow]Warning: Could not take screenshot after search: {str(e)}[/yellow]")
                    
                    return f"Searched for '{query}' on {website['name']}"
                
                # If no website is provided, check if we're already on a search engine
                current_url = self.page.url
                if "google.com" in current_url or "bing.com" in current_url or "yahoo.com" in current_url or "duckduckgo.com" in current_url:
                    # We're already on a search engine, just use the search box
                    await self.search(query)
                    
                    # Take a screenshot after search
                    try:
                        await self._take_screenshot("search_current")
                    except Exception as e:
                        console.print(f"[yellow]Warning: Could not take screenshot after search: {str(e)}[/yellow]")
                    
                    return f"Searched for '{query}' on current page"
                
                # If no website is provided and we're not on a search engine, default to Google
                await self.navigate("https://www.google.com")
                console.print("[yellow]No specific website provided for search. Defaulting to Google.[/yellow]")
                
                # Then search using Google's search functionality
                await self.search(query)
                
                # Take a screenshot after search
                try:
                    await self._take_screenshot("search_google")
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not take screenshot after search: {str(e)}[/yellow]")
                
                return f"Searched for '{query}' on Google"
                
            elif action_type == 'capture_state':
                state = await self.capture_page_state()
                return "Captured current page state"
                
            else:
                return f"Error: Unknown action type: {action_type}"
                
        except Exception as e:
            console.print(f"[bold red]Error executing action:[/bold red] {str(e)}")
            import traceback
            console.print(traceback.format_exc())
            return f"Error executing {action_type} action: {str(e)}"

    async def press_key(self, key):
        """
        Press a keyboard key
        
        Args:
            key (str): Key to press (e.g., 'Enter', 'Tab', etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized:
            if not await self.initialize():
                return False
        
        try:
            await self.page.keyboard.press(key)
            console.print(f"[green]Pressed key:[/green] {key}")
            return True
        
        except Exception as e:
            console.print(f"[bold red]Error pressing key:[/bold red] {str(e)}")
            return False

    async def _take_screenshot(self, action_name):
        """
        Take a screenshot of the current page
        
        Args:
            action_name (str): The name of the action for the screenshot filename
            
        Returns:
            str: Path to the screenshot file
        """
        if not self.is_initialized:
            return None
        
        try:
            # Create screenshots directory if it doesn't exist
            screenshots_dir = "screenshots"
            if not os.path.exists(screenshots_dir):
                os.makedirs(screenshots_dir)
            
            # Generate a filename based on the action name and timestamp
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{screenshots_dir}/{timestamp}_{action_name}.png"
            
            # Take the screenshot
            await self.page.screenshot(path=filename)
            
            console.print(f"[green]Screenshot saved:[/green] {filename}")
            return filename
            
        except Exception as e:
            console.print(f"[bold red]Error taking screenshot:[/bold red] {str(e)}")
            return None

    def _clean_search_query(self, query):
        """
        Clean up the search query to ensure it only contains search keywords
        
        Args:
            query (str): The original search query
            
        Returns:
            str: The cleaned search query
        """
        import re
        
        # Check if the query is already clean (short and simple)
        if len(query.split()) <= 10 and not any(phrase in query.lower() for phrase in ["i'll", "let me", "first", "then", "help me", "please", "could you"]):
            return query
            
        # Remove common phrases that indicate explanations or instructions
        phrases_to_remove = [
            r"i'll.*?search for",
            r"let me search for",
            r"i will search for",
            r"help me find",
            r"please search for",
            r"could you search for",
            r"i need to find",
            r"i want to search for",
            r"search for",
            r"looking for",
            r"find",
            r"first,.*?",
            r"then,.*?",
            r"next,.*?",
            r"finally,.*?",
            r"i'll.*?",
            r"i will.*?",
            r"let's.*?",
            r"let me.*?",
        ]
        
        cleaned_query = query.lower()
        for phrase in phrases_to_remove:
            cleaned_query = re.sub(phrase, "", cleaned_query, flags=re.IGNORECASE)
        
        # Remove punctuation except for $ and % which might be relevant for searches
        cleaned_query = re.sub(r'[^\w\s$%]', '', cleaned_query)
        
        # Remove extra whitespace
        cleaned_query = re.sub(r'\s+', ' ', cleaned_query).strip()
        
        # If the cleaning removed too much, fall back to the original query
        if len(cleaned_query) < 3:
            # Just remove punctuation as a fallback
            cleaned_query = re.sub(r'[^\w\s$%]', '', query).strip()
        
        return cleaned_query

# Global variable to store the browser executor instance
_browser_executor = None

# Helper function to run browser actions
def run_browser_action(action_type, **kwargs):
    """
    Run a browser action
    
    Args:
        action_type (str): The type of action to execute
        **kwargs: Additional arguments for the action
        
    Returns:
        bool: True if successful, False otherwise
    """
    global _browser_executor
    
    async def _run_action():
        global _browser_executor
        
        # Create a new executor if one doesn't exist
        if _browser_executor is None:
            _browser_executor = BrowserExecutor()
            console.print("[bold green]Created new browser session[/bold green]")
        
        # Remove action_type from kwargs to avoid duplicate argument
        if 'action_type' in kwargs:
            del kwargs['action_type']
        
        # Execute the action
        result = await _browser_executor.execute_action(action_type, **kwargs)
        
        # Only close the browser if explicitly requested or on error
        if action_type == 'close' or (not result and kwargs.get('close_on_error', False)):
            if _browser_executor:
                await _browser_executor.close()
                _browser_executor = None
                console.print("[bold yellow]Browser session closed[/bold yellow]")
        
        return result
    
    # Create a new event loop if needed
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(_run_action())
    except RuntimeError:
        # If we're already in an event loop, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_run_action()) 