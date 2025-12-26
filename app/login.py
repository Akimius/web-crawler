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
    email = os.environ.get('INVESTING_EMAIL', '')
    password = os.environ.get('INVESTING_PASSWORD', '')

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

        # Try multiple strategies to find sign-in button
        sign_in_btn = None
        selectors = [
            (By.XPATH, "//a[contains(text(), 'Sign In')]"),
            (By.XPATH, "//button[contains(text(), 'Sign In')]"),
            (By.XPATH, "//span[contains(text(), 'Sign In')]/.."),
            (By.XPATH, "//*[contains(@class, 'sign') and contains(@class, 'in')]"),
            (By.CSS_SELECTOR, 'a[data-test="sign-in-button"]'),
            (By.CSS_SELECTOR, '[data-test*="signin"]'),
            (By.CSS_SELECTOR, 'header a[href*="login"]'),
            (By.CSS_SELECTOR, 'header a[href*="sign"]'),
        ]

        for by, selector in selectors:
            try:
                sign_in_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((by, selector))
                )
                print(f"Found sign-in button with: {by}='{selector}'")
                break
            except TimeoutException:
                print(f"  Not found: {selector}")
                continue

        if not sign_in_btn:
            # Debug: print all links in header
            print("\nDebug - Links in page header:")
            header_links = driver.find_elements(By.CSS_SELECTOR, 'header a, nav a')
            for link in header_links[:20]:
                href = link.get_attribute('href') or ''
                text = link.text.strip() or link.get_attribute('aria-label') or ''
                if text or 'sign' in href.lower() or 'login' in href.lower():
                    print(f"  '{text}' -> {href}")
            raise TimeoutException("Could not find sign-in button")

        sign_in_btn.click()
        time.sleep(2)

        driver.save_screenshot('/app/data/debug_after_signin_click.png')
        print("Screenshot saved to /app/data/debug_after_signin_click.png")

        # Click "Sign in with Email" button (site shows social login options first)
        print("Looking for 'Sign in with Email' option...")
        email_login_btn = None
        email_selectors = [
            (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign in with email')]"),
            (By.XPATH, "//button[contains(text(), 'Email')]"),
            (By.XPATH, "//a[contains(text(), 'Email')]"),
            (By.XPATH, "//*[contains(text(), 'with Email')]"),
            (By.CSS_SELECTOR, '[data-test*="email"]'),
            (By.CSS_SELECTOR, 'button[class*="email"], a[class*="email"]'),
        ]

        for by, selector in email_selectors:
            try:
                email_login_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((by, selector))
                )
                print(f"Found email login with: {by}='{selector}'")
                break
            except TimeoutException:
                print(f"  Not found: {selector}")
                continue

        if not email_login_btn:
            # Debug: print all buttons/links in modal
            print("\nDebug - Buttons in modal:")
            buttons = driver.find_elements(By.CSS_SELECTOR, 'button, a[role="button"], [class*="btn"]')
            for btn in buttons:
                text = btn.text.strip()
                if text and len(text) < 50:
                    print(f"  '{text}'")
            raise TimeoutException("Could not find 'Sign in with Email' button")

        email_login_btn.click()
        print("Clicked 'Sign in with Email'")
        time.sleep(1)

        driver.save_screenshot('/app/data/debug_after_email_option.png')
        print("Screenshot saved to /app/data/debug_after_email_option.png")

        # Wait for login form and fill credentials
        print("Looking for email field...")
        email_field = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[type="email"], input[name="email"], input[placeholder*="mail"]'))
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
        driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", submit_btn)  # Use JS click for reliability
        print("Submit clicked")

        driver.save_screenshot('/app/data/debug_after_submit.png')
        print("Screenshot saved to /app/data/debug_after_submit.png")

        # Wait a moment for any error messages to appear
        time.sleep(3)

        # Check for error messages
        try:
            error_elem = driver.find_element(By.CSS_SELECTOR, '[class*="error"], [class*="Error"], [role="alert"], .alert')
            error_text = error_elem.text
            if error_text:
                print(f"Login error message: {error_text}")
        except NoSuchElementException:
            print("No error message found")

        driver.save_screenshot('/app/data/debug_after_wait.png')
        print("Screenshot saved to /app/data/debug_after_wait.png")

        # Wait for login to complete (check for user menu or profile element)
        print("Waiting for login to complete...")
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-test="user-menu"], .user-menu, [class*="userMenu"], [class*="avatar"], [class*="profile"]'))
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
