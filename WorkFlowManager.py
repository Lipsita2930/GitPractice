from langgraph.graph import StateGraph, END, START, MessagesState
from langgraph.prebuilt.tool_node import ToolNode
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from typing import Literal

from src.tools import query_snowflake
from src.llm_manager import LLMManager
import src.schema_prompt as sp

class WorkflowManager:
    """Manager for creating and running the LangGraph agent workflow."""

    def __init__(self):
        self.tools = [query_snowflake]
        self.llm_manager = LLMManager(self.tools)
        self.state_graph = self.create_workflow()
        self.max_attempts = 3

    def create_workflow(self):
        workflow = StateGraph(MessagesState)

        workflow.add_node("agent", self.call_snowflake_model)
        workflow.add_node("tools", ToolNode(self.tools))

        workflow.set_entry_point("agent")
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", self.should_continue)
        workflow.add_edge("tools", "agent")

        return workflow.compile(checkpointer=MemorySaver())

    def should_continue(self, state: MessagesState) -> Literal["tools", END]:
        messages = state['messages']
        last_message = messages[-1]

        attempt_count = getattr(last_message, 'attempt_count', 0)

        if last_message.tool_calls and not getattr(last_message, 'tool_calls_processed', False):
            setattr(last_message, 'tool_calls_processed', True)
            attempt_count += 1
            setattr(last_message, 'attempt_count', attempt_count)

            if self.is_tool_result_successful(last_message) or attempt_count >= self.max_attempts:
                return END

            return "tools"

        return END

    def is_tool_result_successful(self, message):
        result = getattr(message, "tool_result", None)
        if result and isinstance(result, str) and "error" not in result.lower():
            return True
        return False

    def call_snowflake_model(self, state: MessagesState):
        user_message = state['messages'][-1]
        system_prompt = sp.get_schema_prompt()

        formatted_messages = [
            SystemMessage(content=system_prompt),
            user_message
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
