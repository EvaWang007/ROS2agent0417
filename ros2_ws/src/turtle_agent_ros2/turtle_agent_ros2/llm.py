import os
import dotenv
from langchain_openai import ChatOpenAI


def get_env_variable(var_name: str) -> str:
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"Environment variable {var_name} is not set.")
    return value


def get_llm(streaming: bool = False):
    dotenv.load_dotenv(dotenv.find_dotenv())

    # DeepSeek OpenAI-compatible config
    return ChatOpenAI(
        api_key=get_env_variable("sk-b5d302d9143245b9af8af66df5fc26cb"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        streaming=streaming,
        temperature=0,
    )
