import hmac
import hashlib
import struct
import argparse
import os
import time
import binascii
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


def generate_encryption_key(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key


def store_key(hex_key):
    if len(hex_key) < 64:
        print("Error: Key must be at least 64 hexadecimal characters")
        return False
    
    try:
        binascii.unhexlify(hex_key)
    except:
        print("Error: Key must be in hexadecimal format")
        return False
    
    password = b"ft_otp_password"
    salt = os.urandom(16)
    
    encryption_key = generate_encryption_key(password, salt)
    cipher = Fernet(encryption_key)
    
    encrypted_key = cipher.encrypt(hex_key.encode())
    
    with open("ft_otp.key", "wb") as f:
        f.write(salt)
        f.write(encrypted_key)
    
    print("Key was successfully stored in ft_otp.key")
    return True


def get_stored_key():
    """Retrieve and decrypt the key from ft_otp.key."""
    try:
        with open("ft_otp.key", "rb") as f:
            salt = f.read(16)  
            encrypted_key = f.read()  
        
        password = b"ft_otp_password"
        encryption_key = generate_encryption_key(password, salt)
        cipher = Fernet(encryption_key)
        
        hex_key = cipher.decrypt(encrypted_key).decode()
        return hex_key
    
    except Exception as e:
        print(f"Error reading key: {str(e)}")
        return None


def get_counter():
    """Get the current counter value from the counter file or create it if it doesn't exist."""
    counter_file = "ft_otp.counter"
    
    try:
        if os.path.exists(counter_file):
            with open(counter_file, "r") as f:
                counter = int(f.read().strip())
        else:
            counter = 0
            with open(counter_file, "w") as f:
                f.write(str(counter))
        
        return counter
    
    except Exception as e:
        print(f"Error managing counter: {str(e)}")
        return 0


def update_counter(counter):
    """Update the counter value in the counter file."""
    counter_file = "ft_otp.counter"
    
    try:
        with open(counter_file, "w") as f:
            f.write(str(counter))
    except Exception as e:
        print(f"Error updating counter: {str(e)}")


def hotp(key, counter, digits=6):
    """
    Generate an HOTP value based on RFC 4226.
    
    Args:
        key: The secret key in hexadecimal format
        counter: The counter value
        digits: The number of digits in the OTP (default: 6)
    
    Returns:
        A string containing the HOTP value
    """
    key_bytes = binascii.unhexlify(key)
    
    counter_bytes = struct.pack(">Q", counter)
    
    h = hmac.new(key_bytes, counter_bytes, hashlib.sha1).digest()
    
    offset = h[-1] & 0xf
    binary = ((h[offset] & 0x7f) << 24 |
              (h[offset + 1] & 0xff) << 16 |
              (h[offset + 2] & 0xff) << 8 |
              (h[offset + 3] & 0xff))
    
    hotp_value = binary % (10 ** digits)
    
    return f"{hotp_value:0{digits}d}"


def generate_password():
    """Generate a new OTP based on the stored key."""
    hex_key = get_stored_key()
    if hex_key is None:
        return
    
    counter = get_counter()
    new_counter = counter + 1
    
    password = hotp(hex_key, counter)
    
    update_counter(new_counter)
    
    return password


def main():
    parser = argparse.ArgumentParser(description='HOTP-based one-time password generator')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-g', metavar='hex_key', help='Store a hexadecimal key of at least 64 characters')
    group.add_argument('-k', action='store_true', help='Generate a new temporary password')
    
    args = parser.parse_args()
    
    if args.g:
        store_key(args.g)
    elif args.k:
        password = generate_password()
        if password:
            print(password)


if __name__ == "__main__":
    main()
