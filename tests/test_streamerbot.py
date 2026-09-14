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
