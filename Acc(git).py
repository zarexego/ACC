import os
import json
import time
import getpass
import logging
import hashlib
import hmac
import subprocess
import shutil
import platform
from pathlib import Path

APP_NAME = "Privacy Launcher"
BASE_DIR = Path(__file__).resolve().parent
USERS_FILE = BASE_DIR / "users.json"
CONFIG_FILE = BASE_DIR / "config.json"
EXAMPLE_CONFIG_FILE = BASE_DIR / "config.example.json"
LOG_FILE = BASE_DIR / ".audit.log"

DEFAULT_CONFIG = {
    "browser_paths": {
        "Firefox": [
            ["firefox", "--private-window"],
            ["/usr/bin/firefox", "--private-window"]
        ],
        "Brave": [
            ["flatpak", "run", "com.brave.Browser"],
            ["brave-browser", "--incognito"],
            ["brave", "--incognito"]
        ],
        "Tor Browser": [
            ["/path/to/tor-browser/start-tor-browser.desktop"]
        ]
    },
    "fallback_open": ["xdg-open"]
}

SITES = {
    "1": ("VK", "https://vk.com"),
    "2": ("Google Translate", "https://translate.google.com"),
    "3": ("Gmail", "https://mail.google.com"),
    "4": ("Mail.ru", "https://mail.ru"),
    "5": ("Reddit", "https://www.reddit.com"),
    "6": ("DuckDuckGo", "https://duckduckgo.com"),
    "7": ("YouTube", "https://www.youtube.com"),
    "8": ("GitHub", "https://github.com")
}

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def log_event(message):
    logging.info(message)

