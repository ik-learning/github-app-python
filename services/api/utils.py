# -*- coding: utf-8 -*-

import json
import logging
import base64
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_datetime(dt_value):
    """
    Parse datetime value to datetime object.

    Args:
        dt_value: datetime object or ISO format string

    Returns:
        datetime: Parsed datetime object
    """
    if isinstance(dt_value, datetime):
        return dt_value
    if isinstance(dt_value, str):
        # Try ISO format first (most common)
        try:
            return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            # Fallback to common formats
            for fmt in ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%fZ']:
                try:
                    return datetime.strptime(dt_value, fmt)
                except ValueError:
                    continue
    return dt_value

def decode_base64_key(encoded_key):
    """
    Decode a base64-encoded key.

    Args:
        encoded_key: Base64-encoded string

    Returns:
        str: Decoded UTF-8 string

    Raises:
        ValueError: If the key cannot be decoded
    """
    if not encoded_key:
        raise ValueError("Encoded key cannot be empty")

    try:
        decoded_bytes = base64.b64decode(encoded_key)
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Failed to decode base64 key: {str(e)}")


def json_prettify(data):
    return json.dumps(data, indent=4, default=str)

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def write_file(file_path, content):
    with open(file_path, "w") as f:
        f.write(content)
