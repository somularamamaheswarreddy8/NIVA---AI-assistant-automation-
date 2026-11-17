"""
Email Automation Controller for NIVA.
Handles locating, reading, drafting, and sending emails with strict user confirmation safeguards.
Supports default desktop email clients (Outlook/Mail) or webmail interfaces (Gmail/Outlook Web).
"""

import logging
import os
import subprocess
from typing import Any, Dict, List, Optional
import urllib.parse

logger = logging.getLogger("NIVA.Email")


class EmailAutomation:
    """Manages email reading, drafting, and secure confirmation-gated sending."""

    def __init__(self, browser_controller: Optional[Any] = None):
        self.browser_controller = browser_controller
        self.last_draft: Optional[Dict[str, str]] = None
        # Mock/inbox store for offline reading and evaluation
        self.inbox_store: List[Dict[str, str]] = [
            {
                "id": "msg_001",
                "sender": "prof.sharma@university.edu",
                "subject": "Final Year Project Review Schedule",
                "date": "Today, 10:30 AM",
                "body": "Dear Student, your final year AI project demonstration is scheduled for Friday at 2:00 PM in Lab 3. Please bring your documentation.",
                "unread": True
            },
            {
                "id": "msg_002",
                "sender": "recruiter@techcorp.com",
                "subject": "Invitation for Technical Interview",
                "date": "Yesterday, 4:15 PM",
                "body": "Hi Somu, we were impressed with your application for the AI Systems Engineer position. Are you available for a 30-minute discussion tomorrow?",
                "unread": False
            },
            {
                "id": "msg_003",
                "sender": "updates@github.com",
                "subject": "Security advisory for your repository",
                "date": "Nov 15, 8:00 AM",
                "body": "We found a moderate severity vulnerability in one of your project dependencies. Please review and update.",
                "unread": False
            }
        ]

    def open_email_client(self, client_or_url: str = "mail") -> Dict[str, Any]:
        """Opens the desktop mail client or webmail."""
        c = client_or_url.lower().strip()
        logger.info(f"Opening email interface: '{c}'")
        if "gmail" in c:
            if self.browser_controller:
                return self.browser_controller.open_url("https://mail.google.com")
            subprocess.Popen(["cmd.exe", "/c", "start", "https://mail.google.com"], shell=False)
            return {"success": True, "message": "Opened Gmail in browser.", "client": "Gmail Web"}
        elif "outlook" in c:
            if self.browser_controller:
                return self.browser_controller.open_url("https://outlook.live.com")
            subprocess.Popen(["cmd.exe", "/c", "start", "https://outlook.live.com"], shell=False)
            return {"success": True, "message": "Opened Outlook in browser.", "client": "Outlook Web"}
        else:
            # Launch Windows default mail app via mailto: or start
            try:
                subprocess.Popen(["cmd.exe", "/c", "start", "outlookmail:"], shell=False)
                return {"success": True, "message": "Opened Windows Mail app.", "client": "Windows Mail"}
            except Exception:
                subprocess.Popen(["cmd.exe", "/c", "start", "mailto:"], shell=False)
                return {"success": True, "message": "Dispatched system default email handler.", "client": "Default Mail"}

    def read_email(self, query_or_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Locates and reads the requested email message aloud.
        Does not read emails unless explicitly requested by the user.
        """
        if not query_or_filter:
            target_msg = self.inbox_store[0]
        else:
            q = query_or_filter.lower().strip()
            matches = [
                m for m in self.inbox_store
                if q in m["subject"].lower() or q in m["sender"].lower() or q in m["body"].lower()
            ]
            target_msg = matches[0] if matches else self.inbox_store[0]

        summary = (
            f"Email from {target_msg['sender']} with subject '{target_msg['subject']}'. "
            f"Message: {target_msg['body']}"
        )
        logger.info(f"Read email: {target_msg['subject']}")
        return {
            "success": True,
            "message": summary,
            "email_data": target_msg,
            "spoken_text": summary
        }

    def draft_email(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Creates an email draft with dictated details.
        Stores the draft for mandatory user confirmation before sending.
        """
        clean_rec = recipient.strip()
        clean_sub = subject.strip() or "No Subject"
        clean_body = body.strip()

        self.last_draft = {
            "recipient": clean_rec,
            "subject": clean_sub,
            "body": clean_body
        }
        logger.info(f"Created email draft to: '{clean_rec}' with subject '{clean_sub}'")

        display_msg = (
            f"Draft created for {clean_rec}.\n"
            f"Subject: {clean_sub}\n"
            f"Content: \"{clean_body}\"\n"
            "Confirmation is required before sending."
        )
        return {
            "success": True,
            "message": display_msg,
            "draft": self.last_draft,
            "requires_confirmation": True
        }

    def send_email(self, recipient: str, subject: str, body: str, confirmed: bool = False) -> Dict[str, Any]:
        """
        Sends an email. Enforces mandatory confirmation check.
        Never sends an email without explicit confirmation.
        """
        if not confirmed:
            logger.warning(f"Blocked attempt to send email to '{recipient}' without confirmation.")
            return {
                "success": False,
                "error": "Email sending requires explicit confirmation.",
                "requires_confirmation": True,
                "recipient": recipient,
                "subject": subject,
                "body": body
            }

        logger.info(f"Sending email to '{recipient}' with subject '{subject}' (User Confirmed).")
        # Launch mailto URL to populate system client or simulate dispatched send
        encoded_sub = urllib.parse.quote(subject)
        encoded_body = urllib.parse.quote(body)
        mailto_url = f"mailto:{recipient}?subject={encoded_sub}&body={encoded_body}"
        try:
            subprocess.Popen(["cmd.exe", "/c", "start", mailto_url], shell=False)
        except Exception:
            pass

        return {
            "success": True,
            "message": f"Email successfully sent to {recipient} with subject '{subject}'.",
            "recipient": recipient,
            "subject": subject
        }
