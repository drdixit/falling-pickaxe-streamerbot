# tests/test_streamerbot.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from unittest.mock import patch, MagicMock
import json
from streamerbot import get_new_messages, _on_message, _on_open, _run_with_reconnect, start_client

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

def test_on_open_subscription():
    mock_ws = MagicMock()
    _on_open(mock_ws)
    mock_ws.send.assert_called_once()
    sent_data = json.loads(mock_ws.send.call_args[0][0])
    assert sent_data["request"] == "Subscribe"
    assert "ChatMessage" in sent_data["events"]["Twitch"]
    assert "Message" in sent_data["events"]["YouTube"]

@patch("streamerbot.websocket.WebSocketApp")
@patch("streamerbot.time.sleep")
def test_reconnect_loop(mock_sleep, mock_ws_app):
    mock_ws = MagicMock()
    mock_ws_app.return_value = mock_ws
    
    _run_with_reconnect(retry_interval=1, max_retries=2)
    
    assert mock_ws.run_forever.call_count == 2
    mock_sleep.assert_called_once_with(1)

@patch("streamerbot.threading.Thread")
def test_start_client(mock_thread):
    start_client()
    mock_thread.assert_called_once_with(target=_run_with_reconnect, daemon=True)
    mock_thread.return_value.start.assert_called_once()
