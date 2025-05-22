# HumanFlow: Saucedemo Automation Script

## Overview
HumanFlow is a Python script that automates user interactions on saucedemo.com, simulating realistic human behavior with features like character-by-character typing, hovering, scrolling, and configurable delays. It includes retry logic, proxy support, organized screenshots, a re-login mechanism, network error handling, and an extensible architecture.

## Repository
The source code is hosted on GitHub. You can clone the repository using:

- **SSH**: `git clone git@github.com:igor20192/HumanFlow.git`
- **HTTPS**: `git clone https://github.com/igor20192/HumanFlow.git`

View the project on GitHub: [https://github.com/igor20192/HumanFlow](https://github.com/igor20192/HumanFlow)

## Prerequisites
- Python 3.8+
- Playwright: Install via `pip install playwright`
- Tenacity (for retries): Install via `pip install tenacity`
- Aiohttp (for proxy check): Install via `pip install aiohttp`
- Python-decouple (for env variables): Install via `pip install python-decouple`
- Run `playwright install` to install browser binaries
- (Optional) Proxy server or Tor service running for proxy support

## Installation
1. Clone or download the project.
2. Install dependencies: `pip install -r requirements.txt`
3. Run `playwright install` to set up browser binaries.

## Configuration
- (Optional) Set environment variables in a `.env` file:
  ```
  SAUCE_USERNAME=standard_user  # saucedemo.com username
  SAUCE_PASSWORD=secret_sauce   # saucedemo.com password
  PROXY_SERVER_URL=http://your-proxy-server:port
  PROXY_USERNAME=your_username
  PROXY_PASSWORD=your_password
  MIN_ACTION_DELAY=1.0  # Min action delay in seconds
  MAX_ACTION_DELAY=3.0  # Max action delay in seconds
  MIN_TYPING_DELAY=0.1  # Min typing delay in seconds
  MAX_TYPING_DELAY=0.3  # Max typing delay in seconds
  ```
- For Tor, ensure a Tor service is running (e.g., Tor Browser or `tor` on port 9050) and use `--proxy socks5://127.0.0.1:9050` or update `.env`.

## Running the Script
1. Save the script as `saucedemo_automation.py`.
2. Run the script with optional arguments:
   ```
   python saucedemo_automation.py [--headless] [--num-products N] [--proxy URL] [--proxy-username USER] [--proxy-password PASS] [--min-action-delay MIN] [--max-action-delay MAX] [--min-typing-delay MIN] [--max-typing-delay MAX] [--version]
   ```
   - `--headless`: Run in headless mode (default: False, visible browser).
   - `--num-products N`: Interact with N products (1-6, default: random 1-3).
   - `--proxy URL`: Proxy server (e.g., `http://proxy:port` or `socks5://127.0.0.1:9050`).
   - `--proxy-username USER`: Proxy username (optional).
   - `--proxy-password PASS`: Proxy password (optional).
   - `--min-action-delay MIN`: Min action delay in seconds (default: 1.0).
   - `--max-action-delay MAX`: Max action delay in seconds (default: 3.0).
   - `--min-typing-delay MIN`: Min typing delay in seconds (default: 0.1).
   - `--max-typing-delay MAX`: Max typing delay in seconds (default: 0.3).
   - `--version`: Display script version.

   Examples:
   ```
   python saucedemo_automation.py  # Default: non-headless, random 1-3 products, no proxy
   python saucedemo_automation.py --headless --num-products 2 --min-action-delay 0.5 --max-action-delay 1.5
   python saucedemo_automation.py --proxy socks5://127.0.0.1:9050
   python saucedemo_automation.py --version  # Shows HumanFlow v1.0.0
   ```

## Features
- Logs actions to console and `automation.log` with timestamps, URLs, progress messages, and execution summary.
- Simulates human-like behavior: character-by-character typing, hovering, random scrolling, configurable delays.
- Retry logic (3 attempts, 2s delay) for login and actions.
- Command-line arguments for headless mode, product count, proxy, and delay ranges.
- Saves screenshots in `screens/YYYYMMDD_HHMM/` (e.g., `screens/20250522_1203/after_login.png`).
- Re-login mechanism to handle unexpected redirects to the login page.
- Network error handling with logging and screenshots for connection issues.
- CSS selectors defined as constants for maintainability.
- Modular `perform_actions` with private methods for product interactions, cart navigation, cart removal, and logout.
- Credentials configurable via `.env` (defaults to `standard_user`, `secret_sauce`).
- Proxy support (HTTP or Tor; via `.env` or command-line, with CLI precedence).
- Proxy connectivity check using a test HTTP request.
- Interacts with 1–6 products (viewing details, adding to cart).
- Navigates to cart, removes a random item, and logs out.
- Execution summary with step statuses and total runtime.
- Robust navigation with page state checks and URL validation.
- Uses Playwright `Locator` API with strict mode and scoped selectors.

## Notes
- Screenshots are saved in `screens/<timestamp>/<step>.png` (e.g., `after_login.png`, `cart_view.png`).
- Logs are saved to `automation.log` with detailed debugging info and a final summary.
- For Tor proxy, use `--proxy socks5://127.0.0.1:9050` or configure in `.env`.
- Proxy connectivity is tested before execution.
- If errors occur, check `automation.log` and screenshots in `screens/`.
- Network errors are logged with screenshots (e.g., `network_error_login.png`).