def load_json(path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def ensure_config_files():
    if not CONFIG_FILE.exists():
        save_json(CONFIG_FILE, DEFAULT_CONFIG)
    if not EXAMPLE_CONFIG_FILE.exists():
        save_json(EXAMPLE_CONFIG_FILE, DEFAULT_CONFIG)

def load_users():
    return load_json(USERS_FILE, {})

def save_users(users):
    save_json(USERS_FILE, users)

def load_config():
    ensure_config_files()
    return load_json(CONFIG_FILE, DEFAULT_CONFIG)

def hash_password(password, salt=None, iterations=200000):
    if salt is None:
        salt = os.urandom(16)
    elif isinstance(salt, str):
        salt = bytes.fromhex(salt)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return salt.hex(), pwd_hash.hex(), iterations

def verify_password(password, salt_hex, hash_hex, iterations):
    _, new_hash, _ = hash_password(password, salt_hex, iterations)
    return hmac.compare_digest(new_hash, hash_hex)

def clear_screen():
    if platform.system().lower() == "windows":
        subprocess.run("cls", shell=True, check=False)
    else:
        subprocess.run(["clear"], check=False)

def banner():
    print(f"===== {APP_NAME} =====")
    print("Privacy launcher for Linux")
    print(f"System: {platform.system()} {platform.release()}")
    print()

def browser_variant_available(variant):
    if not variant:
        return False
    first = variant[0]
    if first.startswith("/"):
        return Path(first).exists()
    if first.endswith(".desktop"):
        return Path(first).exists()
    if first == "flatpak" and len(variant) >= 3 and variant[1] == "run":
        return shutil.which("flatpak") is not None
    return shutil.which(first) is not None

def resolve_browser_command(variants):
    for variant in variants:
        if browser_variant_available(variant):
            return variant
    return None

def build_available_browsers(config):
    available = {}
    for name, variants in config["browser_paths"].items():
        cmd = resolve_browser_command(variants)
        if cmd:
            available[name] = cmd
    return available

def open_url(browser_cmd, url):
    try:
        if browser_cmd[0].endswith(".desktop"):
            desktop_path = Path(browser_cmd[0])
            subprocess.Popen([str(desktop_path)], cwd=str(desktop_path.parent))
        else:
            subprocess.Popen(browser_cmd + [url])
    except Exception:
        subprocess.Popen(["xdg-open", url])

def register(users):
    clear_screen()
    banner()
    print("--- REGISTRATION ---")
    username = input("Choose username: ").strip()

    if not username:
        print("Username cannot be empty.")
        time.sleep(1)
        return None

    if username in users:
        print("User already exists.")
        time.sleep(1)
        return None

    password = getpass.getpass("Choose password: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        print("Passwords do not match.")
        time.sleep(1)
        return None

    salt, pwd_hash, iterations = hash_password(password)
    users[username] = {
        "salt": salt,
        "hash": pwd_hash,
        "iterations": iterations
    }
    save_users(users)
    log_event(f"SUCCESS: New user registered: {username}")
    print("Registration successful.")
    time.sleep(1)
    return username

def login(users):
    clear_screen()
    banner()
    print("--- LOGIN ---")
    username = input("Username: ").strip()

    if username not in users:
        print("User not found.")
        log_event(f"ALERT: Login failed for unknown user: {username}")
        time.sleep(1)
        return None

    password = getpass.getpass("Password: ")
    data = users[username]

    if verify_password(password, data["salt"], data["hash"], data["iterations"]):
        log_event(f"SUCCESS: User authenticated: {username}")
        print("Login successful.")
        time.sleep(1)
        return username

    log_event(f"ALERT: Failed login for user: {username}")
    print("Invalid password.")
    time.sleep(1)
    return None

def choose_browser(available_browsers):
    clear_screen()
    banner()
    print("--- CHOOSE BROWSER ---")

    names = list(available_browsers.keys())
    if not names:
        print("No browser found.")
        time.sleep(2)
        return None, None

    for i, name in enumerate(names, start=1):
        print(f"{i}. {name}")

    print("0. Back")
    choice = input("Select browser: ").strip()

    if choice == "0":
        return "BACK", None

    if choice.isdigit() and 1 <= int(choice) <= len(names):
        name = names[int(choice) - 1]
        return name, available_browsers[name]

    return None, None

def browse_menu(browser_name, browser_cmd):
    while True:
        clear_screen()
        banner()
        print(f"Selected browser: {browser_name}")
        print("1. VK")
        print("2. Google Translate")
        print("3. Gmail")
        print("4. Mail.ru")
        print("5. Reddit")
        print("6. DuckDuckGo")
        print("7. YouTube")
        print("8. GitHub")
        print("9. Open custom URL")
        print("0. Back to browser menu")
        print("L. Logout")

        choice = input("Select option: ").strip().lower()

        if choice == "l":
            log_event("INFO: User logged out")
            return "logout"

        if choice == "0":
            return "back"

        if choice in SITES:
            site_name, url = SITES[choice]
            log_event(f"ACTION: Opened {site_name} in {browser_name}")
            open_url(browser_cmd, url)
            time.sleep(1)
            continue

        if choice == "9":
            url = input("Enter URL: ").strip()
            if url:
                log_event(f"ACTION: Opened custom URL in {browser_name}: {url}")
                open_url(browser_cmd, url)
                time.sleep(1)
            continue

        print("Invalid option.")
        time.sleep(1)

def settings_menu(config):
    while True:
        clear_screen()
        banner()
        print("--- SETTINGS ---")
        print("1. Show browser config")
        print("2. Restore default config")
        print("0. Back")

        choice = input("Select: ").strip()

        if choice == "1":
            clear_screen()
            banner()
            print(json.dumps(config, indent=2, ensure_ascii=False))
            input("Press Enter to continue...")
        elif choice == "2":
            save_json(CONFIG_FILE, DEFAULT_CONFIG)
            config.clear()
            config.update(load_config())
            print("Default config restored.")
            time.sleep(1)
        elif choice == "0":
            break
        else:
            print("Invalid option.")
            time.sleep(1)

def main():
    users = load_users()
    config = load_config()

    while True:
        clear_screen()
        banner()
        print("1. Login")
        print("2. Register")
        print("3. Settings")
        print("0. Exit")

        choice = input("Select: ").strip()

        if choice == "1":
            user = login(users)
            if user:
                while True:
                    available_browsers = build_available_browsers(config)
                    browser_name, browser_cmd = choose_browser(available_browsers)

                    if browser_name == "BACK":
                        break

                    if not browser_name:
                        print("Invalid browser choice.")
                        time.sleep(1)
                        continue

                    result = browse_menu(browser_name, browser_cmd)

                    if result == "logout":
                        break
                    if result == "back":
                        continue

        elif choice == "2":
            register(users)

        elif choice == "3":
            settings_menu(config)

        elif choice == "0":
            print("Goodbye!")
            log_event("INFO: Application exited")
            break

        else:
            print("Invalid option.")
            time.sleep(1)

if __name__ == "__main__":
    main()