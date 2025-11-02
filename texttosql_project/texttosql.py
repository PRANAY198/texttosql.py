import os
import time
import requests
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
load_dotenv()
st.set_page_config(page_title="AI SQL Assistant", page_icon="🧠", layout="wide")

mode = st.radio("Choose mode:", ["Database SQL Assistant", "General Chatbot"], index=0)

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
if not PERPLEXITY_API_KEY:
    st.error("🚨 Please set your PERPLEXITY_API_KEY as an environment variable.")
    st.stop()

def get_schema_list(engine):
    inspector = inspect(engine)
    schemas = inspector.get_schema_names()
    ignore_schemas = {"information_schema", "pg_catalog", "sys", "dbo"}
    schemas = [s for s in schemas if s not in ignore_schemas]
    return schemas

def get_database_schema(engine, selected_tables=None, selected_schema=None):
    inspector = inspect(engine)
    schema_info = []
    for table_name in inspector.get_table_names(schema=selected_schema):
        if selected_tables and table_name not in selected_tables:
            continue
        columns = inspector.get_columns(table_name, schema=selected_schema)
        foreign_keys = inspector.get_foreign_keys(table_name, schema=selected_schema)
        col_defs = "\n".join([f"- {col['name']} ({col['type']})" for col in columns])
        if foreign_keys:
            fk_text = "\n".join([
                f"  -> references {fk['referred_table']}.{fk['referred_columns'][0]}"
                for fk in foreign_keys if fk.get("referred_table")
            ])
            col_defs += f"\n{fk_text}"
        schema_info.append(f"Table: {table_name}\nColumns:\n{col_defs}\n")
    return "\n\n".join(schema_info)

def nl_to_sql(prompt: str, schema: str) -> str:
    headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert SQL generator. Given the database schema below, generate a correct SQL query. "
                    "If multiple tables are involved, use JOINs based on matching key names (like *_id). "
                    "Return only SQL code — no explanation.\n\n"
                    f"{schema}\n\n"
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    return result["choices"][0]["message"]["content"].strip()

def validate_sql(engine, query):
    try:
        with engine.connect() as conn:
            conn.execute(text(query))
        return True, None
    except SQLAlchemyError as e:
        return False, str(e)

def execute_sql(engine, query):
    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = result.fetchall()
        columns = result.keys()
    return columns, rows
def is_safe_sql(query: str) -> bool:
    ban_words = ['truncate', 'drop', 'delete']
    query_lc = query.lower()
    for ban in ban_words:
        if f'{ban} ' in query_lc or f'{ban}\n' in query_lc:
            return False
    return True
def create_dynamic_engine(db_type, user, password, host, port, db_name):
    if db_type == "PostgreSQL":
        return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}")
    elif db_type == "MySQL":
        return create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}")
    elif db_type == "SQLite":
        return create_engine(f"sqlite:///{db_name}")
    elif db_type == "SQL Server":
        return create_engine(f"mssql+pyodbc://{user}:{password}@{host}:{port}/{db_name}?driver=ODBC+Driver+17+for+SQL+Server")
    elif db_type == "Oracle":
        return create_engine(f"oracle+cx_oracle://{user}:{password}@{host}:{port}/{db_name}")
    elif db_type == "Snowflake":
        return create_engine(f"snowflake://{user}:{password}@{host}/{db_name}")
    elif db_type == "DuckDB":
        return create_engine(f"duckdb:///{db_name}")
    elif db_type == "Redshift":
        return create_engine(f"redshift+psycopg2://{user}:{password}@{host}:{port}/{db_name}")
    elif db_type == "MariaDB":
        return create_engine(f"mariadb+pymysql://{user}:{password}@{host}:{port}/{db_name}")
    else:
        raise ValueError("Unsupported database type")

