import os
import datetime
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from langchain.output_parsers import PydanticOutputParser

from langchain import PromptTemplate, LLMChain

class CalendarAction(BaseModel):
    action: str = Field(description="The action to be performed. Supported actions are 'get', 'create', 'search', 'update', and 'delete'.")

    class EventData(BaseModel):
        summary: Optional[str] = Field(None, description="The summary of the event.")
        start: Optional[Dict[str, str]] = Field(None, description="The start time of the event. It contains 'dateTime' and 'timeZone' keys.")
        end: Optional[Dict[str, str]] = Field(None, description="The end time of the event. It contains 'dateTime' and 'timeZone' keys.")
        query: Optional[str] = Field(None, description="The search query to find matching events.")
        updated_data: Optional[Dict[str, Any]] = Field(None, description="The updated data for the event. It contains keys to update such as 'summary', 'start', and 'end'.")

    event_data: Optional[EventData] = Field(None, description="The data for the event or query. Contains fields such as 'summary', 'start', 'end', 'query', and 'updated_data'.")

class GoogleCalendar:
    def __init__(self, credentials_file, scopes=['https://www.googleapis.com/auth/calendar']):
        self.scopes = scopes
        self.credentials = self._get_credentials(credentials_file)
        if self.credentials is None:
            raise ValueError("Error: 認証情報が見つかりませんでした。")
        self.service = build('calendar', 'v3', credentials=self.credentials)

    def _get_credentials(self, credentials_file):
        # クレデンシャルファイルから認証情報を取得
        creds = None
        if os.path.exists(credentials_file):
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, self.scopes)
            creds = flow.run_local_server(port=0)
        return creds

    def get_events(self, calendar_id='primary', time_min=None, time_max=None):
        # 現在の日時または指定された期間内のイベントを取得
        if time_min is None:
            time_min = datetime.datetime.utcnow().isoformat() + 'Z'
        if time_max is None:
            time_max = (datetime.datetime.utcnow() + datetime.timedelta(weeks=1)).isoformat() + 'Z'

        events_result = self.service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        return events

    def create_event(self, event_data, calendar_id='primary'):
        # 新しいイベントを作成
        created_event = self.service.events().insert(calendarId=calendar_id, body=event_data).execute()
        return created_event

    def update_event(self, event_id, updated_event_data, calendar_id='primary'):
        # 既存のイベントを更新
        updated_event = self.service.events().patch(calendarId=calendar_id, eventId=event_id, body=updated_event_data).execute()
        return updated_event

    def delete_event(self, event_id, calendar_id='primary'):
        # イベントを削除
        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

    def search_events(self, query, calendar_id='primary'):
        # イベントを検索
        events_result = self.service.events().list(
            calendarId=calendar_id,
            q=query,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        return events

    def process_json_data(self, json_data: str):
        data = CalendarAction.parse_raw(json_data)

        if data.action == "get":
            events = self.get_events()
            for event in events:
                print(event['summary'], event['start']['dateTime'])
            return events

        elif data.action == "create":
            event_data = data.event_data.dict()
            created_event = self.create_event(event_data)
            print("Event created:", created_event['id'])
            return "Finish."

        elif data.action == "search":
            query = data.event_data.query
            events = self.search_events(query)
            for event in events:
                print(event['summary'], event['start']['dateTime'])
            return events

        elif data.action == "update":
            query = data.event_data.query
            updated_data = data.event_data.updated_data

            today = datetime.datetime.utcnow().date()
            time_min = datetime.datetime.combine(today, datetime.time.min).isoformat() + 'Z'
            time_max = datetime.datetime.combine(today, datetime.time.max).isoformat() + 'Z'

            #events = self.search_events(query, time_min=time_min, time_max=time_max)
            events = self.search_events(query)
            for event in events[:20]:
                updated_event = self.update_event(event['id'], updated_data)
                print("Event updated:", updated_event['id'])
            return "Finish."

        elif data.action == "delete":
            query = data.event_data.query

            today = datetime.datetime.utcnow().date()
            time_min = datetime.datetime.combine(today, datetime.time.min).isoformat() + 'Z'
            time_max = datetime.datetime.combine(today, datetime.time.max).isoformat() + 'Z'

            #events = self.search_events(query, time_min=time_min, time_max=time_max)
            events = self.search_events(query)
            for event in events[:20]:
                self.delete_event(event['id'])
                print("Event deleted:", event['id'])
            return "Finish."

        else:
            print("Invalid action")
            return "Finish with Error!"



class GoogleCalendarTool:
    def __init__(self, credentials_file, llm=None, time_zone='JST', memory=None, prompt="""Follow the user query and take action on the calendar appointments.
    Current time: {current_time}, timeZone: JST.
    History: {chat_history}
    Format: {format_instructions}

    User Query: {query}
    Processing and reporting must be done in Japanese. If unclear, do not process and ask questions.""" ,scopes=['https://www.googleapis.com/auth/calendar']):
        self.cal = GoogleCalendar(credentials_file)
        self.llm = llm
        if self.llm is None:
            raise ValueError("Error: LLM is undefined.")
        self.time_zone = time_zone
        self.memory = memory
        # Parser に元になるデータの型を提供する
        self.parser =  PydanticOutputParser(pydantic_object=CalendarAction)
        self.prompt = PromptTemplate(
            template=prompt,
            input_variables=["query", "current_time", "chat_history"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    def run(self, query):
        _input = self.prompt.format_prompt(query=query, current_time=datetime.datetime.now(), chat_history=self.memory)
        output = self.chain.run({'query': query, 'current_time': datetime.datetime.now(), 'chat_history': self.memory})

        return self.cal.process_json_data(output)

