import base64
import os
import pickle

from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class EMail:
    def __init__(self, sender, to, subject, message_text):
        self.message = self.create_message(sender, to, subject, message_text)
        self.service = self.build_service()

    @staticmethod
    def create_message(sender, to, subject, message_text):
        """Create a message for an email.

        Args:
          sender: Email address of the sender.
          to: Email address of the receiver.
          subject: The subject of the email message.
          message_text: The text of the email message.

        Returns:
          An object containing a base64url encoded email object.
        """
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        return base64.urlsafe_b64encode(message.as_bytes())

    @staticmethod
    def build_service():
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server()
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        return build("gmail", "v1", creds)

    def send_message(self, user_id="me"):
        """Send an email message.

        Args:
          service: Authorized Gmail API service instance.
          user_id: User's email address. The special value "me"
          can be used to indicate the authenticated user.
          message: Message to be sent.

        Returns:
          Sent Message.
        """

        return self.service.users().messages().send(userId=user_id, body=self.message.execute())


if __name__ == '__main__':
    email = EMail("fxstempfel@gmail.com", "francois-xavier.stempfel@atos.net", "[Test] Gmail API", "HelloWorld")
    email.send_message()
