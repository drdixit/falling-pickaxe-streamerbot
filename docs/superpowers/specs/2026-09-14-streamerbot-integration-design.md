# Streamer.bot Integration Design Spec

## 1. Overview
The goal of this project is to replace the existing Google/YouTube API polling mechanism with a local WebSocket connection to Streamer.bot. This removes the need for Google API keys, reduces latency, and allows the game to easily support Twitch and YouTube simultaneously.

## 2. Architecture & Approach
We will use the **"Drop-In Replacement"** approach to minimize risk and avoid breaking the existing game logic.

Instead of `main.py` calling the YouTube API, it will poll an in-memory queue populated by a background thread running a WebSocket client.

### 2.1 Components
* **`streamerbot.py` (New):**
  * Uses the `websocket-client` library.
  * Connects to `ws://127.0.0.1:8080/`.
  * Subscribes to `Twitch.ChatMessage` and `YouTube.Message` events upon connection.
  * Parses incoming JSON and appends normalized messages to a thread-safe list.
* **`main.py` (Modified):**
  * Removes `google-api-python-client` imports.
  * Removes `live_chat_id` and YouTube setup logic.
  * Replaces `get_new_live_chat_messages(live_chat_id)` with `streamerbot.get_new_messages()`.

### 2.2 Data Flow
1. Viewer types a message in Twitch/YouTube.
2. Streamer.bot receives it and emits a WebSocket event.
3. `streamerbot.py` receives the JSON event.
4. `streamerbot.py` extracts the `username` and `message` (and superchat details if available).
5. It formats a dictionary: `{"author": "username", "message": "text", "sc_details": None, "ss_details": None}` and appends it to an internal list.
6. The `main.py` game loop calls `get_new_messages()`, retrieving and clearing the list.
7. `main.py` parses the messages for commands (`tnt`, `wood`, `big`, etc.) exactly as it did before.

## 3. Dependencies
* **Add:** `websocket-client` to `requirements.txt`
* **Remove:** `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2` from `requirements.txt` (and the `youtube.py` file can be safely deleted or ignored).

## 4. Error Handling
* If the WebSocket disconnects, `streamerbot.py` should attempt to quietly reconnect in the background without crashing the game.
* If Streamer.bot is not running, the game will still start, but `streamerbot.py` will print a warning and retry connecting periodically.
