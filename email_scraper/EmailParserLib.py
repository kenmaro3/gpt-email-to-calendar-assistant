import yaml
import imaplib
import email
from bs4 import BeautifulSoup
import pprint
import dateutil.parser

from langchain import PromptTemplate, LLMChain


class GmailScraper:
    def __init__(self, credentials_file="credentials.yml", num_to_parse=5):
        self.num_to_parse = num_to_parse

        with open(credentials_file) as f:
            content = f.read()

        # from credentials.yml import user name and password
        my_credentials = yaml.load(content, Loader=yaml.FullLoader)

        #Load the user name and passwd from yaml file
        user, password = my_credentials["user"], my_credentials["password"]

        #URL for IMAP connection
        imap_url = 'imap.gmail.com'

        # Connection with GMAIL using SSL
        self.my_mail = imaplib.IMAP4_SSL(imap_url)

        # Log in using your credentials
        self.my_mail.login(user, password)
    
    def get_emails(self):
        self.my_mail.select('inbox')

        #Define Key and Value for email search
        #For other keys (criteria): https://gist.github.com/martinrusev/6121028#file-imap-search
        status, [data] = self.my_mail.search(None, "(UNSEEN)")

        mail_id_list = data.split()  #IDs of all emails that we want to fetch 
        #print("mail_id_list:", mail_id_list)

        print("Number of emails:", len(mail_id_list))

        self.msgs = [] # empty list to capture all messages
        contents = []
        #Iterate through messages and extract data into the msgs list
        for i in range(min(self.num_to_parse, len(mail_id_list))):
            num = mail_id_list[i]
            content_dict = {}
            result, d = self.my_mail.fetch(num, '(RFC822)') #RFC822 returns whole message (BODY fetches just body)
            raw_email = d[0][1]
            #文字コード取得用
            msg = email.message_from_string(raw_email.decode('utf-8'))
            msg_encoding = email.header.decode_header(msg.get('Subject'))[0][1] or 'iso-2022-jp'
            #パースして解析準備
            msg = email.message_from_string(raw_email.decode(msg_encoding))

            #print(msg.keys()) 

            # get from
            fromObj = email.header.decode_header(msg.get('From'))
            addr = ""
            for f in fromObj:
                if isinstance(f[0],bytes):
                    addr += f[0].decode(msg_encoding)
                else:
                    addr += f[0]
            content_dict["from"] = addr

            # get subject   
            subject = email.header.decode_header(msg.get('Subject'))
            title = ""
            for sub in subject:
                if isinstance(sub[0],bytes):
                    title += sub[0].decode(msg_encoding)
                else:
                    title += sub[0]
            content_dict["subject"] = title

            # get date
            date = dateutil.parser.parse(msg.get('Date')).strftime("%Y/%m/%d %H:%M:%S")
            content_dict["date"] = date

            # get body
            body = ""
            if msg.is_multipart():
                for payload in msg.get_payload():
                    if payload.get_content_type() == "text/plain":
                        body = payload.get_payload()
            else:
                if msg.get_content_type() == "text/plain":
                    body = msg.get_payload()   
            content_dict["body"] = body
            
            contents.append(content_dict)

            # put back unseen
            self.my_mail.store(num, '-FLAGS','\\SEEN')
        
        return contents


class GmailTool:
    def __init__(self, credentials_file="credentials.yml", num_to_parse=5, llm=None, memory=None, prompt="""
        you will be given the email content. If this email contains something that you need to add to the calendar,
        report it to tell to add that event to calendar with detail.
        if not please say "nothing".

    History: {chat_history}
    Email content: {email_content}
                 """):
        self.gmail = GmailScraper(credentials_file=credentials_file, num_to_parse=num_to_parse)
        self.llm = llm
        if self.llm is None:
            raise ValueError("llm is None")
        self.memory = memory

        self.prompt = PromptTemplate(
            template=prompt,
            input_variables=["email_content", "chat_history"],
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    def run_scraping(self):
        return self.gmail.get_emails()
    
    def run_summary(self, email_content):
        _input = self.prompt.format(email_content=email_content, chat_history=self.memory)
        output = self.chain.run({'email_content': email_content, 'chat_history': self.memory})
        return output

