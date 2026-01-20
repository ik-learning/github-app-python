import json
from dataclasses import dataclass


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
