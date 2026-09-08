from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import requests
from bs4 import BeautifulSoup

# Initialize Chrome driver
driver = webdriver.Chrome()

try:
    # =============================================================
    # PAGE 1: Reach the SSO portal (4 Tabs + Enter)
    # =============================================================
    driver.get(
        "https://cpp.starrezhousing.com/StarRezWeb/main/directory"
    )
    time.sleep(4)

    actions = ActionChains(driver)

    print("Tab-navigating Page 1...")
    actions.send_keys(Keys.TAB * 4).send_keys(Keys.ENTER).perform()
    time.sleep(4)

    # =============================================================
    # PAGE 2: Fill credentials and execute SSO submit
    # =============================================================
    print("Typing credentials...")

    actions.reset_actions()
    actions.send_keys("lgamboa2") \
        .send_keys(Keys.TAB) \
        .send_keys("Weezer123!?!?") \
        .send_keys(Keys.TAB * 4) \
        .send_keys(Keys.ENTER) \
        .perform()

    # =============================================================
    # PAGE 3: Duo Multi-Factor Verification
    # =============================================================
    print(
        "\n[ACTION REQUIRED] Duo push sent! "
        "Please approve it on your phone now..."
    )
    time.sleep(15)

    # Click through the trust-device screen
    print(
        "Executing Trust Device selection via keyboard "
        "(2 Tabs + Enter)..."
    )

    actions.reset_actions()
    actions.send_keys(Keys.TAB * 2).send_keys(Keys.ENTER).perform()

    print("Waiting for StarRez Dashboard to initialize and settle...")
    time.sleep(8)

    # =============================================================
    # SESSION DATA EXTRACTION
    # =============================================================
    print("\nExtracting session authorization data...")

    user_agent = driver.execute_script(
        "return navigator.userAgent;"
    )

    selenium_cookies = driver.get_cookies()

    cookie_header_string = "; ".join(
        [
            f"{cookie['name']}={cookie['value']}"
            for cookie in selenium_cookies
        ]
    )

    anti_forgery_token = ""

    try:
        token_js_script = """
        return Array.from(document.querySelectorAll('input'))
            .find(element =>
                element.name?.toLowerCase().includes('token')
            )?.value || '';
        """

        anti_forgery_token = driver.execute_script(
            token_js_script
        )

    except Exception as error:
        print(f"[-] Token extraction issue: {error}")

    print(
        "Anti-forgery token found:",
        bool(anti_forgery_token)
    )

    # =============================================================
    # FIRST REQUEST: Directory page
    # =============================================================
    print("\n" + "=" * 50)
    print(" EXECUTING DIRECT BACKEND POST REQUEST")
    print("=" * 50)

    target_api_url = (
        "https://cpp.starrezhousing.com/"
        "StarRezWeb/main/directory"
    )

    api_headers = {
        "User-Agent": user_agent,
        "Cookie": cookie_header_string,
        "Content-Type": "application/json",
        "X-RequestVerificationToken": anti_forgery_token,
        "__RequestVerificationToken": anti_forgery_token,
        "Referer": (
            "https://cpp.starrezhousing.com/"
            "StarRezWeb/main/directory"
        ),
        "X-Requested-With": "XMLHttpRequest"
    }

    api_payload = {
        "id": 314065
    }

    print(f"Sending POST to: {target_api_url}")

    response = requests.post(
        target_api_url,
        headers=api_headers,
        json=api_payload
    )

    print(f"Response Status Code: {response.status_code}")

    if response.status_code == 200:
        print("\n[+] SUCCESS! Processing HTML content...")

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        print("\n--- Readable Text Found Inside Response ---")

        clean_text = soup.get_text(
            separator="\n",
            strip=True
        )

        print(clean_text[:3000])

    else:
        print(
            "[-] Request failed or returned abnormal code: "
            f"{response.status_code}"
        )
        print(response.text[:500])

    print("=" * 50)

    # =============================================================
    # SECOND REQUEST: Entry address list
    # =============================================================
    target_api_url = (
        "https://cpp.starrezhousing.com/"
        "StarRezWeb/Main/EntryAddressList/Show"
        "?id=314065"
        "&_=1788467171296"
    )

    # DevTools shows that this endpoint uses GET
    print(f"Sending GET to: {target_api_url}")

    response = requests.get(
        target_api_url,
        headers=api_headers
    )

    print(f"Response Status Code: {response.status_code}")

    if response.status_code == 200:
        print("\n[+] SUCCESS! Processing HTML content...")

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        print("\n--- Readable Text Found Inside Response ---")

        clean_text = soup.get_text(
            separator="\n",
            strip=True
        )

        print(clean_text[:3000])

    else:
        print(
            "[-] Request failed or returned abnormal code: "
            f"{response.status_code}"
        )
        print(response.text[:500])

finally:
    # Gracefully close the browser session window
    driver.quit()
