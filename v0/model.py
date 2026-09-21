"""Minimal Chat Completions SSE adapter, without an agent framework."""
import json
import urllib.request


class Model:
    def __init__(self, config):
        self.config = config

    def complete(self, messages, tools, emit):
        cfg = self.config
        body = {"model": cfg.model, "messages": messages, "tools": tools, "stream": True,
                "stream_options": {"include_usage": True}}
        if cfg.reasoning_effort:
            body["reasoning_effort"] = cfg.reasoning_effort
        request = urllib.request.Request(
            cfg.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {cfg.api_key}"})
        content, calls, finished = [], {}, False
        emit({"type": "model_start"})
        try:
            with urllib.request.urlopen(request, timeout=cfg.timeout) as response:
                for raw in response:
                    line = raw.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        finished = True
                        break
                    chunk = json.loads(data)
                    if chunk.get("error"):
                        raise RuntimeError(str(chunk["error"]))
                    if chunk.get("usage"):
                        emit({"type": "usage", **chunk["usage"]})
                    for choice in chunk.get("choices", []):
                        if choice.get("index", 0) != 0:
                            continue
                        delta = choice.get("delta", {})
                        if delta.get("content"):
                            content.append(delta["content"])
                            emit({"type": "token", "text": delta["content"]})
                        for part in delta.get("tool_calls", []):
                            # 参数是分片 JSON 字符串；按调用 index 拼完后，外层循环才解码并执行。
                            call = calls.setdefault(part["index"], {"id": "", "type": "function",
                                "function": {"name": "", "arguments": ""}})
                            if part.get("id"):
                                call["id"] += part["id"]
                            for key in ("name", "arguments"):
                                call["function"][key] += part.get("function", {}).get(key, "")
            if not finished:
                # 不能把网络截断时的半个工具请求当成合法完整响应。
                raise RuntimeError("Incomplete SSE response (missing [DONE])")
        finally:
            emit({"type": "model_end"})
        result = {"role": "assistant", "content": "".join(content)}
        if calls:
            result["tool_calls"] = [calls[index] for index in sorted(calls)]
        return result
