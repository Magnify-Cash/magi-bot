from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from pydantic import Field, BaseModel
from pydantic.v1 import SecretStr
from config import config
import structlog
import httpx
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("."))
template = env.get_template("prompt.md")
with open("defillama.yaml", "r") as f:
    defillama_openapi_yaml = f.read()
prompt = template.render(defillama_openapi_yaml=defillama_openapi_yaml)

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=3,
    api_key=SecretStr(config.openai_api_key),
)
log = structlog.stdlib.get_logger()


class CallDefiLlamaAPI(BaseModel):
    """Use this tool to get crypto market data from the DeFi Llama API."""

    url: str = Field(
        description="The full API url, including base url and all arguments. Make sure to limit the number of results to 10 at max if you can, using limit or other parameters. Make sure to include the base url in the url."
    )


async def call_defi_llama_api(url: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text


async def run_agent(message: str) -> str:
    llm_with_tools = llm.bind_tools([CallDefiLlamaAPI])
    messages: list[BaseMessage] = [
        SystemMessage(content=prompt),
        HumanMessage(content=message),
    ]

    while len(messages) < 5:
        response: AIMessage = await llm_with_tools.ainvoke(messages)  # pyright:ignore[reportAssignmentType]
        log.info("Intermediate response", response=response)
        messages.append(response)

        if response.tool_calls:
            tool_call = response.tool_calls[0]
            if not tool_call["id"]:
                log.error("No tool call id", response=response)
                return "No tool call id"
            url = CallDefiLlamaAPI(**tool_call["args"]).url
            log.info("Calling DeFi Llama API", url=url)

            api_response = await call_defi_llama_api(url)
            api_response = api_response[:30000]
            messages.append(
                ToolMessage(content=api_response, tool_call_id=tool_call["id"])
            )
        else:
            assert isinstance(response.content, str)
            return response.content

    return "No response from agent"
