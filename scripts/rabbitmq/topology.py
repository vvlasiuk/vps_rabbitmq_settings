from __future__ import annotations

import re
from typing import Any, Dict, List

DEFAULT_TAGS = ""


def build_topology(vhost: str, channels: List[str] | None = None) -> Dict[str, Any]:
    """
    Build RabbitMQ topology for a vhost with multiple channels.
    
    If channels is provided and non-empty, creates:
    - One exchange and queue per channel: {channel}.events, {channel}.queue
    - Bindings with routing key equal to exchange name: {channel}.events
    - One user with permissions for all channels
    
    If channels is empty/None, falls back to legacy single-exchange mode:
    - Exchange: {vhost}.events
    - Queue: {vhost}.queue
    - Routing key equal to exchange name: {vhost}.events
    
    Args:
        vhost: The vhost name (e.g., "vps_messages")
        channels: List of channel names (e.g., ["input", "output"]). If None or empty, uses legacy mode.
    
    Returns:
        Dictionary with keys: users, permissions, exchanges, queues, bindings
    """
    if channels is None:
        channels = []
    
    channels = [ch.strip() for ch in channels if isinstance(ch, str) and ch.strip()]
    
    user_name = f"user_{vhost}"
    
    if not channels:
        # Legacy mode: single exchange and queue per vhost
        exchange_name = f"{vhost}.events"
        queue_name = f"{vhost}.queue"
        
        return {
            "users": [
                {"name": user_name, "tags": DEFAULT_TAGS},
            ],
            "permissions": [
                {
                    "user": user_name,
                    "configure": "^$",
                    "write": f"^{re.escape(exchange_name)}$",
                    "read": f"^{re.escape(queue_name)}$",
                },
            ],
            "exchanges": [
                {
                    "name": exchange_name,
                    "type": "direct",
                    "durable": True,
                    "auto_delete": False,
                    "internal": False,
                    "arguments": {},
                }
            ],
            "queues": [
                {
                    "name": queue_name,
                    "durable": True,
                    "auto_delete": False,
                    "arguments": {},
                }
            ],
            "bindings": [
                {
                    "source": exchange_name,
                    "destination": queue_name,
                    "routing_key": exchange_name,
                    "arguments": {},
                }
            ],
        }
    
    # Multi-channel mode: one exchange and queue per channel
    exchanges = []
    queues = []
    bindings = []
    
    for channel in channels:
        exchange_name = f"{channel}.events"
        queue_name = f"{channel}.queue"
        
        exchanges.append({
            "name": exchange_name,
            "type": "direct",
            "durable": True,
            "auto_delete": False,
            "internal": False,
            "arguments": {},
        })
        
        queues.append({
            "name": queue_name,
            "durable": True,
            "auto_delete": False,
            "arguments": {},
        })
        
        bindings.append({
            "source": exchange_name,
            "destination": queue_name,
            "routing_key": exchange_name,
            "arguments": {},
        })
    
    # Build regex patterns for permissions allowing all channels
    # For write: allow all channel exchanges (input.events, output.events, etc.)
    # For read: allow all channel queues (input.queue, output.queue, etc.)
    exchange_pattern = "^(" + "|".join(re.escape(ch) for ch in channels) + r")\.events$"
    queue_pattern = "^(" + "|".join(re.escape(ch) for ch in channels) + r")\.queue$"
    
    return {
        "users": [
            {"name": user_name, "tags": DEFAULT_TAGS},
        ],
        "permissions": [
            {
                "user": user_name,
                "configure": "^$",
                "write": exchange_pattern,
                "read": queue_pattern,
            },
        ],
        "exchanges": exchanges,
        "queues": queues,
        "bindings": bindings,
    }
