from langgraph.graph import StateGraph, END, START, MessagesState
from langgraph.prebuilt.tool_node import ToolNode
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import tools_condition
from typing import Literal

from src.tools import query_snowflake
from src.llm_manager import LLMManager
import src.schema_prompt as sp

class WorkflowManager:
    """Manager for creating and running the LangGraph agent workflow."""

    def __init__(self):
        self.tools = [query_snowflake]
        self.llm_manager = LLMManager(self.tools)
        self.max_attempts = 3
        self.state_graph = self.create_workflow()

    def create_workflow(self):
        workflow = StateGraph(MessagesState)

        # Define nodes
        workflow.add_node("snowflake_query_agent", self.call_snowflake_model)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_node("summary_agent", self.call_summary_model)

        # Define flow
        workflow.add_edge(START, "snowflake_query_agent")

        workflow.add_conditional_edges(
            "snowflake_query_agent",
            tools_condition,
        )

        workflow.add_edge("tools", "snowflake_query_agent")

        workflow.add_conditional_edges(
            "snowflake_query_agent",
            self.route_after_agent
        )

        workflow.add_edge("summary_agent", END)

        return workflow.compile(checkpointer=MemorySaver())

    def is_tool_result_successful(self, message):
        result = getattr(message, "tool_result", None)
        return result and isinstance(result, str) and "error" not in result.lower()

    def call_snowflake_model(self, state: MessagesState):
        user_message = state['messages'][-1]
        system_prompt = sp.get_schema_prompt()

        formatted_messages = [
            SystemMessage(content=system_prompt),
            user_message
        ]

        response = self.llm_manager.invoke_model(formatted_messages)

        if not isinstance(response, AIMessage):
            raise Exception("Expected AIMessage from LLMManager, but got something else.")

        return {"messages": [response]}

    def call_summary_model(self, state: MessagesState):
        tool_result = None
        for msg in reversed(state['messages']):
            if hasattr(msg, "tool_result") and msg.tool_result:
                tool_result = msg.tool_result
                break

        summary_prompt = f"""
You are a data summarization assistant. Use the tool result below and generate a meaningful natural language summary for visualization:

Tool Result:
{tool_result}

Summary:
"""
        formatted_messages = [
            SystemMessage(content=summary_prompt)
        ]

        response = self.llm_manager.invoke_model(formatted_messages)
        return {"messages": [response]}

    def call_model(self, state: MessagesState):
        messages = state['messages']
        response = self.llm_manager.invoke_model(messages)
        return {"messages": [response]}

    def run(self, input_message, thread_id):
        initial_state = {
            "messages": [HumanMessage(content=input_message)]
        }
        return self.state_graph.invoke(initial_state, config={"configurable": {"thread_id": thread_id}})

    def route_after_agent(self, state: MessagesState) -> Literal["tools", "summary_agent", END]:
        messages = state['messages']
        last_message = messages[-1]

        attempt_count = getattr(last_message, 'attempt_count', 0)

        if last_message.tool_calls and not getattr(last_message, 'tool_calls_processed', False):
            return "tools"

        if self.is_tool_result_successful(last_message):
            return "summary_agent"

        if attempt_count >= self.max_attempts:
            return END

        return "tools"
