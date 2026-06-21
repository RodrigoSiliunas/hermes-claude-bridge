"""Tool handlers for the Hermes plugin."""

from __future__ import annotations

import json
import os
from typing import Any

from hermes_claude_bridge.bridge import HermesClaudeBridge
from hermes_claude_bridge.client import BridgeClient
from hermes_claude_bridge.schemas import ClaudeTask


async def handle_delegate(args: dict[str, Any], **kwargs: Any) -> str:
    """Handle claude_code_delegate tool calls from Hermes."""
    prompt = args["prompt"]
    context_files = args.get("context_files") or []
    working_dir = args.get("working_dir", ".")
    model = args.get("model")
    permission_mode = args.get("permission_mode", "acceptEdits")
    timeout = args.get("timeout", 300)
    bridge_url = args.get("bridge_url") or os.environ.get("HERMES_CLAUDE_BRIDGE_URL")
    mode = args.get("mode", "headless")
    max_history_events = args.get("max_history_events", 10)

    if bridge_url:
        client = BridgeClient(bridge_url)
        session = await client.create_session(
            working_dir=working_dir,
            model=model,
            mode=mode,
            max_history_events=max_history_events,
        )
        result = await client.send_prompt(
            session["session_id"],
            prompt,
            context_files=context_files,
            timeout=timeout,
        )
        await client.close()
        return json.dumps(result)

    bridge = HermesClaudeBridge()
    result = await bridge.run_task(
        ClaudeTask(
            prompt=prompt,
            context_files=context_files,
            working_dir=working_dir,
            model=model,
            permissions_mode=permission_mode,  # type: ignore[arg-type]
            timeout_seconds=timeout,
        )
    )
    return json.dumps(result.model_dump())
