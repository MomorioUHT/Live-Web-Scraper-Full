import asyncio
import websockets
import json

class TikTokLiveScraper:
    _is_ws_active = False

    def __init__(self):
        pass

    def fetch_live_data(self, url: str, api_key: str = None, limit: int = 50) -> dict:
        """
        Scrape TikTok live chat using Tik Tools websocket API.
        
        Args:
            url (str): Creator name (e.g., "@streamer_name")
            api_key (str): Tik Tools API Key
            limit (int): Number of comments to wait for
        """
        if TikTokLiveScraper._is_ws_active:
            return {
                "status": "error",
                "error_message": "WebSocket is still in use. Please wait until the current session finishes.",
                "chat_messages": []
            }
            
        TikTokLiveScraper._is_ws_active = True
        
        if not api_key:
            TikTokLiveScraper._is_ws_active = False
            return {
                "status": "error",
                "error_message": "Missing API Key for Tik Tools",
                "chat_messages": []
            }
            
        # Clean unique_id from url
        unique_id = url.split('/')[-1] if '/' in url else url
        unique_id = unique_id.replace('@', '').strip()
        
        ws_url = f"wss://api.tik.tools?uniqueId={unique_id}&apiKey={api_key}"
        
        chat_messages = []
        viewers_count = 0
        
        async def listen():
            nonlocal viewers_count
            try:
                async with websockets.connect(ws_url, close_timeout=2) as ws:
                    print(f"[TikTok] Connected to Tik Tools for @{unique_id}. Waiting for {limit} comments...")
                    
                    while len(chat_messages) < limit:
                        try:
                            # Wait up to 30 seconds for a new message
                            message = await asyncio.wait_for(ws.recv(), timeout=30.0)
                        except asyncio.TimeoutError:
                            print(f"[TikTok] Timeout waiting for messages. Returning {len(chat_messages)} messages.")
                            break
                            
                        event = json.loads(message)
                        data = event.get("data", {})
                        
                        if isinstance(data, dict) and "viewerCount" in data:
                            try:
                                viewers_count = int(data.get("viewerCount"))
                            except (ValueError, TypeError):
                                pass

                        if event.get("event") == "chat":
                            user = data.get("user", {})
                            comment = data.get("comment", "")
                            sender = user.get("uniqueId", "Unknown")
                            
                            if comment and sender:
                                chat_messages.append({
                                    "id": len(chat_messages) + 1,
                                    "sender": sender,
                                    "message": comment
                                })
                                print(f"[TikTok] Collected {len(chat_messages)}/{limit}")
                    
                    print("[TikTok] Closing websocket connection before returning result...")
                    await ws.close()
                                
            except Exception as e:
                return str(e)
            return None

        # Run the async loop
        error_msg = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            error_msg = loop.run_until_complete(listen())
            loop.close()
        except Exception as e:
            error_msg = str(e)
            
        TikTokLiveScraper._is_ws_active = False

        return {
            "status": "success" if not error_msg else "error",
            "url": f"https://www.tiktok.com/@{unique_id}/live",
            "title": f"Live Chat - @{unique_id}",
            "is_live": True if not error_msg else False,
            "viewers": viewers_count,
            "chat_messages": chat_messages,
            "error_message": error_msg
        }
