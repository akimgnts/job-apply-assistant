"""Gmail tracking uses isolated SQLite and mocked Gmail only."""
import base64
from datetime import datetime
from unittest.mock import Mock
import pytest
from app.services.gmail_service import parse_message, fetch_page
from app.services.email_tracking_service import classify_email


def test_nested_mime_headers_and_utc():
    msg={'id':'m1','threadId':'t1','internalDate':'1700000000000','labelIds':['INBOX'],'payload':{
        'headers':[{'name':'from','value':'Ada <ada@example.org>'},{'name':'subject','value':'Entretien'}, {'name':'to','value':'candidate@example.net'}],
        'parts':[{'mimeType':'multipart/alternative','parts':[{'mimeType':'text/plain','body':{'data':base64.urlsafe_b64encode('Bonjour à vous'.encode()).decode().rstrip('=')}}]}]}}
    parsed=parse_message(msg)
    assert parsed['sender_email']=='ada@example.org'
    assert parsed['subject']=='Entretien'
    assert parsed['body_text']=='Bonjour à vous'
    assert parsed['received_at']==datetime(2023,11,14,22,13,20)


def test_fetch_page_preserves_continuation():
    service=Mock()
    service.users.return_value.messages.return_value.list.return_value.execute.return_value={'messages':[{'id':'m1'}],'nextPageToken':'page2'}
    service.users.return_value.messages.return_value.get.return_value.execute.return_value={'id':'m1','internalDate':'1700000000000','payload':{}}
    page=fetch_page(service,'me','query',25,'page1')
    assert page['next_page_token']=='page2'
    assert len(page['messages'])==1
    assert service.users.return_value.messages.return_value.list.call_args.kwargs['pageToken']=='page1'


def test_classification_does_not_treat_unknown_or_auto_reply_as_human():
    assert classify_email({'subject':'Thanks','body_text':'Received','labels':[]})['type']=='unknown'
    assert classify_email({'subject':'Candidature reçue','body_text':'Nous avons bien reçu votre candidature','labels':[]})['type']=='acknowledgement'
    assert classify_email({'subject':'Entretien','body_text':'Nous vous proposons un entretien','labels':[]})['type']=='interview_request'
    assert classify_email({'subject':'Re: Entretien','body_text':'Ma réponse','labels':['SENT']})['type']=='application_sent'
