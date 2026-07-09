import re
import time
from selenium import webdriver
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from API.utilities.helpers import clean_and_parse_count, get_element_text_with_emojis

class FacebookLiveScraper:
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
        self.options.add_argument('--disable-notifications')

    def _close_dialogs(self, driver):
        try:
            dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
            if dialogs:
                xpaths = [
                    "//div[@role='dialog']//div[@aria-label='Close']", 
                    "//div[@role='dialog']//div[@aria-label='ปิด']", 
                    "//div[@aria-label='Close']", 
                    "//div[@aria-label='ปิด']"
                ]
                for xpath in xpaths:
                    try:
                        close_btn = driver.find_element(By.XPATH, xpath)
                        if close_btn.is_displayed():
                            driver.execute_script("arguments[0].click();", close_btn)
                            time.sleep(1)
                            break
                    except Exception:
                        pass
        except Exception:
            pass

    def get_video_title(self, driver):
        try:
            script = """
            let els = document.querySelectorAll('span[dir="auto"], p, h1, h2, a, div[dir="auto"]');
            for(let el of els) {
                let txt = el.innerText;
                if(!txt) continue;
                txt = txt.trim();

                if(txt.startsWith("🔴") || txt.startsWith("🟠")) {
                    return txt;
                }
            }
            return "";
            """
            
            raw_title = driver.execute_script(script)
            
            if raw_title:
                clean_title = raw_title.split('\n')[0].strip()
                return clean_title
                
        except Exception:
            pass
            
        return "ไม่ทราบชื่อคลิป"

    def get_viewer_count(self, driver):
        view_val = 0
        
        try:
            viewer_elements = driver.find_elements(By.XPATH, "//span[i]/following-sibling::span")
            for el in viewer_elements:
                t = el.get_attribute("textContent")
                if t:
                    t = t.strip()
                    v = clean_and_parse_count(t)
                    if v > 0:
                        view_val = v
                        break
        except Exception:
            pass

        if view_val == 0:
            try:
                # ลองดึงจาก JS โดยตรง เผื่อว่า Selenium XPath ดึงออกมาไม่ได้
                script = """
                let els = document.querySelectorAll('span > i');
                for(let i of els) {
                    let parentSpan = i.parentElement;
                    let siblingSpan = parentSpan.nextElementSibling;
                    if(siblingSpan && siblingSpan.tagName.toLowerCase() === 'span') {
                        let txt = siblingSpan.textContent.trim();
                        if(/[0-9]+/.test(txt)) {
                            return txt;
                        }
                    }
                }
                return "";
                """
                val = driver.execute_script(script)
                if val:
                    v = clean_and_parse_count(val)
                    if v > 0:
                        view_val = v
            except:
                pass

        # Fallback to body text match
        if view_val == 0:
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                match = re.search(r'(?:LIVE|สด)\s*([\d.,KkMmพันล้าน]+)', body_text)
                if match:
                    v = clean_and_parse_count(match.group(1))
                    if v > 0:
                        view_val = v
            except:
                pass
                
        return view_val

    def scrape_facebook_comments_live(self, driver):
        """Parses live comments from Facebook using dir='auto' and lang attributes."""
        comments = []

        try:            
            # --- CHANGE COMMENT FILTER TO ALL COMMENTS ---
            try:
                script_filter = """
                let selectors = ['span[dir="auto"]', 'span', 'div'];
                for(let sel of selectors) {
                    let els = document.querySelectorAll(sel);
                    for(let el of els) {
                        let txt = (el.textContent || el.innerText || "").toLowerCase().trim();
                        if(txt.startsWith("เกี่ยวข้องมากที่สุด") || txt.startsWith("most relevant")) {
                            el.click();
                            return true;
                        }
                    }
                }
                return false;
                """
                if driver.execute_script(script_filter):
                    print("  [DEBUG] Clicked 'Most relevant' filter")
                    time.sleep(1)
                    
                    script_all_comments = """
                    let selectors = ['span[dir="auto"]', 'span', 'div'];
                    for(let sel of selectors) {
                        let els = document.querySelectorAll(sel);
                        for(let el of els) {
                            let txt = (el.textContent || el.innerText || "").toLowerCase().trim();
                            if(txt === "ความคิดเห็นทั้งหมด" || txt === "all comments" || txt.startsWith("ความคิดเห็นทั้งหมด") || txt.startsWith("all comments")) {
                                el.click();
                                return true;
                            }
                        }
                    }
                    return false;
                    """
                    if driver.execute_script(script_all_comments):
                        print("  [DEBUG] Selected 'All comments'")
                        time.sleep(1)
            except Exception as e:
                print(f"  [DEBUG] Error changing comment filter: {e}")

            # ---------------------------------------------
            # --- EXPAND COMMENTS ---
            try:
                script_view_more = """
                let selectors = ['span[dir="auto"]', 'span', 'div'];
                for(let sel of selectors) {
                    let els = document.querySelectorAll(sel);
                    for(let el of els) {
                        let txt = (el.textContent || el.innerText || "").toLowerCase().trim();
                        if(txt === "view more comments" || txt === "ดูความคิดเห็นเพิ่มเติม" || txt.includes("view more comments") || txt.includes("ดูความคิดเห็นเพิ่มเติม")) {
                            el.click();
                            return true;
                        }
                    }
                }
                return false;
                """
                click_count = 0
                max_clicks = 20
                while click_count < max_clicks:
                    if driver.execute_script(script_view_more):
                        click_count += 1
                        print(f"  [DEBUG] Clicked 'View more comments' (Click {click_count}/{max_clicks})")
                        time.sleep(1.5)
                    else:
                        break
                print(f"  [DEBUG] Finished expanding comments. Total clicks: {click_count}")
            except Exception as e:
                print(f"  [DEBUG] Error expanding comments: {e}")
                
            # -----------------------
            script = """
            let extracted_comments = [];
            let anchors = document.querySelectorAll('*[dir="auto"][lang]');
            for (let anchor of anchors) {
                let container = anchor.parentElement;
                let maxDepth = 10;
                while(container && container.querySelectorAll('*[dir="auto"]').length < 3 && maxDepth > 0) {
                    container = container.parentElement;
                    maxDepth--;
                }
                
                if (container) {
                    let dirAutos = Array.from(container.querySelectorAll('*[dir="auto"]'));
                    let anchorIndex = dirAutos.indexOf(anchor);
                    
                    if (anchorIndex > 0 && anchorIndex < dirAutos.length - 1) {
                        let senderEl = dirAutos[anchorIndex - 1];
                        let messageEl = dirAutos[anchorIndex + 1];
                        
                        function extractText(el) {
                            let text = "";
                            for (let node of el.childNodes) {
                                if (node.nodeType === 3) {
                                    text += node.textContent;
                                } else if (node.nodeType === 1) {
                                    if (node.tagName.toLowerCase() === 'img' && node.hasAttribute('alt')) {
                                        text += node.getAttribute('alt');
                                    } else {
                                        text += extractText(node);
                                    }
                                }
                            }
                            return text;
                        }
                        
                        let sender = extractText(senderEl).trim();
                        let message = extractText(messageEl).trim();
                        
                        if (sender && message) {
                            extracted_comments.push({author: sender, message: message});
                        }
                    }
                }
            }
            return JSON.stringify(extracted_comments);
            """

            # --- ScreenShot
            # try:
            #     driver.save_screenshot("debug_facebook.png")
            #     with open("debug_facebook.html", "w", encoding="utf-8") as f:
            #         f.write(driver.page_source)
            #     print("  [DEBUG] Saved debug_facebook.png and debug_facebook.html")
            # except Exception as e:
            #     print(f"  [DEBUG] Failed to save debug files: {e}")
            # -------------------
            
            import json
            comments_json_str = driver.execute_script(script)
            extracted_comments = json.loads(comments_json_str) if comments_json_str else []
            print(f"  [Comment Scraper] JS Found {len(extracted_comments)} message elements")
            
            for item in extracted_comments:
                try:
                    author = item.get("author", "ไม่ทราบชื่อ")
                    message = item.get("message", "").strip()
                    if not message:
                        continue
                        
                    t_lower = message.lower()
                    
                    ui_words = {
                        "log in", "forgotten account?", "video", "home", "reels", "explore", 
                        "comment", "comments", "see more", "most relevant", "view more comments", 
                        "related reels", "related videos", "pages", "media", "videos", 
                        "view transcript", "create new account", "follow", "share", "like", 
                        "reply", "top fan", "ผู้เขียน", "สด", "live", "ตอบกลับ", "แชร์", "ถูกใจ",
                        "hide", "ซ่อน", "report", "รายงาน", "about", "about this video", "ไทยพีบีเอส"
                    }

                    if t_lower in ui_words:
                        continue
                    if re.match(r'^\d+\s*[mhdwys]$', t_lower) or re.match(r'^\d+\s*(นาที|ชม|ชั่วโมง|วัน|สัปดาห์|ปี)(ที่แล้ว)?$', t_lower):
                        continue
                    if re.search(r'^\d+[mhdwys]\s*\n\s*·', t_lower): 
                        continue
                    if re.match(r'^[\d\.,]+[kmb]?$', t_lower) or re.match(r'^[\d\.,]+[kmb]?\s*(views|comments|shares|plays|views|ความคิดเห็น|แชร์)$', t_lower):
                        continue
                    if re.match(r'^\d+:\d+(:\d+)?$', t_lower):
                        continue
                    if "privacy" in t_lower and "terms" in t_lower:
                        continue
                    if ("views\n" in t_lower and "·" in t_lower) or "\n was live." in t_lower:
                        continue
                    if t_lower.startswith("🔴") or t_lower.startswith("🟠"):
                        continue
                    if "live" in t_lower or "thaipbs" in t_lower or "thai pbs" in t_lower:
                        continue
                        
                    comments.append({"sender": author, "message": message})
                except:
                    pass
                    
        except Exception as e:
            print(f"  [Comment Scraper] Facebook parse error: {e}")

        unique_comments = []
        seen = set()
        for comment in comments:
            identifier = (comment["sender"], comment["message"])
            if identifier not in seen:
                seen.add(identifier)
                comment["id"] = len(unique_comments) + 1
                unique_comments.append(comment)

        return unique_comments

    def fetch_live_data(self, url: str) -> dict:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=self.options)
        
        result = {
            "status": "success",
            "url": url,
            "embed_url": url,
            "title": "",
            "is_live": False,
            "viewers": 0,
            "chat_messages": [],
            "error_message": None
        }

        try:
            driver.get(url)
            try:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                
                # ตรวจสอบ text ตามที่กำหนดด้วย custom wait
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script("""
                        let els = document.querySelectorAll('span[dir="auto"], span, div');
                        for(let el of els) {
                            let txt = (el.textContent || el.innerText || "").toLowerCase().trim();
                            if(txt.startsWith("เกี่ยวข้องมากที่สุด") || txt.startsWith("most relevant") || txt.startsWith("ความคิดเห็นทั้งหมด") || txt.startsWith("all comments")) {
                                return true;
                            }
                        }
                        return false;
                    """)
                )
            except Exception as e:
                print(f"  [DEBUG] Wait condition timeout: {e}")

            self._close_dialogs(driver)
            
            is_live_video = False
            try:
                is_live_video = driver.execute_script("""
                    let els = document.querySelectorAll('span');
                    for(let el of els) {
                        let txt = (el.textContent || el.innerText || "").toLowerCase();
                        if(txt.includes("กำลังถ่ายทอดสด") || txt.includes("is live")) {
                            return true;
                        }
                    }
                    return false;
                """)
            except:
                pass

            if not is_live_video:
                live_indicators = driver.find_elements(By.CSS_SELECTOR, "._u_g, ._u_h")
                for el in live_indicators:
                    if el.is_displayed():
                        is_live_video = True
                        break
            
            result["is_live"] = is_live_video
            result["title"] = self.get_video_title(driver)

            if is_live_video:
                result["viewers"] = self.get_viewer_count(driver)
            else:
                result["viewers"] = 0
                
            result["chat_messages"] = self.scrape_facebook_comments_live(driver)

        except Exception as e:
            result["status"] = "error"
            result["error_message"] = str(e)
        
        finally:
            driver.quit()
            
        return result