import logging
import os
import time
from typing import List, Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def login() -> bool:
    email = os.environ.get('INVESTING_EMAIL', 'akim.savchenko@gmail.com')
    password = os.environ.get('INVESTING_PASSWORD', 'ab123456789')

    from browser import get_chrome_driver
    driver = get_chrome_driver()
    logger.info("Selenium driver initialized for Investing.com")

    try:
        print("Logging in to Investing.com")
        driver.get("https://www.investing.com")
        print(f"Page loaded: {driver.title}")

        wait = WebDriverWait(driver, 15)

        # Try to dismiss cookie consent popup if present
        try:
            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, '#onetrust-accept-btn-handler, [id*="accept"], button[class*="accept"]'))
            )
            cookie_btn.click()
            print("Dismissed cookie consent popup")
            time.sleep(1)
        except TimeoutException:
            print("No cookie popup found, continuing...")

        # Take screenshot for debugging
        driver.save_screenshot('/app/data/debug_before_login.png')
        print("Screenshot saved to /app/data/debug_before_login.png")

        # Click sign-in button to open login modal
        print("Looking for sign-in button...")
        sign_in_btn = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'a[data-test="sign-in-button"], .login-btn, [class*="signIn"], [data-test="header-signin-button"]'))
        )
        print(f"Found sign-in button: {sign_in_btn.text}")
        sign_in_btn.click()
        time.sleep(2)

        driver.save_screenshot('/app/data/debug_after_signin_click.png')
        print("Screenshot saved to /app/data/debug_after_signin_click.png")

        # Wait for login form and fill credentials
        print("Looking for email field...")
        email_field = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[type="email"], input[name="email"], #loginFormUser_email'))
        )
        email_field.clear()
        email_field.send_keys(email)
        print("Email entered")

        password_field = driver.find_element(By.CSS_SELECTOR,
                                             'input[type="password"], input[name="password"], #loginForm_password')
        password_field.clear()
        password_field.send_keys(password)
        print("Password entered")

        # Submit login form
        submit_btn = driver.find_element(By.CSS_SELECTOR,
                                         'button[type="submit"], input[type="submit"], .login-btn-submit')
        submit_btn.click()
        print("Submit clicked")

        # Wait for login to complete
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-test="user-menu"], .user-menu, [class*="userMenu"]'))
        )

        logger.info("Successfully logged in to Investing.com")
        return True

    except TimeoutException as e:
        print(f"Timeout waiting for element")
        driver.save_screenshot('/app/data/debug_error.png')
        print("Error screenshot saved to /app/data/debug_error.png")
        print(f"Current URL: {driver.current_url}")
        print(f"Page source preview: {driver.page_source[:500]}")
        return False
    except Exception as exception:
        print(f"Failed to log in: {type(exception).__name__}: {exception}")
        driver.save_screenshot('/app/data/debug_error.png')
        return False
    finally:
        driver.quit()


if __name__ == '__main__':
    login()
