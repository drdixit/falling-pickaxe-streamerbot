# Streamer.bot Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace YouTube API polling with a local Streamer.bot WebSocket client to capture chat messages seamlessly.

**Architecture:** Create a drop-in replacement module `streamerbot.py` that listens to `ws://127.0.0.1:8080/`, parses messages, and exposes a `get_new_messages()` function to `main.py`.

**Tech Stack:** Python 3.11, `websocket-client`

**Spec:** `docs/superpowers/specs/2026-09-14-streamerbot-integration-design.md`

## Global Constraints

- Do not break the existing game loop in `main.py`.
- Ensure parsed messages exactly match the old format: `{"author": ..., "message": ..., "sc_details": ..., "ss_details": ...}`
- Keep all new code in Python.

---

### Task 1: Update Dependencies

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Produces: Updated environment with `websocket-client`

- [ ] **Step 1: Write the failing test**
No test needed for requirements update.

- [ ] **Step 2: Write minimal implementation**
Remove google dependencies and add `websocket-client`.

```text
pygame==2.6.1
pymunk==7.3.0
websocket-client==1.8.0
```
(Overwrite `requirements.txt` with just these three, removing `google-*` and `python-dateutil` unless otherwise needed, but to be safe we can just remove `google-*`). Let's assume we remove `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`.

- [ ] **Step 3: Commit**
```bash
git add requirements.txt
git commit -m "chore: update dependencies for streamerbot"
```

---

### Task 2: Create Streamer.bot Client (`streamerbot.py`)

**Files:**
- Create: `src/streamerbot.py`
- Test: `tests/test_streamerbot.py`

**Interfaces:**
- Produces: `def get_new_messages() -> list`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_streamerbot.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from streamerbot import get_new_messages, _on_message

def test_on_message_parsing():
    # Simulate a Twitch ChatMessage event from Streamer.bot
    payload = '{"event": {"source": "Twitch", "type": "ChatMessage"}, "data": {"message": {"username": "testuser", "message": "!wood"}}}'
    _on_message(None, payload)
    
    msgs = get_new_messages()
    assert len(msgs) == 1
    assert msgs[0]["author"] == "testuser"
    assert msgs[0]["message"] == "!wood"
    assert msgs[0]["sc_details"] is None
    assert msgs[0]["ss_details"] is None
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_streamerbot.py -v`
Expected: FAIL (file not found or import error)

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_streamerbot.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/streamerbot.py tests/test_streamerbot.py
git commit -m "feat: add streamerbot websocket client"
```

---

### Task 3: Integrate Streamer.bot into Game Loop

**Files:**
- Modify: `src/main.py`

**Interfaces:**
- Consumes: `streamerbot.get_new_messages()`
- Consumes: `streamerbot.start_client()`

- [ ] **Step 1: Write the failing test**
Since `main.py` is a visual pygame app, a unit test for the main loop import is complex. We will rely on manual visual testing or standard python syntax checks for this refactor.

- [ ] **Step 2: Write minimal implementation**
Modify `src/main.py`:
1. Remove `from youtube import ...`
2. Add `from streamerbot import start_client, get_new_messages`
3. Remove the entire `if config["CHAT_CONTROL"] == True:` block dealing with YouTube `live_stream` and `live_chat_id` (Lines 23-45 approx).
4. Add `start_client()` before the `game()` function starts, or right at the beginning of the `game()` function.
5. In the game loop, replace:
   `new_messages = get_new_live_chat_messages(live_chat_id)`
   with
   `new_messages = get_new_messages()`
6. Remove any superchat/subscriber API fetching logic that relies on `google-api-python-client` (e.g., `get_subscriber_count()`), or mock it out.

- [ ] **Step 3: Run test to verify it passes**
Run `python src/main.py` to ensure it launches successfully without Google API crashes and connects to the websocket.

- [ ] **Step 4: Commit**
```bash
git add src/main.py
git commit -m "refactor: swap youtube api for streamerbot websocket"
```
