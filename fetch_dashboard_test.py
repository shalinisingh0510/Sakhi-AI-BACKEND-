import urllib.request
import urllib.error
import json
import sys

def fetch_dashboard():
    req = urllib.request.Request("http://localhost:8000/api/v1/wellness/dashboard")
    # We need a valid token. Or we can just print the 500 error if it doesn't need auth, wait, it DOES need auth.
    # Without auth it returns 401 Unauthorized.
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        print(e.read().decode())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_dashboard()
