from langchain_core.messages import BaseMessage, HumanMessage

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import tools_condition

import operator
from typing import Annotated, Sequence, TypedDict, List
import time

from chain import get_tool_node, get_outliner_chain, get_researcher_chain, get_critic_chain



# define agent state
class AgentState(TypedDict):
    outline: List[str]
    heading_index: int
    sender: str
    content: Annotated[str, operator.add]
    messages: Annotated[Sequence[BaseMessage], operator.add]

# get tool node for all tools
tools_node = get_tool_node()
# get all chains
outliner_chain = get_outliner_chain()
researcher_chain = get_researcher_chain()
critic_chain = get_critic_chain()


# define agent call functions
def outliner(state: AgentState):
    outline = outliner_chain.invoke({'messages': state['messages']})
    return {'outline': outline.outline, 'messages': [outline], 'heading_index': 0, 'sender': "outliner"}

def outline_feedback(state: AgentState):
    feedback = input("Enter your feedback for Outline: ")
    return {'messages': [HumanMessage(content=feedback)]}

def researcher(state: AgentState):
    heading_index = state['heading_index']
    outline_lst = state['outline']
    #
    # outline = ""
    # for i, heading in enumerate(outline_lst):
    #     outline += f"{i + 1}. {heading}\n"

    research = researcher_chain.invoke({
        # "outline": outline,
        'heading': outline_lst[heading_index],
        'messages': state['messages']
    })
    return {"messages": [research], "sender": 'researcher'}

def critic(state: AgentState):
    heading_index = state['heading_index']
    outline = state['outline']
    messages = state['messages']

    criticism = critic_chain.invoke({
        'messages': messages,
        'heading': outline[heading_index]
    })

    update = {'messages': [criticism], 'sender': 'critic'}
    # update index to next heading if no critic
    if criticism.route == 'next':
        # save nice content
        update['content'] = messages[-1].content + "\n\n"
        update['heading_index'] = heading_index+1
        time.sleep(5)
    return update


# define router functions for navigation in graph
def critic_conditions(state: AgentState):
    messages = state['messages']
    if route := messages[-1].route:
        if route == "critic":
            return "researcher"
        elif route == 'next':
            outline_len = len(state['outline'])
            heading_index = state['heading_index']
            if (heading_index+1) > (outline_len):
                # no more headings/topics left

                # first save the content in text file
                with open("content.md", 'w', encoding="utf-8") as f:
                    f.write(state['content'])

                return "end"
            else:
                return "researcher"

def outline_feedback_conditions(state: AgentState):
    print(state['messages'][-1])
    feedback = input("Any Feedback? y/n: ")
    if feedback == 'n':
        return "n"
    elif feedback=='y':
        return "y"
    else:
        return "invalid"

# define graph
graph = StateGraph(AgentState)

# add nodes
graph.add_node("outliner", outliner)
graph.add_node("outline_feedback", outline_feedback)
graph.add_node("researcher", researcher)
graph.add_node("critic", critic)
graph.add_node("tools_node", tools_node)

# entry point
graph.set_entry_point("outliner")


# add normal edges
# graph.add_edge("outliner", "researcher")
graph.add_edge("outline_feedback", "outliner")
# add conditional edges
graph.add_conditional_edges("outliner", outline_feedback_conditions, {"y": "outline_feedback", "n": "researcher", "invalid": 'outline_feedback'})
graph.add_conditional_edges('researcher', tools_condition, {"tools": "tools_node", "__end__": "critic"})
graph.add_conditional_edges("tools_node", lambda x: x['sender'], {'researcher': "researcher"})
graph.add_conditional_edges('critic', critic_conditions, {"researcher": "researcher", "end": END})


app = graph.compile().with_config({'run_name': "study_assistant"}).with_config({'recursion_limit': 200})
# app.get_graph().draw_mermaid_png(output_file_path="graph_mermaid_v2.png")

text = "\n\n------------------NEW RUN---------------------------------\n"
query = input("Type the topic: ")
for event in app.stream({'messages': [HumanMessage(content=query)]}):
    for v in event.values():
        print(v['messages'])
        text += str(v['messages'])
        # if input("\nStop?......") == "y":
        #     break
with open("log.md", 'a', encoding="utf-8") as f:
    f.write(text + "\n\n")
# result = outliner.invoke({'messages': [HumanMessage(content="Building the entrepreneural team. Role of Directors and advisors.")]})
# print(result)
