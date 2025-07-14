from langchain_core.messages import AIMessage, ToolCall

def call_snowflake_model(self, state):
    user_msg = state['messages'][-1]
    sql_prompt = sp.get_schema_prompt(user_msg)

    response = self.llm_manager.invoke_model([SystemMessage(content=sql_prompt)])

    if isinstance(response, AIMessage) and "select" in response.content.lower():
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        ToolCall(
                            name="query_snowflake",
                            args='{"query": "' + response.content.replace('"', '\\"') + '"}',
                            id=str(uuid.uuid4())
                        )
                    ]
                )
            ]
        }

    return {"messages": [response]}
