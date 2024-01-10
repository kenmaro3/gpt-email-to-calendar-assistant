
from calendar_agent.GoogleCalendarLib import GoogleCalendarTool
from email_scraper.EmailParserLib import GmailTool
from langchain.chat_models import ChatOpenAI
import json

if __name__ == '__main__':
    # Test Google Calendar API
    # calendar = GoogleCalendarLib()
    # calendar.get_events()

    llm = ChatOpenAI(temperature=0)

    # gmail tool
    gmail_tool = GmailTool(credentials_file="credentials.yml", num_to_parse=5, llm=llm, memory=None)


    # calendar tool
    calendar_tool = GoogleCalendarTool(credentials_file="credentials.json", llm=ChatOpenAI(temperature=0), memory=None)

    # run scraping
    email_contents = gmail_tool.run_scraping()
    print("email_contents: ", email_contents)
    res = []

    # feed email to llm and get summary if something should be added to calendar
    for email_content in email_contents:
        res.append(gmail_tool.run_summary(json.dumps(email_content, ensure_ascii=False)))
    
    print("done summarizing: ", res)
    
    # add to calender
    for el in res:
        calendar_tool.run(el)


