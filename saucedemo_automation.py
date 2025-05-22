import asyncio
import logging
import random
import time
import os
import argparse
from abc import ABC, abstractmethod
from playwright.async_api import async_playwright, Playwright, BrowserContext
from dataclasses import dataclass
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import TimeoutError, Error
import aiohttp
from decouple import config

# Configure logging for HumanFlow
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("automation.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@dataclass
class UserCredentials:
    username: str
    password: str


class BrowserContextManager:
    """Manages Playwright browser context and proxy setup for HumanFlow."""

    def __init__(self, headless: bool = False, proxy: Optional[dict] = None):
        self.headless = headless
        self.proxy = proxy
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[BrowserContext] = None

    async def test_proxy_connectivity(self):
        """Tests proxy connectivity by making a simple HTTP request."""
        if not self.proxy:
            logger.info("No proxy configured, skipping connectivity test")
            return True
        async with aiohttp.ClientSession() as session:
            try:
                proxy_url = self.proxy.get("server")
                logger.info(f"Testing proxy connectivity: {proxy_url}")
                auth = (
                    aiohttp.BasicAuth(
                        login=self.proxy.get("username"),
                        password=self.proxy.get("password"),
                    )
                    if self.proxy.get("username")
                    else None
                )
                async with session.get(
                    "http://ipinfo.io/ip", proxy=proxy_url, auth=auth, timeout=5
                ) as response:
                    ip = await response.text()
                    logger.info(f"Proxy connectivity successful, IP: {ip.strip()}")
                    return True
            except Exception as e:
                logger.error(f"Proxy connectivity test failed: {str(e)}")
                return False

    async def __aenter__(self) -> BrowserContext:
        if not await self.test_proxy_connectivity():
            raise Exception("Proxy connectivity test failed")
        self.playwright = await async_playwright().start()
        launch_args = {"headless": self.headless}
        if self.proxy:
            logger.info(f"Using proxy: {self.proxy.get('server')}")
            launch_args["proxy"] = self.proxy
        self.browser = await self.playwright.chromium.launch(**launch_args)
        return await self.browser.new_context()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


class UserBehaviorSimulator:
    """Simulates human-like behavior for HumanFlow automation."""

    @staticmethod
    async def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
        delay = random.uniform(min_seconds, max_seconds)
        logger.info(f"Applying random delay of {delay:.2f} seconds")
        await asyncio.sleep(delay)

    @staticmethod
    async def human_like_scroll(page):
        logger.info("Performing human-like scroll")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await UserBehaviorSimulator.random_delay()
        await page.evaluate("window.scrollTo(0, 0)")

    @staticmethod
    async def human_like_mouse_move(page, x: int, y: int):
        logger.info(f"Moving mouse to coordinates ({x}, {y})")
        await page.mouse.move(x, y, steps=10)
        await UserBehaviorSimulator.random_delay(0.5, 1.5)

    @staticmethod
    async def human_like_type(page, selector: str, text: str):
        logger.info(f"Typing '{text}' into {selector}")
        for char in text:
            await page.type(selector, char)
            await UserBehaviorSimulator.random_delay(0.1, 0.3)

    @staticmethod
    async def hover_over_element(page, selector):
        logger.info(f"Hovering over element: {selector}")
        if isinstance(selector, str):
            locator = page.locator(selector)
        else:
            locator = selector  # Already a Locator object
        await locator.wait_for(state="visible", timeout=20000)
        button_count = await locator.count()
        logger.info(f"Found {button_count} elements for selector")
        if button_count != 1:
            logger.error(f"Expected 1 element for selector, found {button_count}")
            raise ValueError(
                f"Strict mode violation: selector resolved to {button_count} elements"
            )
        await locator.hover()
        await UserBehaviorSimulator.random_delay(0.5, 1.0)


class SiteAutomation(ABC):
    """Abstract base class for site-specific automation in HumanFlow."""

    def __init__(self, context: BrowserContext):
        self.context = context
        self.page = None

    @abstractmethod
    async def setup(self):
        pass

    @abstractmethod
    async def login(self, credentials: Optional[UserCredentials] = None):
        pass

    @abstractmethod
    async def perform_actions(
        self,
        credentials: Optional[UserCredentials] = None,
        num_products: Optional[int] = None,
    ):
        pass

    @abstractmethod
    async def take_screenshot(self, step: str):
        pass


class SauceDemoAutomation(SiteAutomation):
    """Handles interactions with saucedemo.com for HumanFlow."""

    def __init__(self, context: BrowserContext):
        super().__init__(context)
        self.run_timestamp = time.strftime("%Y%m%d_%H%M")

    async def setup(self):
        self.page = await self.context.new_page()
        await self.page.goto("https://www.saucedemo.com")
        await self.page.wait_for_load_state("networkidle")
        logger.info(f"Navigated to saucedemo.com, URL: {self.page.url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type((TimeoutError, Error)),
    )
    async def login(self, credentials: Optional[UserCredentials] = None):
        if not credentials:
            raise ValueError("Credentials required for saucedemo.com")
        try:
            await UserBehaviorSimulator.human_like_type(
                self.page, "#user-name", credentials.username
            )
            await UserBehaviorSimulator.human_like_type(
                self.page, "#password", credentials.password
            )
            await UserBehaviorSimulator.human_like_mouse_move(self.page, 500, 600)
            await UserBehaviorSimulator.hover_over_element(self.page, "#login-button")
            await self.page.click("#login-button")
            await self.page.wait_for_load_state("networkidle")
            await self.page.wait_for_selector(
                ".inventory_list", state="visible", timeout=20000
            )
            logger.info(f"Login successful, URL: {self.page.url}")
            await self.take_screenshot("after_login")
        except Exception as e:
            logger.error(f"Login failed: {str(e)}, URL: {self.page.url}")
            raise

    async def check_and_relogin(self, credentials: UserCredentials):
        """Checks for login page and re-logs in if detected."""
        if await self.page.locator("#user-name").count() > 0:
            logger.warning(
                f"Login page detected at URL: {self.page.url}, attempting re-login"
            )
            await self.take_screenshot("relogin_attempt")
            await self.login(credentials)
            await self.page.goto("https://www.saucedemo.com/inventory.html")
            await self.page.wait_for_selector(
                ".inventory_list", state="visible", timeout=20000
            )
            logger.info(f"Re-login successful, URL: {self.page.url}")
            return True
        return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type((TimeoutError, Error)),
    )
    async def perform_actions(
        self,
        credentials: Optional[UserCredentials] = None,
        num_products: Optional[int] = None,
    ):
        if not credentials:
            raise ValueError("Credentials required for perform_actions")
        try:
            # Check for login page
            await self.check_and_relogin(credentials)
            # Verify we're on the inventory page
            await self.page.wait_for_selector(
                ".inventory_list", state="visible", timeout=20000
            )
            logger.info(f"On inventory page, URL: {self.page.url}")
            await UserBehaviorSimulator.human_like_scroll(self.page)
            # Interact with multiple products
            products = await self.page.locator(".inventory_item").all()
            logger.info(f"Found {len(products)} products")
            if products:
                num_interactions = (
                    num_products
                    if num_products is not None
                    else random.randint(1, min(3, len(products)))
                )
                if num_interactions < 1 or num_interactions > len(products):
                    logger.warning(
                        f"Invalid num_products {num_interactions}, setting to {min(3, len(products))}"
                    )
                    num_interactions = min(3, len(products))
                logger.info(f"Interacting with {num_interactions} products")
                for i in range(num_interactions):
                    product = random.choice(products)
                    product_name = product.locator(".inventory_item_name").first
                    if await product_name.count() == 0:
                        logger.warning("Product name locator not found")
                        name = "unknown"
                    else:
                        name = await product_name.inner_text()
                    logger.info(f"Selected product: {name}")
                    await UserBehaviorSimulator.hover_over_element(
                        self.page, f".inventory_item >> nth={products.index(product)}"
                    )
                    await product.locator(".inventory_item_name").click()
                    await self.page.wait_for_url(
                        "**/inventory-item.html**", timeout=20000
                    )
                    await self.page.wait_for_load_state("networkidle")
                    logger.info(
                        f"Navigated to product details page for {name}, URL: {self.page.url}"
                    )
                    await UserBehaviorSimulator.random_delay()
                    await UserBehaviorSimulator.hover_over_element(
                        self.page, ".btn_inventory"
                    )
                    await self.page.click(".btn_inventory")
                    logger.info(f"Added product '{name}' to cart")
                    await self.page.goto("https://www.saucedemo.com/inventory.html")
                    await self.page.wait_for_selector(
                        ".inventory_list", state="visible", timeout=20000
                    )
                    logger.info(f"Returned to inventory page, URL: {self.page.url}")
                    products = await self.page.locator(
                        ".inventory_item"
                    ).all()  # Refresh list
            else:
                logger.warning("No products found")

            # Check for login page before cart
            await self.check_and_relogin(credentials)
            # Navigate to cart
            await self.page.wait_for_selector(
                ".shopping_cart_link", state="visible", timeout=20000
            )
            await UserBehaviorSimulator.hover_over_element(
                self.page, ".shopping_cart_link"
            )
            await self.page.click(".shopping_cart_link")
            await self.page.wait_for_load_state("networkidle")
            logger.info(f"Navigated to cart, URL: {self.page.url}")
            await self.take_screenshot("cart_view")

            # Remove an item from cart
            cart_items = await self.page.locator(".cart_item").all()
            if cart_items:
                item = random.choice(cart_items)
                item_name = item.locator(".inventory_item_name").first
                if await item_name.count() == 0:
                    logger.warning("Cart item name locator not found")
                    name = "unknown"
                else:
                    name = await item_name.inner_text()
                logger.info(f"Selected cart item: {name}")
                remove_button = item.locator(".btn_secondary")
                if await remove_button.count() != 1:
                    logger.error(
                        f"Expected 1 remove button for cart item '{name}', found {await remove_button.count()}"
                    )
                    raise ValueError(
                        f"Strict mode violation: remove button for cart item '{name}' resolved to {await remove_button.count()} elements"
                    )
                await UserBehaviorSimulator.hover_over_element(self.page, remove_button)
                await remove_button.click()
                logger.info(f"Removed item '{name}' from cart")
            else:
                logger.info("No items in cart to remove")

            # Check for login page before logout
            await self.check_and_relogin(credentials)
            # Log out
            await self.page.wait_for_selector(
                "#menu_button_container .bm-burger-button",
                state="visible",
                timeout=20000,
            )
            await UserBehaviorSimulator.hover_over_element(
                self.page, "#menu_button_container .bm-burger-button"
            )
            await self.page.click("#menu_button_container .bm-burger-button")
            await UserBehaviorSimulator.random_delay()
            await UserBehaviorSimulator.hover_over_element(
                self.page, "#logout_sidebar_link"
            )
            await self.page.click("#logout_sidebar_link")
            await self.page.wait_for_load_state("networkidle")
            logger.info(f"Logged out successfully, URL: {self.page.url}")
            await self.take_screenshot("after_logout")
        except Exception as e:
            logger.error(f"Action failed: {str(e)}, URL: {self.page.url}")
            raise

    async def take_screenshot(self, step: str):
        screenshot_dir = os.path.join("screens", self.run_timestamp)
        os.makedirs(screenshot_dir, exist_ok=True)
        screenshot_path = os.path.join(screenshot_dir, f"{step}.png")
        await self.page.screenshot(path=screenshot_path)
        logger.info(f"Screenshot saved to {screenshot_path}")


