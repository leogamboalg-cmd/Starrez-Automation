import json
import time

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# AUTOMATICALLY MAKES API CALLS
# TO CREATE CONTACT AND ADD
# EMAIL FIELD
# Remaining: Import excel file
# and automating to run entire
# file

# =============================================================
# SETTINGS
# =============================================================

FIRST_NAME = "Leoo"
LAST_NAME = "Test7"
EMAIL = "leotest7@gmail.com"

STARREZ_DIRECTORY = (
    "https://cpp.starrezhousing.com/StarRezWeb/main/directory"
)


# =============================================================
# START CHROME
# =============================================================

driver = webdriver.Chrome()

try:

    # =========================================================
    # PAGE 1: REACH SSO PORTAL
    # =========================================================

    print("Opening StarRez...")

    driver.get(STARREZ_DIRECTORY)

    time.sleep(2)

    actions = ActionChains(driver)

    print("Tab-navigating Page 1...")

    actions.send_keys(
        Keys.TAB * 4
    ).send_keys(
        Keys.ENTER
    ).perform()

    time.sleep(2)

    # =========================================================
    # PAGE 2: LOGIN
    # =========================================================

    print("Typing credentials...")

    actions.reset_actions()

    actions.send_keys("user") \
        .send_keys(Keys.TAB) \
        .send_keys("password") \
        .send_keys(Keys.TAB * 4) \
        .send_keys(Keys.ENTER) \
        .perform()

    # =========================================================
    # PAGE 3: DUO MFA
    # =========================================================

    print(
        "\n[ACTION REQUIRED] Duo push sent! "
        "Please approve it on your phone now..."
    )

    time.sleep(15)

    print("Selecting Trust Device...")

    actions.reset_actions()

    actions.send_keys(
        Keys.TAB * 2
    ).send_keys(
        Keys.ENTER
    ).perform()

    print("Waiting for StarRez to load...")

    time.sleep(8)

    # =========================================================
    # GET ANTI-FORGERY TOKEN
    # =========================================================

    print("\nGetting anti-forgery token...")

    token_script = """
    return Array.from(document.querySelectorAll('input'))
        .find(element =>
            element.name?.toLowerCase().includes('token')
        )?.value || '';
    """

    anti_forgery_token = driver.execute_script(
        token_script
    )

    print(
        "Anti-forgery token found:",
        bool(anti_forgery_token)
    )

    if not anti_forgery_token:
        raise RuntimeError(
            "Could not find StarRez anti-forgery token."
        )

    # =========================================================
    # CREATE CONTACT PAYLOAD
    # =========================================================

    print("\n" + "=" * 60)
    print(" CREATING STARREZ CONTACT")
    print("=" * 60)

    print(
        f"Creating contact: "
        f"{FIRST_NAME} {LAST_NAME}"
    )

    # IMPORTANT:
    # StarRez expects literal apostrophes around these JSON-like
    # configured-field names.

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

        # StarRez Contact status
        "EntryStatus": "100",

        "NameTitle": "",
        "NameFirst": FIRST_NAME,
        "NameLast": LAST_NAME,
        "DOB": "",
        "GenderEnum": "0",
        "ID1": "",

        portal_auth_field: "",
        portal_email_field: "",
        custom_field_10: "",
        custom_field_19: "",

        "__ConfiguredFieldsValues": configured_values
    }

    create_payload = {
        "vm": vm,

        "handler": {
            "_error": {
                "_autoFix": False,
                "_autoIgnore": False
            }
        }
    }

    # =========================================================
    # CREATE CONTACT
    # =========================================================

    create_fetch_script = """
    const callback = arguments[arguments.length - 1];

    const token = arguments[0];
    const payload = arguments[1];

    fetch("/StarRezWeb/Main/Entry/New", {

        method: "POST",

        headers: {
            "__requestverificationtoken": token,
            "Accept":
                "application/json, text/javascript, */*; q=0.01",
            "Content-Type":
                "application/json; charset=UTF-8",
            "X-Requested-With":
                "XMLHttpRequest"
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

    create_result = driver.execute_async_script(
        create_fetch_script,
        anti_forgery_token,
        create_payload
    )

    print(
        "\nCreate status:",
        create_result["status"]
    )

    if not create_result["ok"]:

        print("[-] Failed to create contact.")

        print(
            create_result["body"][:2000]
        )

        raise RuntimeError(
            "StarRez contact creation failed."
        )

    print(
        "[+] Contact successfully created."
    )

    # =========================================================
    # GET ENTRY ID
    # =========================================================

    try:

        create_response = json.loads(
            create_result["body"]
        )

    except json.JSONDecodeError:

        print(
            "Unexpected create response:"
        )

        print(
            create_result["body"][:2000]
        )

        raise RuntimeError(
            "Could not parse create response."
        )

    if not create_response.get("Success"):

        raise RuntimeError(
            "StarRez did not report successful creation."
        )

    entry_id = create_response.get("Data")

    if not entry_id:

        raise RuntimeError(
            "StarRez did not return an Entry ID."
        )

    print(
        f"[+] Entry ID: {entry_id}"
    )

    # =============================================================
    # LOAD ENTRY ADDRESS LIST
    # =============================================================

    print("\n" + "=" * 60)
    print(" FINDING ENTRY ADDRESS ID")
    print("=" * 60)

    address_lookup_script = """
     const callback = arguments[arguments.length - 1];

     const entryId = arguments[0];
     const token = arguments[1];

     const url =
     "/StarRezWeb/Main/EntryAddressList/Show" +
     "?id=" +
     encodeURIComponent(entryId) +
     "&_=" +
     Date.now();

     fetch(url, {

     method: "GET",

     headers: {
          "__requestverificationtoken": token,
          "Accept": "*/*",
          "Content-Type": "application/json; charset=utf-8",
          "X-Requested-With": "XMLHttpRequest"
     },

     credentials: "include"

     })
     .then(async response => {

     const html = await response.text();

     callback({
          ok: response.ok,
          status: response.status,
          statusText: response.statusText,
          body: html
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

    address_result = driver.execute_async_script(
        address_lookup_script,
        entry_id,
        anti_forgery_token
    )

    print(
        "Address lookup status:",
        address_result["status"]
    )

    if not address_result["ok"]:

        print("[-] Failed to load EntryAddress information.")
        print("Status:", address_result["status"])
        print("Status text:", address_result["statusText"])
        print("Response:")
        print(address_result["body"][:2000])

        raise RuntimeError(
            "Could not load EntryAddress information."
        )

        print("[+] Address information loaded.")

    # =========================================================
    # EXTRACT ENTRY ADDRESS ID
    # =========================================================

    extract_address_script = """
    const html = arguments[0];

    const parser = new DOMParser();

    const documentObject =
        parser.parseFromString(
            html,
            "text/html"
        );

    const editButton =
        documentObject.querySelector(
            '[data-controller="EntryAddress"]' +
            '[data-srelement="Edit_Link"]' +
            '[data-id]'
        );

    if (!editButton) {
        return null;
    }

    return editButton.getAttribute(
        "data-id"
    );
    """

    entry_address_id = driver.execute_script(
        extract_address_script,
        address_result["body"]
    )

    if not entry_address_id:

        print(
            "[-] Could not find EntryAddress ID."
        )

        print(
            address_result["body"][:2000]
        )

        raise RuntimeError(
            "EntryAddress ID was not found."
        )

    entry_address_id = int(
        entry_address_id
    )

    print(
        f"[+] Entry Address ID: "
        f"{entry_address_id}"
    )

    # =========================================================
    # CREATE EMAIL UPDATE PAYLOAD
    # =========================================================

    print("\n" + "=" * 60)
    print(" ADDING EMAIL")
    print("=" * 60)

    print(
        f"Adding email: {EMAIL}"
    )

    email_payload = {

        "id": entry_address_id,

        "vm": {

            "__ChangedFields": [
                "Email"
            ],

            "Email": EMAIL
        },

        "handler": {

            "_error": {

                "_autoFix": False,

                "_autoIgnore": False
            }
        }
    }

    # =========================================================
    # UPDATE EMAIL
    # =========================================================

    email_fetch_script = """
    const callback = arguments[arguments.length - 1];

    const token = arguments[0];
    const payload = arguments[1];

    fetch(
        "/StarRezWeb/Main/EntryAddress/EditData",
        {

            method: "POST",

            headers: {

                "__requestverificationtoken":
                    token,

                "Accept":
                    "application/json, text/javascript, */*; q=0.01",

                "Content-Type":
                    "application/json; charset=UTF-8",

                "X-Requested-With":
                    "XMLHttpRequest"
            },

            credentials: "include",

            body: JSON.stringify(payload)
        }
    )
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

    email_result = driver.execute_async_script(
        email_fetch_script,
        anti_forgery_token,
        email_payload
    )

    print(
        "\nEmail update status:",
        email_result["status"]
    )

    if not email_result["ok"]:

        print(
            "[-] Failed to add email."
        )

        print(
            email_result["body"][:2000]
        )

        raise RuntimeError(
            "Email update failed."
        )

    print(
        f"[+] Email successfully added: "
        f"{EMAIL}"
    )

    # =========================================================
    # FINISHED
    # =========================================================

    print("\n" + "=" * 60)
    print(" SUCCESS")
    print("=" * 60)

    print(
        f"Name:             "
        f"{FIRST_NAME} {LAST_NAME}"
    )

    print(
        f"Entry ID:         "
        f"{entry_id}"
    )

    print(
        f"Entry Address ID: "
        f"{entry_address_id}"
    )

    print(
        f"Email:            "
        f"{EMAIL}"
    )

    print("=" * 60)


finally:

    # Give you a moment to see the final browser state.
    time.sleep(2)

    driver.quit()
