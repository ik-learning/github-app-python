import json
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class MessagePayload:
    """Parse worker message from stream."""
    id: str
    callback_url: str

    @classmethod
    def message(cls, payload: Dict[str, Any]) -> 'MessagePayload':
        """Create MessagePayload from Redis stream message."""
        data = payload.get('data', '{}')
        if isinstance(data, str):
            data = json.loads(data)
        return cls(
            id=data.get('id', ''),
            callback_url=data.get('callback_url', '')
        )


@dataclass
class StoragePayload:
    """Parse storage data from Redis."""
    id: str
    name: str
    owner: str
    branch: str
    prId: int

    @classmethod
    def from_json(cls, data: str) -> 'StoragePayload':
        """Create StoragePayload from JSON string."""
        parsed = json.loads(data)
        return cls(
            id=parsed.get('id', ''),
            name=parsed.get('name', ''),
            owner=parsed.get('owner', ''),
            branch=parsed.get('branch', ''),
            prId=parsed.get('prId', 0)
        )
