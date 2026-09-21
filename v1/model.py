from langchain_openai import ChatOpenAI


class Model:
    def __init__(self, config):
        kwargs = dict(model=config.model, api_key=config.api_key or "unused",
                      base_url=config.base_url, timeout=config.timeout, max_retries=1,
                      stream_usage=True)
        if config.reasoning_effort:
            kwargs["reasoning_effort"] = config.reasoning_effort
        self.client = ChatOpenAI(**kwargs)

    def complete(self, messages, tools, emit):
        emit({"type": "model_start"})
        total = None
        try:
            client = self.client.bind_tools(tools) if tools else self.client
            # bind_tools 只传声明，不执行函数；本地执行仍由自己的 Agent 循环负责。
            for chunk in client.stream(messages):
                total = chunk if total is None else total + chunk
                # 展示用 delta 立即发出，协议历史则保存合并后的完整消息。
                if isinstance(chunk.content, str) and chunk.content:
                    emit({"type": "token", "text": chunk.content})
            if total is None:
                raise RuntimeError("Empty model stream")
            if total.usage_metadata:
                emit({"type": "usage", **total.usage_metadata})
            from langchain_core.messages import message_chunk_to_message
            return message_chunk_to_message(total)
        finally:
            emit({"type": "model_end"})
