import os
import base64
import json
import requests
import datetime
from anthropic import Anthropic
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
from email.utils import parsedate_to_datetime

load_dotenv()

# ========== CONFIG ==========
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")
GMAIL_LABEL_FILTER = "label:important newer_than:1d"
# ============================

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def gmail_auth():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def get_emails(service):
    result = service.users().messages().list(userId='me', q=GMAIL_LABEL_FILTER).execute()
    messages = result.get('messages', [])
    email_bodies = []

    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_data['payload'].get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        date_str = next((h['value'] for h in headers if h['name'] == 'Date'), None)
        email_date = parsedate_to_datetime(date_str).strftime("%Y-%m-%d") if date_str else datetime.datetime.today().strftime("%Y-%m-%d")

        parts = msg_data['payload'].get('parts', [])
        body = ''
        for part in parts:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode()
                    break

        email_bodies.append({
            "subject": subject,
            "from": sender,
            "body": body,
            "email_date": email_date
        })

    return email_bodies

import re

def classify_email_with_claude(email):
    email_body = f"Subject: {email['subject']}\nFrom: {email['from']}\n\n{email['body']}"
    email_date = email['email_date']
    system_message = """
        You are an AI that extracts job application details like below ones from an email.
        Given the following email, answer the questions below. Be accurate and do NOT consider job ads, job alerts, or job suggestions. ONLY process emails that are clear job application confirmations (i.e., when the user has applied for a job u can use ur knowledge to determine the job description and job title or designation for which user has applied)
        - company
        - job_title
        - application_date
        - job_location (if available)
        If application_date is not present, use {email_date}.
        Output the result in this JSON format:
        {{
        "confirmation": "Yes/No",
        "job_title": "...",
        "company": "...",
        "source": "...",
        "applied_date": "YYYY-MM-DD"
        }}
        """
    user_message = f"""
        Email Date: {email_date}
        Email Body:
        {email_body}
        """

    client = Anthropic(api_key=os.environ["CLAUDE_API_KEY"])

    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1000,
        temperature=0,
        system=system_message.strip(),
        messages=[
            {"role": "user", "content": user_message.strip()}
        ]
    )

    try:
        full_output = response.content[0].text
        json_str = extract_json(full_output)
        return json.loads(json_str)
    except Exception as e:
        print(f"Error parsing Claude output: {e}")
        print("Claude raw output:", response.text)
        return None

def extract_json(text):
    """Extracts the first valid JSON object found in a text block."""
    match = re.search(r'\{.*?\}', text, re.DOTALL)
    if match:
        return match.group(0)
    raise ValueError("No JSON object found in Claude output")

def send_to_notion(data):
    print(data)
    notion_url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    payload = {
        "parent": { "database_id": NOTION_DB_ID },
        "properties": {
            "Company": { "title": [{ "text": { "content": data['company'] } }] },
            "Job Title": { "rich_text": [{ "text": { "content": data['job_title'] } }] },
            "Applied Date": { "date": { "start": data['applied_date'] } },
            "Status": { "select": { "name": "Applied" } }
        }
    }

    res = requests.post(notion_url, headers=headers, json=payload)
    if res.status_code != 200:
        print(f"Notion API Error: {res.status_code}, {res.text}")
    else:
        print(f"✅ Added to Notion: {data['job_title']} at {data['company']}")

def main():
    service = gmail_auth()
    emails = get_emails(service)

    for email in emails:
        result = classify_email_with_claude(email)
        if result and result.get("confirmation", "").lower() == "yes":
            send_to_notion(result)

if __name__ == "__main__":
    main()
