# src/streamerbot.py
import websocket
import json
import threading
import time

_message_queue = []
_lock = threading.Lock()

def _on_message(ws, message):
    try:
        data = json.loads(message)
        event = data.get("event", {})
        
        # Streamer.bot YouTube Message and Subscriber events
        if event.get("type") in ["Message", "Subscriber"]:
            payload_data = data.get("data", {})
            
            # Message event
            if event.get("type") == "Message":
                author = payload_data.get("user", {}).get("name") or "Unknown"
                text = payload_data.get("message") or ""
                with _lock:
                    _message_queue.append({
                        "author": author,
                        "message": text,
                        "sc_details": None,
                        "ss_details": None,
                        "is_subscriber": False
                    })
            
            # Subscriber event
            elif event.get("type") == "Subscriber":
                user_data = payload_data.get("user", {})
                author = user_data.get("name") or user_data.get("displayName") or "Someone"
                with _lock:
                    _message_queue.append({
                        "author": author,
                        "message": "",
                        "sc_details": None,
                        "ss_details": None,
                        "is_subscriber": True
                    })
    except Exception as e:
        print(f"Error parsing Streamer.bot message: {e}")

def _on_error(ws, error):
    print(f"Streamer.bot WS Error: {error}")

def _on_close(ws, close_status_code, close_msg):
    print("Streamer.bot WS Closed")

def _on_open(ws):
    print("Connected to Streamer.bot WS")
    # Subscribe to chat messages and subscribers
    sub_msg = {
        "request": "Subscribe",
        "events": {
            "YouTube": ["Message", "Subscriber"]
        },
        "id": "falling-pickaxe"
    }
    ws.send(json.dumps(sub_msg))

def _run_with_reconnect(retry_interval=5, max_retries=None):
    retries = 0
    while True:
        try:
            ws = websocket.WebSocketApp("ws://127.0.0.1:8080/",
                                      on_open=_on_open,
                                      on_message=_on_message,
                                      on_error=_on_error,
                                      on_close=_on_close)
            ws.run_forever()
        except Exception as e:
            print(f"Streamer.bot connection exception: {e}")
        print(f"Warning: Streamer.bot disconnected. Retrying in {retry_interval} seconds...")
        retries += 1
        if max_retries is not None and retries >= max_retries:
            break
        time.sleep(retry_interval)

def start_client():
    websocket.enableTrace(False)
    # Run in background with reconnection loop
    wst = threading.Thread(target=_run_with_reconnect, daemon=True)
    wst.start()

def get_new_messages():
    with _lock:
        msgs = list(_message_queue)
        _message_queue.clear()
        return msgs
