from GoogleCalendarLib import GoogleCalendarTool

if __name__ == "__main__":
    credentials_file = "credentials.json"

    from langchain.chat_models import ChatOpenAI

    # モデル作成
    llm = ChatOpenAI(temperature=0)

    calendar_tool = GoogleCalendarTool(credentials_file, llm=ChatOpenAI(temperature=0), memory=None)
    calendar_tool.run('明日の12時にデートの約束を入れて')
    # calendar_tool.run('明日の12時のデートの約束を削除して')