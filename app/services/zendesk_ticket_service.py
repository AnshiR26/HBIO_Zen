import base64
import requests


class ZendeskTicketService:
    def __init__(self, subdomain: str, email: str, api_token: str, sc_app_id: str = None, sc_key_id: str = None, sc_secret: str = None):
        clean_subdomain = (subdomain or "").strip()
        clean_email = (email or "").strip()
        clean_token = (api_token or "").strip()

        self.base_url   = f"https://{clean_subdomain}.zendesk.com"
        self.sc_app_id  = (sc_app_id  or "").strip()
        self.sc_key_id  = (sc_key_id  or "").strip()
        self.sc_secret  = (sc_secret  or "").strip()

        # ── Zendesk Support API session (email/token auth) ──
        zd_cred = f"{clean_email}/token:{clean_token}"
        zd_enc  = base64.b64encode(zd_cred.encode("utf-8")).decode("utf-8")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type":  "application/json",
            "Accept":        "application/json",
            "Authorization": f"Basic {zd_enc}",
        })

        # ── Sunshine Conversations API session (SC key:secret auth) ──
        if self.sc_key_id and self.sc_secret:
            sc_cred = f"{self.sc_key_id}:{self.sc_secret}"
            sc_enc  = base64.b64encode(sc_cred.encode("utf-8")).decode("utf-8")
            self.sc_session = requests.Session()
            self.sc_session.headers.update({
                "Content-Type":  "application/json",
                "Accept":        "application/json",
                "Authorization": f"Basic {sc_enc}",
            })
        else:
            self.sc_session = None

    def create_ticket(
        self,
        subject: str,
        description: str,
        requester_name: str,
        requester_email: str,
    ):
        url = f"{self.base_url}/api/v2/tickets.json"

        payload = {
            "ticket": {
                "subject": subject,
                "comment": {
                    "body": description
                },
                "requester": {
                    "name": requester_name or "Widget User",
                    "email": requester_email
                },
                "tags": ["bot_created", "widget_ticket"]
            }
        }

        response = self.session.post(
            url,
            json=payload,
            timeout=12,
        )

        print("ZENDESK DEBUG: status:", response.status_code, flush=True)
        print("ZENDESK DEBUG: body:", response.text, flush=True)

        response.raise_for_status()
        return response.json()

    def add_ticket_comment(self, ticket_id: int, comment_body: str, public: bool = False, subject: str = None):
        url = f"{self.base_url}/api/v2/tickets/{ticket_id}.json"

        payload = {
            "ticket": {
                "comment": {
                    "body": comment_body,
                    "public": public
                }
            }
        }

        if subject:
            payload["ticket"]["subject"] = subject

        response = self.session.put(
            url,
            json=payload,
            timeout=12,
        )

        print("ZENDESK COMMENT DEBUG: status:", response.status_code, flush=True)
        print("ZENDESK COMMENT DEBUG: body:", response.text, flush=True)

        response.raise_for_status()
        return response.json()

    def get_user_by_email(self, email: str) -> dict:
        if not email:
            return None
        url = f"{self.base_url}/api/v2/users/search.json"
        params = {"query": f"type:user email:{email}"}
        response = self.session.get(url, params=params, timeout=12)
        response.raise_for_status()
        results = response.json().get("users") or []
        return results[0] if results else None

    def get_user_by_external_id(self, external_id: str) -> dict:
        if not external_id:
            return None
        url = f"{self.base_url}/api/v2/users/search.json"
        params = {"query": f"type:user external_id:{external_id}"}
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        results = response.json().get("users") or []
        return results[0] if results else None

    def get_user_by_id(self, support_user_id: int) -> dict:
        """Fetch a Zendesk Support user by their integer Support user ID."""
        if not support_user_id:
            return None
        url = f"{self.base_url}/api/v2/users/{support_user_id}.json"
        response = self.session.get(url, timeout=12)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json().get("user")

    def get_user_by_sc_user_id(self, sc_user_id: str) -> dict:
        """
        Resolve a Zendesk Support user from a Sunshine Conversations user ID.

        ROOT CAUSE FIX:
          Sunshine webhook sends author.userId (e.g. '6a0c41...').
          This is the SC user ID — NOT a Zendesk Support external_id.

        CONFIRMED via live test:
          GET https://api.smooch.io/v2/apps/{appId}/users/{scUserId}
          (with SC key:secret auth) returns:
            user.zendeskId  = Zendesk Support user ID (integer string)
            user.identities = [{type: 'email', value: 'prachia@parkar.in'}]

          The email is directly available — no second API call needed.
        """
        if not sc_user_id or not self.sc_app_id:
            print(f"SC USER LOOKUP: Missing sc_user_id or sc_app_id, skipping.", flush=True)
            return None

        if not self.sc_session:
            print("SC USER LOOKUP: No SC session (sc_key_id/sc_secret not set). Skipping.", flush=True)
            return None

        try:
            # Use api.smooch.io with SC key:secret auth
            # (ZD subdomain /sc/ also works but requires same SC auth)
            sc_url = f"https://api.smooch.io/v2/apps/{self.sc_app_id}/users/{sc_user_id}"
            print(f"SC USER LOOKUP: GET {sc_url}", flush=True)

            sc_resp = self.sc_session.get(sc_url, timeout=8)

            if sc_resp.status_code in (404, 422):
                print(f"SC USER LOOKUP: User not found (status {sc_resp.status_code})", flush=True)
                return None

            sc_resp.raise_for_status()
            sc_data = sc_resp.json()
            sc_user = sc_data.get("user") or {}

            # Extract email directly from identities array
            email = None
            for identity in sc_user.get("identities") or []:
                if identity.get("type") == "email" and identity.get("value"):
                    email = identity["value"]
                    break

            # zendeskId is the Zendesk Support user integer ID
            zendesk_id = sc_user.get("zendeskId")
            profile    = sc_user.get("profile") or {}
            name = f"{profile.get('givenName', '')} {profile.get('surname', '')}".strip() or "Widget User"

            print(
                f"SC USER LOOKUP: Resolved — id={zendesk_id}, email={email}, name={name}",
                flush=True,
            )

            if email or zendesk_id:
                return {
                    "id":    int(zendesk_id) if zendesk_id else None,
                    "email": email or "",
                    "name":  name,
                }

        except Exception as e:
            print(f"SC USER LOOKUP ERROR: {e}", flush=True)

        return None

    def get_user_segments(self, user_id: int) -> list:
        if not user_id:
            return []
        url = f"{self.base_url}/api/v2/help_center/users/{user_id}/user_segments.json"
        response = self.session.get(url, timeout=12)
        response.raise_for_status()
        return response.json().get("user_segments") or []
