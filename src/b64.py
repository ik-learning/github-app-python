import os
import base64

# python src/b64.py

def decode_env_variable(env_var_name: str) -> str:
    """
    Read a base64-encoded environment variable and decode it to a string.

    Args:
        env_var_name: The name of the environment variable to read

    Returns:
        The decoded string value

    Raises:
        ValueError: If the environment variable is not set or cannot be decoded
    """
    # Get the environment variable
    encoded_value = os.getenv(env_var_name)

    if encoded_value is None:
        raise ValueError(f"Environment variable '{env_var_name}' is not set")

    try:
        # Decode from base64
        decoded_bytes = base64.b64decode(encoded_value)
        # Convert bytes to string
        decoded_string = decoded_bytes.decode('utf-8')
        return decoded_string
    except Exception as e:
        raise ValueError(f"Failed to decode environment variable '{env_var_name}': {str(e)}")


# Example usage
if __name__ == "__main__":
    try:
        # Replace 'MY_BASE64_VAR' with your actual environment variable name
        result = decode_env_variable('MY_BASE64')
        print(f"Decoded value: {result}")
    except ValueError as e:
        print(f"Error: {e}")
