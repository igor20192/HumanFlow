import asyncio
import logging
import random
import time
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

    def __init__(self, headless: bool = True, proxy: Optional[dict] = None):
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
    async def hover_over_element(page, selector: str):
        logger.info(f"Hovering over element: {selector}")
        await page.locator(selector).hover()
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
    async def perform_actions(self):
        pass

    @abstractmethod
    async def take_screenshot(self, step: str):
        pass


class SauceDemoAutomation(SiteAutomation):
    """Handles interactions with saucedemo.com for HumanFlow."""

    async def setup(self):
        self.page = await self.context.new_page()
        await self.page.goto("https://www.saucedemo.com")
        logger.info("Navigated to saucedemo.com")

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
            logger.info("Login attempt successful")
            await self.take_screenshot("after_login")
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type((TimeoutError, Error)),
    )
    async def perform_actions(self):
        try:
            await UserBehaviorSimulator.human_like_scroll(self.page)
            # Interact with multiple products
            await self.page.wait_for_selector(
                ".inventory_item", state="visible", timeout=10000
            )
            logger.info("Products on the inventory page are visible.")
            products = await self.page.locator(".inventory_item").all()
            if products:
                num_interactions = random.randint(1, min(3, len(products)))
                logger.info(f"Interacting with {num_interactions} products")
                for i in range(num_interactions):
                    product = random.choice(products)
                    product_name = await product.query_selector(".inventory_item_name")
                    name = (
                        await product_name.inner_text() if product_name else "unknown"
                    )
                    await UserBehaviorSimulator.hover_over_element(
                        self.page, f".inventory_item >> nth={products.index(product)}"
                    )
                    await product.click()
                    logger.info(f"Clicked on product: {name}")
                    await UserBehaviorSimulator.random_delay()
                    await UserBehaviorSimulator.hover_over_element(
                        self.page, '[data-test="add-to-cart-sauce-labs-backpack"]'
                    )
                    await self.page.click(".btn_inventory")
                    logger.info(f"Added product '{name}' to cart")
                    await self.page.go_back()
                    products = await self.page.query_selector_all(
                        ".inventory_item"
                    )  # Refresh list
            else:
                logger.warning("No products found")

            # Navigate to cart
            await UserBehaviorSimulator.hover_over_element(
                self.page, ".shopping_cart_link"
            )
            await self.page.click(".shopping_cart_link")
            logger.info("Navigated to cart")
            await self.take_screenshot("cart_view")

            # Remove an item from cart
            cart_items = await self.page.query_selector_all(".cart_item")
            if cart_items:
                item = random.choice(cart_items)
                item_name = await item.query_selector(".inventory_item_name")
                name = await item_name.inner_text() if item_name else "unknown"
                await UserBehaviorSimulator.hover_over_element(
                    self.page, ".cart_item .btn_secondary"
                )
                await self.page.click(".cart_item .btn_secondary")
                logger.info(f"Removed item '{name}' from cart")

            # Log out
            await UserBehaviorSimulator.hover_over_element(
                self.page, "#menu_button_container .bm-burger-button"
            )
            await self.page.click("#menu_button_container .bm-burger-button")
            await UserBehaviorSimulator.random_delay()
            await UserBehaviorSimulator.hover_over_element(
                self.page, "#logout_sidebar_link"
            )
            await self.page.click("#logout_sidebar_link")
            logger.info("Logged out successfully")
            await self.take_screenshot("after_logout")
        except Exception as e:
            logger.error(f"Action failed: {str(e)}")
            raise

    async def take_screenshot(self, step: str):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshot_{step}_{timestamp}.png"
        await self.page.screenshot(path=screenshot_path)
        logger.info(f"Screenshot saved to {screenshot_path}")


async def main():
    credentials = UserCredentials(username="standard_user", password="secret_sauce")
    # Example proxy configuration (HTTP proxy)
    proxy = {
        "server": config("PROXY_SERVER_URL"),
        "username": (config("PROXY_USERNAME")),  # Optional
        "password": (config("PROXY_PASSWORD")),  # Optional,
    }
    # For Tor, ensure Tor is running locally (e.g., Tor Browser or tor service)
    # proxy = {"server": "socks5://127.0.0.1:9050"}  # Tor default port
    async with BrowserContextManager(
        headless=False, proxy=None
    ) as context:  # Set proxy=None for no proxy
        automation = SauceDemoAutomation(context)
        try:
            await automation.setup()
            await automation.login(credentials)
            await automation.perform_actions()
        except Exception as e:
            logger.error(f"Script execution failed: {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
