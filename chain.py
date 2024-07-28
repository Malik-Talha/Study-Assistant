from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.tools.tavily_search import TavilySearchResults

from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.


import os
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")
from langgraph.prebuilt.tool_node import ToolNode


tools = [TavilySearchResults(max_results=3)]

# MODEL = "gpt-3.5-turbo-0125"
MODEL = "gpt-4o"

def get_tool_node():
    return ToolNode(tools=tools)
def get_outliner_chain():
    class Outliner(BaseModel):
        """ Outline to create """
        outline: List[str] = Field("list of outline headings in sequence to cover whole topic(s)/question(s)")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system",
             "You are helpful assistant. You take a question or topic and then create an outline out of it for university exam. "
             "The outline covers all the headings and no important headings are left in order to prepare for exam.\n"
             "{messages}")
            # MessagesPlaceholder(variable_name='feedback', optional=True)
        ]
    )

    chat_llm = ChatOpenAI(model=MODEL, temperature=0.0).with_structured_output(Outliner)

    chain = {'messages': lambda x: x['messages']} | prompt | chat_llm

    return chain.with_config({'run_name': "Outliner"})

def get_researcher_chain():

    tools = [TavilySearchResults()]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system",
             "You are helpful assistant researcher. You take an outline and current topic/heading you are tasked to research on and "
             "you use tools to do search and write. Do not write anything other than for current heading of the outline and wait for the next headings to come to write about them.\n"
             "Your goal is to do best while researching. If you get any criticism, improve on it. DO NOT use search tool for a topic more than two times\n"
             "Current topic/heading to research and write on: {heading}\n\n"
             "Follow the conversation below:\n"
             "{messages}"
             # "Outline: {outline}\n"
              )
            # MessagesPlaceholder(variable_name="messages")
        ]
    )

    chat_llm = ChatOpenAI(model=MODEL, temperature=0.0).bind_tools(tools)

    chain = {
            # 'outline': lambda x: x['outline'],
            'heading': lambda x: x['heading'],
            'messages': lambda x: x['messages']
                } | prompt | chat_llm

    return chain.with_config({'run_name': "Researcher"})

def get_critic_chain():
    class Critic(BaseModel):
        route: str = Field(description="where to go? use 'critic' if you are not satisfied and have a criticism; use 'next' if no criticism.")
        criticism: Optional[str] = Field(description='constructive criticism')

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system",
             "You are helpful assistant profressor. Your goal is to supervise the quality of research done by a researcher for university exam.\n"
             "You take current topic/heading provide constructive criticim. Do consider outline; don't ask for something that needs to come later.\n"
             "Your focus MUST be to check if the content/research is enough for a Bachelors level university exam.\n"
             "Do not let the researcher write the content for other headings/topics of outline under a headline/topic.\n"
             "IF the last message is ToolCall, you must write content next."
             "Current topic/heading: {heading}\n\n"
             "{messages}")
        ]
    )

    chat_llm = ChatOpenAI(model=MODEL, temperature=0.0).with_structured_output(Critic)

    chain = {
                'heading': lambda x: x['heading'],
                'messages': lambda x: x['messages']
            } | prompt | chat_llm

    return chain.with_config({'run_name': "Critic"})
