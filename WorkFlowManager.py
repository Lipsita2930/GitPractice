from langgraph.graph import StateGraph, END, START, MessagesState
from langgraph.prebuilt.tool_node import ToolNode
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
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
        workflow.add_node("summary", self.call_summary_model)

        workflow.set_entry_point("agent")
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", self.should_continue)
        workflow.add_edge("tools", "agent")
        workflow.add_conditional_edges("agent", self.route_after_agent)
        workflow.add_edge("summary", END)

        return workflow.compile(checkpointer=MemorySaver())

    def should_continue(self, state: MessagesState) -> Literal["tools", END]:
        messages = state['messages']
        last_message = messages[-1]

        attempt_count = getattr(last_message, 'attempt_count', 0)

        if last_message.tool_calls and not getattr(last_message, 'tool_calls_processed', False):
            setattr(last_message, 'tool_calls_processed', True)
            attempt_count += 1
            setattr(last_message, 'attempt_count', attempt_count)

            if self.is_tool_result_successful(last_message):
                return "summary"

            if attempt_count >= self.max_attempts:
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

        # Ensure response is an AIMessage
        if not isinstance(response, AIMessage):
            raise Exception("Expected AIMessage from LLMManager, but got something else.")

        return {"messages": [response]}

    def call_summary_model(self, state: MessagesState):
        """Call a model to generate a summary from tool results for visualization."""
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

    def route_after_agent(self, state: MessagesState) -> Literal["tools", "summary", END]:
        messages = state['messages']
        last_message = messages[-1]

        attempt_count = getattr(last_message, 'attempt_count', 0)

        if last_message.tool_calls and not getattr(last_message, 'tool_calls_processed', False):
            return "tools"

        if self.is_tool_result_successful(last_message):
            return "summary"

        if attempt_count >= self.max_attempts:
            return END

        return "tools"
