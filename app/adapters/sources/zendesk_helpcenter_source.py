import requests
from bs4 import BeautifulSoup
from app.config.settings import (
    ZENDESK_SUBDOMAIN,
    ZENDESK_EMAIL,
    ZENDESK_API_TOKEN,
    ZENDESK_LOCALE,
)
 
 
class ZendeskHelpCenterSource:
    def __init__(
        self,
        subdomain=None,
        email=None,
        api_token=None,
        locale=None,
        ):
        self.subdomain = subdomain or ZENDESK_SUBDOMAIN
        self.email = email or ZENDESK_EMAIL
        self.api_token = api_token or ZENDESK_API_TOKEN
        self.locale = locale or ZENDESK_LOCALE
        self.auth = (f"{self.email}/token", self.api_token)
 
    def fetch_all_public_articles(self):
        url = f"https://{self.subdomain}.zendesk.com/api/v2/help_center/{self.locale}/articles.json"
        articles = []
 
        while url:
            resp = requests.get(url, auth=self.auth)
            resp.raise_for_status()
            data = resp.json()
 
            for article in data.get("articles", []):
                if article.get("draft"):
                    continue
                #if article.get("user_segment_id") or article.get("user_segment_ids"):
                    #continue
                articles.append(article)
 
            url = data.get("next_page")
 
        return articles
 
    def fetch_incremental_articles(self, start_time: int):
        url = f"https://{self.subdomain}.zendesk.com/api/v2/help_center/incremental/articles.json?start_time={start_time}"
        articles = []
        end_time = start_time
 
        while url:
            resp = requests.get(url, auth=self.auth)
            resp.raise_for_status()
            data = resp.json()
 
            for article in data.get("articles", []):
                if article.get("draft"):
                    continue
                # if article.get("user_segment_id") or article.get("user_segment_ids"):
                #     continue
                articles.append(article)
 
            end_time = data.get("end_time", end_time)
            url = data.get("next_page")
 
        return articles, end_time
 
    def extract_text_and_images(self, article: dict):
        body_html=article.get("body")or ""
        soup = BeautifulSoup(body_html, "html.parser")
        text = soup.get_text("\n")
        text = "\n".join([t.strip() for t in text.splitlines() if t.strip()])
 
        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                images.append({
                    "url": src,
                    "alt": img.get("alt", "")
                })
 
        return text, images