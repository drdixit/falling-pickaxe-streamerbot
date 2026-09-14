# src/streamerbot.py
import websocket
import json
import threading

_message_queue = []
_lock = threading.Lock()

def _on_message(ws, message):
    try:
        data = json.loads(message)
        event = data.get("event", {})
        
        # Streamer.bot Twitch/YouTube ChatMessage event structure
        if event.get("type") in ["ChatMessage", "Message"]:
            msg_data = data.get("data", {}).get("message", {})
            # Twitch uses "username", YouTube might use "displayName" or similar, fallback to "author"
            author = msg_data.get("username") or msg_data.get("displayName") or "Unknown"
            text = msg_data.get("message", "")
            
            with _lock:
                _message_queue.append({
                    "author": author,
                    "message": text,
                    "sc_details": None, # Ignore superchats for now or map if data is available
                    "ss_details": None
                })
    except Exception as e:
        print(f"Error parsing Streamer.bot message: {e}")

def _on_error(ws, error):
    print(f"Streamer.bot WS Error: {error}")

def _on_close(ws, close_status_code, close_msg):
    print("Streamer.bot WS Closed")

def _on_open(ws):
    print("Connected to Streamer.bot WS")
    # Subscribe to chat messages
    sub_msg = {
        "request": "Subscribe",
        "events": {
            "Twitch": ["ChatMessage"],
            "YouTube": ["Message"]
        },
        "id": "falling-pickaxe"
    }
    ws.send(json.dumps(sub_msg))

def start_client():
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp("ws://127.0.0.1:8080/",
                              on_open=_on_open,
                              on_message=_on_message,
                              on_error=_on_error,
                              on_close=_on_close)
    
    # Run in background
    wst = threading.Thread(target=ws.run_forever, daemon=True)
    wst.start()

def get_new_messages():
    with _lock:
        msgs = list(_message_queue)
        _message_queue.clear()
        return msgs
