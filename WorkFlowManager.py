from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt.tool_node import ToolNode
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from typing import Literal

from src.tools import query_snowflake
from src.llm_manager import LLMManager
import src.schema_prompt as sp


class WorkflowManager:
    """LangGraph agent that runs: query → tool → summarization, with retries."""

    def __init__(self):
        self.tools = [query_snowflake]
        self.llm_manager = LLMManager(self.tools)
        self.max_attempts = 3
        self.state_graph = self.create_workflow()

    def create_workflow(self):
        workflow = StateGraph(MessagesState)

        # Add nodes
        workflow.add_node("snowflake_query_agent", self.call_snowflake_model)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_node("summary_agent", self.call_summary_model)

        # Entry point
        workflow.set_entry_point("snowflake_query_agent")

        # Retry-aware conditional transitions
        workflow.add_conditional_edges("snowflake_query_agent", self.retry_or_next("snowflake_query_agent", "tools"))
        workflow.add_conditional_edges("tools", self.retry_or_next("tools", "summary_agent"))
        workflow.add_conditional_edges("summary_agent", self.retry_or_next("summary_agent", END))

        return workflow.compile(checkpointer=MemorySaver())

    def retry_or_next(self, current_node, next_node):
        """Returns a retry logic function that either retries or moves to the next step."""

        def condition(state: MessagesState) -> Literal[str, END]:
            attempt_key = f"{current_node}_attempts"
            attempt_count = state.get(attempt_key, 0)
            last_msg = state['messages'][-1]

            print(f"[{current_node}] Attempt #{attempt_count + 1}, Message: {last_msg}")

            if self.is_success(last_msg):
                return next_node

            if attempt_count >= self.max_attempts:
                state['messages'].append(AIMessage(content=f"Step `{current_node}` failed after {self.max_attempts} attempts. Please revise your prompt."))
                return END

            state[attempt_key] = attempt_count + 1
            return current_node

        return condition

    def is_success(self, message):
        """Determine if a message indicates success."""
        result = getattr(message, "tool_result", None)
        if isinstance(message, AIMessage) and message.content:
            return True
        if result and isinstance(result, str) and "error" not in result.lower():
            return True
        return False

    def call_snowflake_model(self, state: MessagesState):
        user_msg = state['messages'][-1]
        system_prompt = sp.get_schema_prompt()
        response = self.llm_manager.invoke_model([
            SystemMessage(content=system_prompt),
            user_msg
        ])
        return {"messages": [response]}

    def call_summary_model(self, state: MessagesState):
        tool_result = next((msg.tool_result for msg in reversed(state['messages']) if hasattr(msg, "tool_result")), None)
        if not tool_result:
            return {"messages": [AIMessage(content="No tool result found to summarize.")]}

        prompt = f"""You are a summarization agent. Use the tool result below and provide a clear, concise summary:

Tool Result:
{tool_result}

Summary:"""

        response = self.llm_manager.invoke_model([SystemMessage(content=prompt)])
        return {"messages": [response]}

    def run(self, input_message, thread_id):
        initial_state = {
            "messages": [HumanMessage(content=input_message)]
        }
        return self.state_graph.invoke(initial_state, config={"configurable": {"thread_id": thread_id}})
