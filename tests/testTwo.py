import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium import webdriver

# Initialize Chrome driver
driver = webdriver.Chrome()

try:
    # =============================================================
    # PAGE 1: Reach the SSO portal
    # =============================================================
    driver.get(
        "https://cpp.starrezhousing.com/StarRezWeb/main/directory"
    )

    time.sleep(2)

    actions = ActionChains(driver)

    print("Tab-navigating Page 1...")

    actions.send_keys(Keys.TAB * 4).send_keys(Keys.ENTER).perform()

    time.sleep(2)

    # =============================================================
    # PAGE 2: Fill credentials
    # =============================================================
    print("Typing credentials...")

    actions.reset_actions()

    actions.send_keys("username") \
        .send_keys(Keys.TAB) \
        .send_keys("password") \
        .send_keys(Keys.TAB * 4) \
        .send_keys(Keys.ENTER) \
        .perform()

    # =============================================================
    # PAGE 3: Duo MFA
    # =============================================================
    print(
        "\n[ACTION REQUIRED] Duo push sent! "
        "Please approve it on your phone now..."
    )

    time.sleep(15)

    print("Selecting Trust Device...")

    actions.reset_actions()
    actions.send_keys(Keys.TAB * 2).send_keys(Keys.ENTER).perform()

    print("Waiting for StarRez to load...")

    time.sleep(8)

    # =============================================================
    # EXTRACT ANTI-FORGERY TOKEN
    # =============================================================
    token_script = """
    return Array.from(document.querySelectorAll('input'))
        .find(element =>
            element.name?.toLowerCase().includes('token')
        )?.value || '';
    """

    anti_forgery_token = driver.execute_script(token_script)

    print(
        "Anti-forgery token found:",
        bool(anti_forgery_token)
    )

    # =============================================================
    # CREATE CONTACT
    # =============================================================
    print("\n" + "=" * 55)
    print(" CREATING STARREZ CONTACT")
    print("=" * 55)

    first_name = "Leo"
    last_name = "Test3"

    portal_auth_field = (
        '\'{"ColumnName":"PortalAuthProviderUserID",'
        '"DbObjectName":"Entry",'
        '"ChildColumn":null,'
        '"ChildColumnValue":null}\''
    )

    portal_email_field = (
        '\'{"ColumnName":"PortalEmail",'
        '"DbObjectName":"Entry",'
        '"ChildColumn":null,'
        '"ChildColumnValue":null}\''
    )

    custom_field_10 = (
        '\'{"ChildColumn":"CustomFieldDefinitionID",'
        '"ChildColumnValue":"10",'
        '"ColumnName":"ValueString",'
        '"DbObjectName":"EntryCustomField"}\''
    )

    custom_field_19 = (
        '\'{"ChildColumn":"CustomFieldDefinitionID",'
        '"ChildColumnValue":"19",'
        '"ColumnName":"ValueString",'
        '"DbObjectName":"EntryCustomField"}\''
    )

    changed_fields = [
        "CategoryID",
        "EntryStatus",
        "NameTitle",
        "NameFirst",
        "NameLast",
        "DOB",
        "GenderEnum",
        "ID1",
        portal_auth_field,
        portal_email_field,
        custom_field_10,
        custom_field_19
    ]

    configured_values = {
        portal_auth_field: "",
        portal_email_field: "",
        custom_field_10: "",
        custom_field_19: ""
    }

    vm = {
        "__ChangedFields": changed_fields,
        "CategoryID": "0",
        "EntryStatus": "100",
        "NameTitle": "",
        "NameFirst": first_name,
        "NameLast": last_name,
        "DOB": "",
        "GenderEnum": "0",
        "ID1": "",

        portal_auth_field: "",
        portal_email_field: "",
        custom_field_10: "",
        custom_field_19: "",

        "__ConfiguredFieldsValues": configured_values
    }

    payload = {
        "vm": vm,
        "handler": {
            "_error": {
                "_autoFix": False,
                "_autoIgnore": False
            }
        }
    }

    print(f"Creating contact: {first_name} {last_name}")

    # =============================================================
    # EXECUTE FETCH INSIDE CHROME
    # =============================================================
    fetch_script = """
    const callback = arguments[arguments.length - 1];
    const token = arguments[0];
    const payload = arguments[1];

    fetch("/StarRezWeb/Main/Entry/New", {
        method: "POST",

        headers: {
            "__requestverificationtoken": token,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest"
        },

        credentials: "include",

        body: JSON.stringify(payload)
    })
    .then(async response => {
        const text = await response.text();

        callback({
            ok: response.ok,
            status: response.status,
            statusText: response.statusText,
            body: text
        });
    })
    .catch(error => {
        callback({
            ok: false,
            status: 0,
            statusText: "FETCH ERROR",
            body: String(error)
        });
    });
    """

    result = driver.execute_async_script(
        fetch_script,
        anti_forgery_token,
        payload
    )

    # =============================================================
    # RESPONSE
    # =============================================================
    print("\nStatus Code:", result["status"])

    if result["ok"]:
        print("[+] Request accepted by StarRez.")
    else:
        print("[-] Create Contact request failed.")

    print("\nResponse:")
    print(result["body"][:2000])

    print("=" * 55)

finally:
    driver.quit()
