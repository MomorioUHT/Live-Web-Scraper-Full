import re

def clean_and_parse_count(text: str) -> int:
    """
    Convert a viewer/like count string to an integer.

    Handles suffixes in both English and Thai:
      - 'K' or 'พัน'  -> x 1,000
      - 'M' or 'ล้าน' -> x 1,000,000
      - 'หมื่น'        -> x 10,000

    Examples:
        '1.2K'  -> 1200
        '3พัน'  -> 3000
        '2.5M'  -> 2500000
        '500'   -> 500
    """
    text = str(text).strip()
    if not text:
        return 0

    multiplier = 1
    text_upper = text.upper()
    if 'K' in text_upper or 'พัน' in text:
        multiplier = 1_000
    elif 'M' in text_upper or 'ล้าน' in text:
        multiplier = 1_000_000
    elif 'หมื่น' in text:
        multiplier = 10_000

    number_str = re.sub(r'[^\d\.]', '', text)
    if number_str:
        return int(float(number_str) * multiplier)
    return 0


def get_element_text_with_emojis(driver, element) -> str:
    """
    Extract visible text from a Selenium WebElement, including emoji characters
    that are rendered as <img> tags with an 'alt' attribute.

    Falls back to element.text if the JS execution fails.
    """
    try:
        script = """
        var el = arguments[0];
        var text = '';
        el.childNodes.forEach(function(node) {
            if (node.nodeType === Node.TEXT_NODE) {
                text += node.textContent;
            } else if (node.nodeType === Node.ELEMENT_NODE) {
                if (node.tagName && node.tagName.toLowerCase() === 'img') {
                    var alt = node.getAttribute('alt');
                    var src = node.getAttribute('src');
                    if (alt === '🫢' || (src && src.indexOf('yt3.ggpht.com') !== -1)) {
                        return; // Skip YouTube custom pictures and specific broken emojis
                    }
                    if (alt) { text += alt; }
                } else {
                    text += node.innerText || node.textContent || '';
                }
            }
        });
        return text.trim();
        """
        return driver.execute_script(script, element) or ""
    except Exception:
        try:
            return element.text.strip()
        except Exception:
            return ""