def parse_args():
    """Parse command-line arguments for HumanFlow."""
    parser = argparse.ArgumentParser(
        description="HumanFlow: Automate saucedemo.com with human-like behavior"
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run in headless mode (default: False)"
    )
    parser.add_argument(
        "--num-products",
        type=int,
        help="Number of products to interact with (1-6, default: random 1-3)",
    )
    parser.add_argument(
        "--proxy",
        help="Proxy server URL (e.g., http://proxy:port or socks5://127.0.0.1:9050)",
    )
    parser.add_argument("--proxy-username", help="Proxy username (optional)")
    parser.add_argument("--proxy-password", help="Proxy password (optional)")
    return parser.parse_args()


async def main():
    args = parse_args()
    credentials = UserCredentials(username="standard_user", password="secret_sauce")

    # Configure proxy
    proxy = None
    if args.proxy:
        proxy = {"server": args.proxy}
        if args.proxy_username:
            proxy["username"] = args.proxy_username
        if args.proxy_password:
            proxy["password"] = args.proxy_password
    else:
        # Check .env for proxy settings as fallback
        env_proxy = {
            "server": config("PROXY_SERVER_URL", default=""),
            "username": config("PROXY_USERNAME", default=""),
            "password": config("PROXY_PASSWORD", default=""),
        }
        proxy = None if not env_proxy["server"] else env_proxy

    logger.info(
        f"Running with headless={args.headless}, num_products={args.num_products or 'random 1-3'}, proxy={proxy.get('server') if proxy else 'None'}"
    )

    async with BrowserContextManager(headless=args.headless, proxy=proxy) as context:
        automation = SauceDemoAutomation(context)
        try:
            await automation.setup()
            await automation.login(credentials)
            await automation.perform_actions(
                credentials=credentials, num_products=args.num_products
            )
            logger.info("Script execution completed.")
        except Exception as e:
            logger.error(
                f"Script execution failed: {str(e)}, URL: {automation.page.url if automation.page else 'unknown'}"
            )
            if automation.page:
                await automation.take_screenshot("error")
            raise


if __name__ == "__main__":
    asyncio.run(main())
    logging.shutdown()
