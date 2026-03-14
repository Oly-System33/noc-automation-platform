import os
import requests
from dotenv import load_dotenv

load_dotenv()


class JiraService:

    def __init__(self):
        self.base_url = os.getenv("JIRA_URL")
        self.email = os.getenv("JIRA_EMAIL")
        self.api_token = os.getenv("JIRA_API_TOKEN")
        self.project_key = os.getenv("JIRA_PROJECT_KEY")
        self.issue_type = os.getenv("JIRA_ISSUE_TYPE")

    def create_ticket(self, summary, description):

        url = f"{self.base_url}/rest/api/3/issue"

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        auth = (self.email, self.api_token)

        payload = {
            "fields": {
                "project": {
                    "key": self.project_key
                },
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": description
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {
                    "name": self.issue_type
                }
            }
        }

        response = requests.post(url, json=payload, headers=headers, auth=auth)

        return response.json()
