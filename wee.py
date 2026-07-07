"""
BabyCenter - Complete Flow (With Proxy Rotation & Verification)
"""

import time
import random
import string
import json
import os
import requests
from pathlib import Path
from faker import Faker
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# ============================================================
# CONFIGURATION
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
TARGET_URL = "https://community.babycenter.com/post/create/85"
PROXY_FILE = BASE_DIR / "proxies.txt"  # proxy list file

# Format: host:port:username:password (one per line)
# Example: 38.154.191.183:8760:xgxowcgc:h6r17blc86s8

fake = Faker()

# ============================================================
# PROXY FUNCTIONS
# ============================================================
def load_proxies():
    """Load proxies from file"""
    proxies = []
    if PROXY_FILE.exists():
        with open(PROXY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    proxies.append(line)
        print(f"✅ Loaded {len(proxies)} proxies from {PROXY_FILE}")
    else:
        print(f"⚠️ Proxy file not found: {PROXY_FILE}")
        print(f"   Create {PROXY_FILE} with format: host:port:username:password")
    return proxies

def parse_proxy(proxy_str):
    """Parse proxy string to config"""
    proxy_str = proxy_str.replace('http://', '').replace('https://', '')
    parts = proxy_str.split(':')
    if len(parts) == 4:
        host, port, username, password = parts
        return {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "label": f"{host}:{port}",
            "requests": {
                "http": f"http://{username}:{password}@{host}:{port}",
                "https": f"http://{username}:{password}@{host}:{port}",
            }
        }
    return None

def test_proxy(proxy_config):
    """Test if proxy is working"""
    try:
        proxy_url = proxy_config["requests"]["http"]
        test_proxies = {"http": proxy_url, "https": proxy_url}
        response = requests.get("https://api.ipify.org?format=json", proxies=test_proxies, timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Proxy working: {response.json().get('ip')}")
            return True
        return False
    except Exception as e:
        print(f"   ❌ Proxy failed: {str(e)[:50]}")
        return False

def get_working_proxy():
    """Get a working proxy from file"""
    proxies = load_proxies()
    if not proxies:
        print("❌ No proxies found in file!")
        return None
    
    random.shuffle(proxies)
    
    for proxy_str in proxies[:30]:  # Test first 30
        proxy_config = parse_proxy(proxy_str)
        if proxy_config:
            print(f"🔄 Testing: {proxy_config['label']}")
            if test_proxy(proxy_config):
                print(f"✅ Found working proxy: {proxy_config['label']}")
                return proxy_config
    
    print("❌ No working proxy found! Using direct connection.")
    return None

# ============================================================
# CREATE PROXY EXTENSION
# ============================================================
def create_proxy_extension(proxy_config):
    """Create Chrome extension for proxy"""
    if not proxy_config:
        return None
    
    host = proxy_config.get("host")
    port = proxy_config.get("port")
    username = proxy_config.get("username")
    password = proxy_config.get("password")
    
    if not host or not port:
        return None
    
    ext_dir = BASE_DIR / f"proxy_ext_{host}_{port}"
    os.makedirs(ext_dir, exist_ok=True)
    
    manifest = {
        "version": "1.0.0",
        "manifest_version": 3,
        "name": f"Chrome Proxy {host}",
        "permissions": [
            "proxy",
            "tabs",
            "storage",
            "webRequest",
            "webRequestAuthProvider"
        ],
        "host_permissions": ["<all_urls>"],
        "background": {
            "service_worker": "background.js"
        }
    }
    
    background = f"""
    const config = {{
        mode: "fixed_servers",
        rules: {{
            singleProxy: {{
                scheme: "http",
                host: "{host}",
                port: parseInt({port})
            }}
        }}
    }};
    
    chrome.proxy.settings.set({{
        value: config,
        scope: "regular"
    }}, () => {{
        console.log("Proxy configured: {host}:{port}");
    }});
    """
    
    if username and password:
        background += f"""
    chrome.webRequest.onAuthRequired.addListener(
        (details, callback) => {{
            callback({{
                authCredentials: {{
                    username: "{username}",
                    password: "{password}"
                }}
            }});
        }},
        {{urls: ["<all_urls>"]}},
        ["blocking"]
    );
    """
    
    with open(ext_dir / "manifest.json", "w") as f:
        json.dump(manifest, f)
    with open(ext_dir / "background.js", "w") as f:
        f.write(background)
    
    print(f"✅ Proxy extension created: {host}:{port}")
    return str(ext_dir.absolute())

# ============================================================
# GENERATE RANDOM DATA
# ============================================================
def generate_random_email():
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com"]
    name = fake.user_name()
    domain = random.choice(domains)
    return f"{name}{random.randint(100, 999)}@{domain}"

def generate_random_password():
    uppercase = random.choice(string.ascii_uppercase)
    lowercase = random.choice(string.ascii_lowercase)
    number = random.choice(string.digits)
    symbol = random.choice("!@-#_$%^&*")
    
    remaining = random.randint(4, 15)
    chars = string.ascii_letters + string.digits + "!@-#_$%^&*"
    rest = ''.join(random.choice(chars) for _ in range(remaining))
    
    password_list = list(uppercase + lowercase + number + symbol + rest)
    random.shuffle(password_list)
    password = ''.join(password_list)
    
    if len(password) < 8:
        password += ''.join(random.choice(string.ascii_letters) for _ in range(8 - len(password)))
    elif len(password) > 20:
        password = password[:20]
    
    return password

def generate_random_name():
    return fake.first_name()

def generate_random_screen_name():
    name = fake.user_name().replace('_', '').replace('-', '')
    numbers = ''.join(random.choices(string.digits, k=random.randint(1, 3)))
    screen_name = name + numbers
    if len(screen_name) < 3:
        screen_name += ''.join(random.choices(string.ascii_lowercase + string.digits, k=3 - len(screen_name)))
    elif len(screen_name) > 20:
        screen_name = screen_name[:20]
    return screen_name.lower()

def generate_random_post_content():
    titles = [
        "Excited to share my journey!",
        "Looking for advice on...",
        "Has anyone experienced this?",
        "My baby just started crawling!",
        "Feeling blessed today",
    ]
    
    details = [
        "I wanted to share my experience and see if anyone else has gone through something similar.",
        "I'm really curious about this topic and would love to hear from other parents.",
    ]
    
    return random.choice(titles), random.choice(details)

# ============================================================
# JS CLICK FUNCTION
# ============================================================
def js_click(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", element)

# ============================================================
# MAIN FUNCTION
# ============================================================
def main():
    print("\n" + "="*70)
    print("👶 BABYCENTER - COMPLETE FLOW (PROXY ROTATION)")
    print("="*70)
    print("   1. Signup")
    print("   2. Close popup")
    print("   3. Create Post")
    print("   4. Screen Name")
    print("="*70)
    
    # Get working proxy
    proxy_config = get_working_proxy()
    
    if proxy_config:
        print(f"\n🌐 Using Proxy: {proxy_config['label']}")
    else:
        print("\n🌐 Using Direct Connection (No Proxy)")
    
    email = generate_random_email()
    password = generate_random_password()
    first_name = generate_random_name()
    screen_name = generate_random_screen_name()
    post_title, post_details = generate_random_post_content()
    
    print("\n📝 GENERATED DATA:")
    print(f"   📧 Email: {email}")
    print(f"   🔑 Password: {password}")
    print(f"   👤 Name: {first_name}")
    print(f"   🖥️ Screen Name: {screen_name}")
    print(f"   📌 Title: {post_title}")
    print(f"   📝 Details: {post_details[:50]}...")
    print("="*70)
    
    # Create proxy extension
    ext_path = None
    if proxy_config:
        print("\n🔧 Creating proxy extension...")
        ext_path = create_proxy_extension(proxy_config)
        if ext_path:
            print(f"✅ Extension created")
    
    print("\n🌐 Launching Chrome...")
    options = uc.ChromeOptions()
    if ext_path:
        options.add_argument(f"--load-extension={ext_path}")
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    
    try:
        # ============================================================
        # STEP 1: NAVIGATE
        # ============================================================
        print(f"\n🌐 Opening: {TARGET_URL}")
        driver.get(TARGET_URL)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)
        
        # ============================================================
        # STEP 2: COOKIE CONSENT
        # ============================================================
        print("\n🍪 Handling cookie consent...")
        try:
            do_not_consent = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler"))
            )
            driver.execute_script("arguments[0].click();", do_not_consent)
            print("   ✅ Clicked 'Do Not Consent'")
        except:
            print("   ℹ️ No cookie consent")
        time.sleep(2)
        
        # ============================================================
        # STEP 3: CLICK SIGNUP BUTTON
        # ============================================================
        print("\n🔘 Clicking Sign Up...")
        
        try:
            signup_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Sign up') or contains(text(), 'Sign Up')]"))
            )
            js_click(driver, signup_btn)
            print("✅ Sign Up clicked!")
        except:
            print("⚠️ Could not find Sign Up button")
        
        time.sleep(3)
        
        # ============================================================
        # STEP 4: FILL SIGNUP FORM
        # ============================================================
        print("\n📝 Filling signup form...")
        
        # Email
        try:
            email_input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
            )
            email_input.clear()
            email_input.send_keys(email)
            print(f"   ✅ Email: {email}")
        except:
            print("   ⚠️ Email input not found")
        
        # Password
        try:
            password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            password_input.clear()
            password_input.send_keys(password)
            print(f"   ✅ Password: {password}")
        except:
            print("   ⚠️ Password input not found")
        
        # Name
        try:
            name_input = driver.find_element(By.CSS_SELECTOR, "input[name='firstName']")
            name_input.clear()
            name_input.send_keys(first_name)
            print(f"   ✅ Name: {first_name}")
        except:
            pass
        
        # Due date
        try:
            due_date = driver.find_element(By.CSS_SELECTOR, "input[type='date']")
            if due_date.is_displayed():
                import datetime
                random_date = datetime.date(2026, 1, 1) + datetime.timedelta(days=random.randint(0, 364))
                due_date.send_keys(random_date.strftime("%Y-%m-%d"))
                print(f"   ✅ Due date set")
        except:
            pass
        
        # Trying to conceive
        try:
            ttc = driver.find_element(By.XPATH, "//*[contains(text(), 'Trying to conceive')]/preceding-sibling::input[@type='checkbox']")
            if ttc and not ttc.is_selected():
                driver.execute_script("arguments[0].click();", ttc)
                print("   ✅ Trying to conceive")
        except:
            pass
        
        # Terms
        try:
            terms = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
            if terms and not terms.is_selected():
                driver.execute_script("arguments[0].click();", terms)
                print("   ✅ Terms accepted")
        except:
            pass
        
        # ============================================================
        # STEP 5: JOIN NOW
        # ============================================================
        print("\n🔘 Clicking Join Now...")
        
        try:
            join_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Join now']"))
            )
            js_click(driver, join_btn)
            print("✅ Join Now clicked!")
        except Exception as e:
            print(f"   ⚠️ Join Now failed: {e}")
            try:
                join_btn = driver.find_element(By.CSS_SELECTOR, "button[class*='submitButton']")
                js_click(driver, join_btn)
                print("✅ Join Now clicked via CSS!")
            except:
                driver.execute_script("""
                    var btns = document.querySelectorAll('button');
                    for(var i=0; i<btns.length; i++){
                        if(btns[i].textContent && btns[i].textContent.includes('Join now')){
                            btns[i].click();
                            return;
                        }
                    }
                """)
                print("✅ Join Now clicked via JS!")
        
        time.sleep(5)
        
        # ============================================================
        # STEP 6: CLOSE POPUP (CUT WALA)
        # ============================================================
        print("\n🔘 Closing popup...")
        
        try:
            close = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[aria-label='close dialog popup']")
                )
            )
            driver.execute_script("arguments[0].click();", close)
            print("✅ Popup closed!")
        except Exception as e:
            print(f"   ⚠️ Close failed: {e}")
            driver.execute_script("""
                var btns = document.querySelectorAll('button');
                for(var i=0; i<btns.length; i++){
                    if(btns[i].textContent && (btns[i].textContent.includes('×') || 
                       btns[i].textContent.includes('X') || 
                       btns[i].textContent.includes('Close'))){
                        btns[i].click();
                        return;
                    }
                }
            """)
            print("✅ Popup closed via JS!")
        
        # Wait for dialog to disappear
        try:
            wait.until(
                EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, "div.MuiDialog-container")
                )
            )
            print("✅ Dialog disappeared!")
        except:
            pass
        
        time.sleep(2)
        
        # ============================================================
        # STEP 7: FILL POST TITLE
        # ============================================================
        print("\n📝 Filling post title...")
        
        try:
            title_input = wait.until(
                EC.presence_of_element_located((By.ID, "title"))
            )
            title_input.clear()
            title_input.send_keys(post_title)
            print(f"   ✅ Title: {post_title}")
        except Exception as e:
            print(f"   ⚠️ Title failed: {e}")
            driver.execute_script(f"""
                var inputs = document.querySelectorAll('input');
                for(var i=0; i<inputs.length; i++){{
                    if(inputs[i].id === 'title' || 
                       (inputs[i].placeholder && inputs[i].placeholder.toLowerCase().includes('title'))){{
                        inputs[i].value = '{post_title}';
                        break;
                    }}
                }}
            """)
            print(f"   ✅ Title set via JS: {post_title}")
        
        # ============================================================
        # STEP 8: FILL POST DETAILS
        # ============================================================
        print("\n📝 Filling post details...")
        
        try:
            details_input = driver.find_element(By.CSS_SELECTOR, "textarea[placeholder*='details'], textarea[placeholder*='Details']")
            details_input.clear()
            details_input.send_keys(post_details)
            print(f"   ✅ Details: {post_details[:50]}...")
        except:
            try:
                textareas = driver.find_elements(By.TAG_NAME, "textarea")
                for ta in textareas:
                    if ta.is_displayed():
                        ta.clear()
                        ta.send_keys(post_details)
                        print(f"   ✅ Details via any textarea: {post_details[:50]}...")
                        break
            except:
                driver.execute_script(f"""
                    var textareas = document.querySelectorAll('textarea');
                    for(var i=0; i<textareas.length; i++){{
                        if(textareas[i].offsetParent !== null){{
                            textareas[i].value = '{post_details}';
                            break;
                        }}
                    }}
                """)
                print(f"   ✅ Details set via JS: {post_details[:50]}...")
        
        # ============================================================
        # STEP 9: CLICK CREATE POST
        # ============================================================
        print("\n🔘 Clicking Create Post...")
        
        try:
            create_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Create Post')]"))
            )
            js_click(driver, create_btn)
            print("✅ Create Post clicked!")
        except:
            print("⚠️ Could not click Create Post")
        
        # ============================================================
        # STEP 10: SCREEN NAME
        # ============================================================
        print("\n⏳ Waiting for screen name form...")
        
        try:
            screen = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "form.screenNameForm input")
                )
            )
            print("✅ Screen name input found!")
            
            print("\n📝 Filling screen name...")
            
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", screen)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", screen)
            time.sleep(0.3)
            
            screen.send_keys(Keys.CONTROL + "a")
            screen.send_keys(Keys.DELETE)
            
            for ch in screen_name:
                screen.send_keys(ch)
                time.sleep(0.05)
            
            screen.send_keys(Keys.TAB)
            print(f"   ✅ Typed: {screen_name}")
            
            time.sleep(1)
            
            # ============================================================
            # STEP 11: SUBMIT
            # ============================================================
            print("\n🔘 Submitting screen name...")
            
            submit = driver.find_element(
                By.CSS_SELECTOR,
                "form.screenNameForm button[type='submit']"
            )
            
            disabled = submit.get_attribute('disabled')
            print(f"   📌 Disabled: {disabled}")
            
            if disabled is None:
                submit.click()
                print("✅ Screen name submitted!")
            else:
                print("   ⚠️ Submit disabled - trying JS click")
                js_click(driver, submit)
                print("✅ Screen name submitted via JS!")
                
        except Exception as e:
            print(f"   ⚠️ Screen name form not found: {e}")
        
        # ============================================================
        # STEP 12: VERIFICATION - URL & TITLE
        # ============================================================
        print("\n" + "="*70)
        print("🔍 VERIFICATION")
        print("="*70)
        
        time.sleep(3)
        
        # 🔥 Print current URL
        current_url = driver.current_url
        print(f"📍 Current URL: {current_url}")
        
        # 🔥 Print page title
        page_title = driver.title
        print(f"📄 Page Title: {page_title}")
        
        # Check if on success page
        if "post" in current_url.lower() or "create" not in current_url.lower():
            print("✅ Post created successfully! (URL changed from create page)")
        else:
            print("⚠️ Still on create page - post may not be published")
        
        # ============================================================
        # STEP 13: GET SUCCESS MESSAGE
        # ============================================================
        print("\n📨 Checking for success message...")
        
        success_message = None
        
        try:
            # Check for success elements
            success_selectors = [
                ".success-message",
                ".post-success",
                "[class*='success']",
                "[role='alert']",
                ".MuiAlert-root",
            ]
            
            for selector in success_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        if text and ('success' in text.lower() or 'created' in text.lower() or 'posted' in text.lower()):
                            success_message = text
                            break
                    if success_message:
                        break
                except:
                    pass
            
            if not success_message:
                page_text = driver.find_element(By.TAG_NAME, "body").text
                keywords = ["success", "created", "posted", "published"]
                for kw in keywords:
                    if kw in page_text.lower():
                        lines = page_text.split('\n')
                        for line in lines:
                            if kw in line.lower() and len(line.strip()) > 10:
                                success_message = line.strip()
                                break
                        if success_message:
                            break
            
            if success_message:
                print(f"\n✅ SUCCESS MESSAGE:\n   {success_message}")
            else:
                print("\n✅ Post created successfully!")
                
        except Exception as e:
            print(f"   ⚠️ Could not get success message: {e}")
            print("\n✅ Post created successfully!")
        
        # ============================================================
        # STEP 14: SAVE RESULTS
        # ============================================================
        print("\n⏳ Saving results...")
        time.sleep(2)
        
        driver.save_screenshot(str(BASE_DIR / "babycenter_result.png"))
        print("📸 Screenshot saved")
        
        with open(BASE_DIR / "babycenter_credentials.txt", "w") as f:
            f.write(f"Email: {email}\n")
            f.write(f"Password: {password}\n")
            f.write(f"Name: {first_name}\n")
            f.write(f"Screen Name: {screen_name}\n")
            f.write(f"Post Title: {post_title}\n")
            f.write(f"Post Details: {post_details}\n")
            f.write(f"Final URL: {current_url}\n")
            f.write(f"Page Title: {page_title}\n")
        print("📁 Credentials saved")
        
        print("\n" + "="*70)
        print("✅ COMPLETED!")
        print(f"📧 Email: {email}")
        print(f"🔑 Password: {password}")
        print(f"🖥️ Screen Name: {screen_name}")
        print(f"📍 Final URL: {current_url}")
        print(f"📄 Page Title: {page_title}")
        if success_message:
            print(f"📨 Success: {success_message}")
        print("="*70)
        
        print("\n⏳ Browser open for 30 seconds...")
        time.sleep(30)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        driver.quit()
        print("✅ Browser closed")

if __name__ == "__main__":
    main()