from flask import Flask, request, jsonify
from flask_cors import CORS
import queue
import threading

from API.Facebook import FacebookLiveScraper
from API.Youtube import YouTubeLiveScraper
from API.X import XLiveScraper
from API.TikTok import TikTokLiveScraper

app = Flask(__name__)
CORS(app)

yt_scraper = YouTubeLiveScraper()
fb_scraper = FacebookLiveScraper()
x_scraper = XLiveScraper()
tiktok_scraper = TikTokLiveScraper()

# --- Queue System ---
# Max concurrent scrapes (can be increased if server has enough RAM)
MAX_CONCURRENT_SCRAPES = 1 
request_queue = queue.Queue()

def scraper_worker():
    while True:
        task = request_queue.get()
        if task is None:
            break
            
        platform_lower, target_url, extra_args, result_container, event = task
        
        try:
            if platform_lower == 'youtube':
                print(f"[System] - [Youtube] fetching data from: {target_url}")
                result_container['data'] = yt_scraper.fetch_live_data(target_url)
            elif platform_lower == 'facebook':
                print(f"[System] - [Facebook] fetching data from: {target_url}")
                result_container['data'] = fb_scraper.fetch_live_data(target_url)
            elif platform_lower == 'x':
                print(f"[System] - [X] fetching data from: {target_url}")
                result_container['data'] = x_scraper.fetch_live_data(target_url)
            elif platform_lower == 'tiktok':
                print(f"[System] - [TikTok] fetching data from: {target_url}")
                result_container['data'] = tiktok_scraper.fetch_live_data(
                    target_url, 
                    api_key=extra_args.get('api_key'), 
                    limit=extra_args.get('limit')
                )
        except Exception as e:
            result_container['error'] = str(e)
            print(f"[System] - Error fetching data: {e}")
        finally:
            event.set()
            request_queue.task_done()

for _ in range(MAX_CONCURRENT_SCRAPES):
    worker_thread = threading.Thread(target=scraper_worker, daemon=True)
    worker_thread.start()
# --------------------

@app.route('/api/v1/live', methods=['GET', 'POST'])
def get_live_data():
    platform = request.args.get('platform')
    url = request.args.get('url')
    api_key = request.args.get('api_key')
    limit = request.args.get('limit')
    
    if not platform or not url:
        return jsonify({"error": "Missing 'platform' or 'url' parameter"}), 400
        
    platform_lower = platform.lower()
    
    if platform_lower not in ['youtube', 'facebook', 'x', 'tiktok']:
        return jsonify({"error": f"Unsupported platform: {platform}"}), 400
        
    extra_args = {}
    if platform_lower == 'tiktok':
        if not api_key:
            return jsonify({"error": "Missing 'api_key' for TikTok"}), 400
        extra_args['api_key'] = api_key
        try:
            extra_args['limit'] = int(limit) if limit else 50
        except ValueError:
            return jsonify({"error": "Invalid 'limit' value"}), 400
        
    result_container = {}
    event = threading.Event()
    
    print(f"[System] Queueing request for {platform} - {url}")
    request_queue.put((platform_lower, url, extra_args, result_container, event))
    
    # Wait until the worker thread processes this request
    event.wait()
    
    if 'error' in result_container:
        return jsonify({
            "status": "error",
            "message": "An error occurred while fetching data.",
            "details": result_container['error']
        }), 500
        
    return jsonify(result_container['data'])

if __name__ == '__main__':
    import os
    port = int(os.environ.get('SERVER_PORT', 8000))
    print(f"[System] Starting Server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)