from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from langchain.chains import SQLDatabaseChain
from langchain.chat_models import ChatOpenAI

def generate_sql_from_snowflake(question: str,
                                 user: str,
                                 password: str,
                                 account: str,
                                 database: str,
                                 warehouse: str,
                                 role: str = "ACCOUNTADMIN",
                                 model: str = "gpt-4",
                                 show_sql_only: bool = True):
    """
    Generates (and optionally executes) a SQL query from a natural language question using Snowflake metadata.
    
    Args:
        question (str): Natural language question.
        user (str): Snowflake username.
        password (str): Snowflake password.
        account (str): Snowflake account identifier (e.g., xyz-abc123).
        database (str): Snowflake database to use.
        warehouse (str): Snowflake warehouse to use.
        role (str): Snowflake role (default: ACCOUNTADMIN).
        model (str): OpenAI model to use (e.g., gpt-3.5-turbo or gpt-4).
        show_sql_only (bool): If True, returns only the generated SQL without executing it.
        
    Returns:
        str: Generated SQL query or query result.
    """
    # Step 1: Create SQLAlchemy engine for Snowflake
    connection_url = f"snowflake://{user}:{password}@{account}/{database}?warehouse={warehouse}&role={role}"
    engine = create_engine(connection_url)

    # Step 2: Auto-load metadata
    db = SQLDatabase(engine)

    # Step 3: Create LLM + Chain
    llm = ChatOpenAI(temperature=0, model=model)
    chain = SQLDatabaseChain.from_llm(llm, db, return_intermediate_steps=show_sql_only, verbose=False)

    # Step 4: Ask the question
    result = chain(question)

    # Step 5: Return result or SQL query
    if show_sql_only:
        return result['intermediate_steps'][0]  # The generated SQL
    else:
        return result['result']  # Executed query result
