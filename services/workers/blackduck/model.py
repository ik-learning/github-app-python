import json
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class MessagePayload:
    """Parse and store relevant fields from a payload."""
    trace_id: str
    name: str
    owner: str
    branch: str
    prId: int
    callbackUrl: str

    @classmethod
    def message(cls, payload: Dict[str, Any]) -> 'MessagePayload':
        """Create MessagePayload from Redis stream message."""
        data = payload.get('data', '{}')
        if isinstance(data, str):
            data = json.loads(data)
        return cls(
            trace_id=data.get('trace_id', ''),
            name=data.get('name', ''),
            owner=data.get('owner', ''),
            branch=data.get('branch', ''),
            prId=data.get('prId', 0),
            callbackUrl=data.get('callbackUrl', '')
        )
