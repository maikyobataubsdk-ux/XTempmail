import random
import string
import requests

API_BASE = "https://api.mail.tm"

class MailService:
    def __init__(self, api_base=API_BASE):
        self.api_base = api_base.rstrip('/')

    def get_domains(self):
        """Fetch available domains from Mail.tm."""
        try:
            resp = requests.get(f"{self.api_base}/domains", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                members = data.get("hydra:member", [])
                return [d["domain"] for d in members if d.get("isAvailable", True)]
        except Exception as e:
            print(f"Error fetching domains: {e}")
        return []

    def create_account(self, custom_prefix=None, password=None):
        """Generate a new temporary email account and return (email, token, account_id)."""
        domains = self.get_domains()
        if not domains:
            return None, None, None

        domain = random.choice(domains)
        if not custom_prefix:
            custom_prefix = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))

        email = f"{custom_prefix}@{domain}"
        if not password:
            password = "".join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=12))

        try:
            reg_resp = requests.post(
                f"{self.api_base}/accounts",
                json={"address": email, "password": password},
                timeout=10
            )
            if reg_resp.status_code in (200, 201):
                acc_data = reg_resp.json()
                acc_id = acc_data.get("id")

                # Get auth token
                token_resp = requests.post(
                    f"{self.api_base}/token",
                    json={"address": email, "password": password},
                    timeout=10
                )
                if token_resp.status_code == 200:
                    token = token_resp.json().get("token")
                    return email, token, acc_id
        except Exception as e:
            print(f"Error creating account: {e}")

        return None, None, None

    def get_messages(self, token, page=1):
        """Fetch list of messages for the account token."""
        if not token:
            return []
        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"{self.api_base}/messages?page={page}", headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("hydra:member", [])
        except Exception as e:
            print(f"Error fetching messages: {e}")
        return []

    def get_message_detail(self, token, message_id):
        """Fetch detail of a specific message by ID."""
        if not token or not message_id:
            return None
        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"{self.api_base}/messages/{message_id}", headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"Error fetching message detail: {e}")
        return None

    def delete_message(self, token, message_id):
        """Delete a specific message by ID."""
        if not token or not message_id:
            return False
        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.delete(f"{self.api_base}/messages/{message_id}", headers=headers, timeout=10)
            return resp.status_code in (200, 204)
        except Exception as e:
            print(f"Error deleting message: {e}")
            return False
