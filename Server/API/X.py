import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from API.utilities.helpers import clean_and_parse_count, get_element_text_with_emojis

class XLiveScraper:
    def __init__(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless=new')
        self.options.add_argument('--mute-audio')
        self.options.add_argument('--log-level=3')
        self.options.add_argument('--window-size=1920,1080')
        self.options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-notifications')

    def is_active_live(self, driver) -> bool:
        try:
            players = driver.find_elements(
                By.XPATH,
                "//*[@data-testid='videoPlayer' or @data-testid='videoComponent']"
            )
            for player in players:
                p_text = player.text
                if "LIVE" in p_text.upper() or "สด" in p_text:
                    return True

            # Fall back to any visible LIVE badge element
            badges = driver.find_elements(
                By.XPATH,
                "//*[text()='LIVE' or text()='Live' or text()='สด']"
            )
            for badge in badges:
                if badge.is_displayed():
                    return True
        except Exception as e:
            print(f"  [X] Error checking live status: {e}")
        return False

    def get_live_status(self, driver, broadcast_url: str) -> dict:
        result = {"is_live": False, "viewers": 0, "title": ""}

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                print(f"  [X] Retrying broadcast page load (attempt {attempt}/{max_attempts})...")
            try:
                # --- Load the page ---
                page_loaded = False
                try:
                    driver.set_page_load_timeout(15)
                except Exception:
                    pass
                try:
                    driver.get(broadcast_url)
                    page_loaded = True
                except Exception as get_err:
                    print(f"  [X] Page load timed out or errored on attempt {attempt}: {get_err}")
                finally:
                    try:
                        driver.set_page_load_timeout(20)
                    except Exception:
                        pass

                if not page_loaded:
                    continue

                # Wait briefly for the page to settle
                try:
                    WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.TAG_NAME, "article"))
                    )
                except Exception:
                    pass  # Continue even if no articles found

                time.sleep(3)

                # --- Check active live badge ---
                if not self.is_active_live(driver):
                    print(f"  [X] Stream is not currently live (ended or normal video): {broadcast_url}")
                    break

                # --- Extract viewer count ---
                xpath_query = (
                    "//*[contains(text(), 'watching') or contains(text(), 'Watching') "
                    "or contains(text(), 'view') or contains(text(), 'View') "
                    "or contains(text(), 'คนดู') or contains(text(), 'ผู้ชม')]"
                )
                elements = driver.find_elements(By.XPATH, xpath_query)
                found_viewers = 0
                for el in elements:
                    try:
                        t = el.text.strip()
                        if t and (
                            "watching" in t.lower()
                            or "view" in t.lower()
                            or "คนดู" in t
                            or "ผู้ชม" in t
                        ):
                            val = clean_and_parse_count(t)
                            if val > 0:
                                print(f"  [X] Found viewer count in DOM (attempt {attempt}): {val} ('{t}')")
                                found_viewers = val
                                break
                    except Exception:
                        pass

                result["is_live"] = True
                result["viewers"] = found_viewers
                result["title"] = self.get_video_title(driver)
                break

            except Exception as e:
                print(f"  [X] Error on attempt {attempt}: {e}")

        return result

    def get_viewer_count(self, driver) -> int:
        xpath_query = (
            "//*[contains(text(), 'watching') or contains(text(), 'Watching') "
            "or contains(text(), 'view') or contains(text(), 'View') "
            "or contains(text(), 'คนดู') or contains(text(), 'ผู้ชม')]"
        )
        elements = driver.find_elements(By.XPATH, xpath_query)
        for el in elements:
            try:
                t = el.text.strip()
                if t and (
                    "watching" in t.lower()
                    or "view" in t.lower()
                    or "คนดู" in t
                    or "ผู้ชม" in t
                ):
                    val = clean_and_parse_count(t)
                    if val > 0:
                        return val
            except Exception:
                pass
        return 0

    def get_video_title(self, driver) -> str:
        # Try <title> tag first
        try:
            title = driver.title
            if title and title.strip() and title.strip().lower() not in ("x", "twitter"):
                return title.strip()
        except Exception:
            pass

        # Fall back to og:title meta tag
        try:
            og_title = driver.find_element(
                By.CSS_SELECTOR, "meta[property='og:title']"
            ).get_attribute("content")
            if og_title and og_title.strip():
                return og_title.strip()
        except Exception:
            pass

        # Fall back to prominent heading text
        try:
            headings = driver.find_elements(By.XPATH, "//h1 | //h2")
            for h in headings:
                t = h.text.strip()
                if t:
                    return t
        except Exception:
            pass

        return "X Broadcast"

    def get_chat_messages(self, driver) -> list:
        messages = []
        try:
            tweet_elements = driver.find_elements(
                By.CSS_SELECTOR, "[data-testid='tweet']"
            )
            for tweet in tweet_elements:
                try:
                    # Sender username
                    user_el = tweet.find_element(
                        By.CSS_SELECTOR, "[data-testid='User-Name']"
                    )
                    user_text_full = get_element_text_with_emojis(driver, user_el)
                    username = user_text_full.split('\n')[0].strip()

                    # Message body
                    text_el = tweet.find_element(
                        By.CSS_SELECTOR, "[data-testid='tweetText']"
                    )
                    msg_text = get_element_text_with_emojis(driver, text_el)

                    if username or msg_text:
                        messages.append({"id": len(messages) + 1, "sender": username, "message": msg_text})
                except Exception:
                    pass
        except Exception as e:
            print(f"  [X] Comment parse error: {e}")
        return messages

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def fetch_live_data(self, url: str) -> dict:
        broadcast_url = url.split('?')[0].rstrip('/')

        result = {
            "status": "success",
            "url": url,
            "broadcast_url": broadcast_url,
            "title": "",
            "is_live": False,
            "viewers": 0,
            "chat_messages": [],
            "error_message": None,
        }

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=self.options)

        try:
            print(f"  [X] Loading broadcast: {broadcast_url}")
            live_status = self.get_live_status(driver, broadcast_url)
            result["is_live"] = live_status["is_live"]
            result["viewers"] = live_status["viewers"]
            result["title"] = live_status["title"]

            if live_status["is_live"]:
                print(f"  [X] Broadcast is LIVE. Scraping chat messages...")
                result["chat_messages"] = self.get_chat_messages(driver)
            else:
                print(f"  [X] Broadcast is NOT live on {broadcast_url}.")

        except Exception as e:
            result["status"] = "error"
            result["error_message"] = str(e)

        finally:
            driver.quit()

        return result