if mode == "Database SQL Assistant":
    st.markdown("""
        <div style='background:linear-gradient(90deg,#6C63FF,#5346d9);padding:18px 28px 14px 20px;border-radius:12px 12px 32px 12px;margin-bottom:14px;'>
            <span style='font-size:2.1em;vertical-align:middle;'>🧠</span>
            <span style='font-size:2em;color:white;font-weight:bold;font-family:sans-serif;margin-left:16px;'>AI SQL Assistant</span>
        </div>
        """, unsafe_allow_html=True)
    st.caption("Ask questions in natural language and get real SQL with results, powered by Perplexity API.")
    st.sidebar.header("Database Connection")
    db_type = st.sidebar.selectbox("Select Database Type", ["PostgreSQL", "MySQL", "SQLite", "SQL Server", "Oracle", "Snowflake", "DuckDB", "Redshift", "MariaDB"])
    if db_type in ["PostgreSQL", "MySQL", "SQL Server", "Oracle", "Redshift", "MariaDB"]:
        user = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        host = st.sidebar.text_input("Host", "localhost")
        port = st.sidebar.text_input("Port", "5432" if db_type == "PostgreSQL" else "3306")
        db_name = st.sidebar.text_input("Database Name")
    elif db_type == "SQLite":
        db_name = st.sidebar.text_input("SQLite File Path")
        user = password = host = port = ""
    elif db_type == "DuckDB":
        db_name = st.sidebar.text_input("DuckDB File Path")
        user = password = host = port = ""
    elif db_type == "Snowflake":
        user = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        account = st.sidebar.text_input("Account Name")
        warehouse = st.sidebar.text_input("Warehouse Name")
        db_name = st.sidebar.text_input("Database Name")
        host = port = ""
    if st.sidebar.button("Connect"):
        try:
            engine = create_dynamic_engine(db_type, user, password, host, port, db_name)
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            schemas = get_schema_list(engine)
            st.session_state["engine"] = engine
            st.session_state["tables"] = tables
            st.session_state["schemas"] = schemas
            st.success(f"✅ Connected! Found {len(tables)} tables and {len(schemas)} schemas.")
        except Exception as e:
            st.error(f"❌ Connection failed: {e}")
    if "engine" in st.session_state:
        engine = st.session_state["engine"]
        all_schemas = st.session_state.get("schemas", [])
        selected_schema = st.selectbox("🏷️ Select schema", all_schemas) if all_schemas else None
        inspector = inspect(engine)
        tables_in_schema = inspector.get_table_names(schema=selected_schema)
        selected_tables = st.multiselect("📊 Select tables for schema context", tables_in_schema, default=tables_in_schema)
        if selected_tables:
            schema_text = get_database_schema(engine, selected_tables, selected_schema)
            with st.expander("🔍 Database Schema", expanded=False):
                st.markdown("<div style='background:#000;border-radius:10px;padding:14px'><pre style='font-size:1.1em; color: #fff;'>"+ schema_text +"</pre></div>", unsafe_allow_html=True)
            user_prompt = st.text_area("💬 Ask your question", placeholder="e.g., Show top 10 customers by total purchase amount in 2024", height=100)
            if st.button("🚀 Generate & Run SQL") and user_prompt.strip():
                with st.spinner("Analyzing and generating SQL..."):
                    sql_query = nl_to_sql(user_prompt, schema_text)
                st.subheader("🧾 Generated SQL (line by line)")
                code_placeholder = st.empty()
                typed_code = ""
                for line in sql_query.split('\n'):
                    typed_code += line + '\n'
                    code_placeholder.code(typed_code, language="sql")
                    time.sleep(0.13)
            if st.button("🚀 Generate & Run SQL") and user_prompt.strip():
                if not is_safe_sql(sql_query):
                    st.warning("⛔ Query blocked: Dangerous operations (DROP, DELETE, TRUNCATE) are not allowed.")
                else:
                    with st.spinner("Validating query..."):
                        is_valid, error_msg = validate_sql(engine, sql_query)
                        time.sleep(5)
                if is_valid:
                    st.subheader("✅ SQL Query is valid")
                    with st.spinner("Running query..."):
                        try:
                            cols, rows = execute_sql(engine, sql_query)
                            st.success("✅ Query executed successfully!")
                            if rows:
                                df = pd.DataFrame([dict(zip(cols, row)) for row in rows])
                                st.dataframe(df.style.set_properties(**{'background-color': '#F5F4FB', 'color': '#22223B', 'border-radius': '10px', 'font-size': '1.1em'}))
                            else:
                                st.info("No results found.")
                        except Exception:
                            st.error("Sorry for the inconvenience. Please give more information to get query with results.")
                else:
                    correction_prompt = (f"The following SQL query failed:\n{sql_query}\nError: {error_msg}"
                        f"\nPlease fix the query based on the schema below:\n{schema_text}")
                    corrected_sql = nl_to_sql(correction_prompt, schema_text)
                    st.subheader("✅ Corrected SQL Query")
                    code_placeholder = st.empty()
                    typed_code = ""
                    for line in corrected_sql.split('\n'):
                        typed_code += line + '\n'
                        code_placeholder.code(typed_code, language="sql")
                        time.sleep(0.13)
                    is_corrected_valid, corrected_error = validate_sql(engine, corrected_sql)
                    if is_corrected_valid:
                        with st.spinner("Running query..."):
                            try:
                                cols, rows = execute_sql(engine, corrected_sql)
                                st.success("✅ Query executed successfully!")
                                if rows:
                                    df = pd.DataFrame([dict(zip(cols, row)) for row in rows])
                                    st.dataframe(df.style.set_properties(**{'background-color': '#F5F4FB', 'color': '#22223B', 'border-radius': '10px', 'font-size': '1.1em'}))
                                else:
                                    st.info("No results found.")
                            except Exception:
                                st.error("Sorry for the inconvenience. Please give more information to get query with results.")
                    else:
                        st.error("Sorry for the inconvenience. Please give more information to get query with results.")
else:
    st.title("💬 Perplexity-Style Chatbot")
    prompt = st.text_area("Ask anything (just chat)", height=120)
    if st.button("Send"):
        with st.spinner("Thinking..."):
            headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"}
            data = {"model": "sonar-pro", "messages": [{"role": "user", "content": prompt}]}
            try:
                response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                answer = result["choices"][0]["message"]["content"].strip()
                st.markdown(answer)
            except Exception:
                st.error("Sorry, something went wrong with the chatbot response.")
