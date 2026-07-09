from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from API.utilities.helpers import clean_and_parse_count, get_element_text_with_emojis

class YouTubeLiveScraper:
    def __init__(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless=new')
        self.options.add_argument('--mute-audio')
        self.options.add_argument('--log-level=3')
        self.options.add_argument('--window-size=1920,1080')
        self.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')

    def get_video_title(self, driver):
            title = "ไม่ทราบชื่อคลิป"
            try:
                title_el = driver.find_element(By.CSS_SELECTOR, "yt-formatted-string.ytd-watch-metadata")
                title = title_el.text.strip()
                if not title:
                    title = title_el.get_attribute("title").strip()
            except Exception:
                try:
                    title = driver.title.replace(" - YouTube", "").strip()
                except Exception:
                    pass
                    
            return title

    def get_viewer_count(self, driver):
        viewers = 0
        try:
            view_el = driver.find_element(By.ID, "view-count")
            aria_label = view_el.get_attribute("aria-label")
            if aria_label:
                viewers = aria_label.strip()
            else:
                viewers = view_el.text.strip()
        except Exception:
            pass

        return clean_and_parse_count(viewers)

    def get_chat_messages(self, driver):
        messages = []
        try:
            WebDriverWait(driver, 15).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "chatframe"))
            )
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "yt-live-chat-text-message-renderer"))
            )

            elements = driver.find_elements(By.TAG_NAME, "yt-live-chat-text-message-renderer")
            
            for el in elements:
                try:
                    author = el.find_element(By.ID, "author-name").text.strip()
                    message_el = el.find_element(By.ID, "message")
                    message = get_element_text_with_emojis(driver, message_el)
                    if len(message) > 0:
                        messages.append({"id": len(messages) + 1, "sender": author[1::], "message": message})
                except Exception:
                    continue
            
            driver.switch_to.default_content()
        except Exception:
            pass
            
        return messages

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def fetch_live_data(self, url: str) -> dict:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=self.options)
        
        result = {
            "status": "success",
            "url": url,
            "title": "",
            "viewers": "",
            "chat_messages": [],
            "error_message": None
        }

        try:
            driver.get(url)
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, "style-scope ytd-watch-info-text"))
                )
            except Exception:
                pass

            result["title"] = self.get_video_title(driver)
            result["viewers"] = self.get_viewer_count(driver)
            result["chat_messages"] = self.get_chat_messages(driver)

        except Exception as e:
            result["status"] = "error"
            result["error_message"] = str(e)
        
        finally:
            driver.quit()
            
        return result