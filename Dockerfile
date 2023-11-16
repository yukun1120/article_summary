FROM python:3

RUN python -m pip install openai
RUN python -m pip install python-dotenv
RUN python -m pip install PyPDF2
RUN python -m pip install notion-client
RUN python -m pip install requests
RUN python -m pip install feedparser
RUN python -m pip install schedule
