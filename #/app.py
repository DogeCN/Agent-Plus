import json
import logging
import queue
import threading
import time
from curl_cffi import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from constants import HTTPConstants
from src.deepseek import *
from constants import (
    DeepSeekConstants,
    ClaudeConstants,
    HTTPConstants,
    SystemConstants,
)
from messages import messages_prepare

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


init_account_queue()
DEEPSEEK_HOST = DeepSeekConstants.HOST
DEEPSEEK_LOGIN_URL = DeepSeekConstants.LOGIN_URL
DEEPSEEK_CREATE_SESSION_URL = DeepSeekConstants.CREATE_SESSION_URL
DEEPSEEK_CREATE_POW_URL = DeepSeekConstants.CREATE_POW_URL
DEEPSEEK_COMPLETION_URL = DeepSeekConstants.COMPLETION_URL
DEEPSEEK_STOP_STREAM_URL = DeepSeekConstants.STOP_STREAM_URL
DEEPSEEK_DELETE_SESSION_URL = DeepSeekConstants.DELETE_SESSION_URL
CLAUDE_DEFAULT_MODEL = ClaudeConstants.DEFAULT_MODEL
WASM_PATH = SystemConstants.WASM_PATH


def login_deepseek_via_account(account):
    """使用 account 中的 email 或 mobile 登录 DeepSeek，
    成功后将返回的 token 写入 account 并保存至配置文件，返回新 token。
    """
    email = account.get("email", "").strip()
    mobile = account.get("mobile", "").strip()
    password = account.get("password", "").strip()
    if not password or (not email and not mobile):
        raise HTTPException(
            status_code=400,
            detail="账号缺少必要的登录信息（必须提供 email 或 mobile 以及 password）",
        )
    if email:
        payload = {
            "email": email,
            "password": password,
            "device_id": "deepseek_to_api",
            "os": "android",
        }
    else:
        payload = {
            "mobile": mobile,
            "area_code": None,
            "password": password,
            "device_id": "deepseek_to_api",
            "os": "android",
        }
    try:
        resp = requests.post(
            DEEPSEEK_LOGIN_URL,
            headers=HTTPConstants.BASE_HEADERS,
            json=payload,
            impersonate="safari15_3",
        )
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"[login_deepseek_via_account] 登录请求异常: {e}")
        raise HTTPException(status_code=500, detail="Account login failed: 请求异常")
    try:
        logger.warning(f"[login_deepseek_via_account] {resp.text}")
        data = resp.json()
    except Exception as e:
        logger.error(f"[login_deepseek_via_account] JSON解析失败: {e}")
        raise HTTPException(
            status_code=500, detail="Account login failed: invalid JSON response"
        )

    if (
        data.get("data") is None
        or data["data"].get("biz_data") is None
        or data["data"]["biz_data"].get("user") is None
    ):
        logger.error(f"[login_deepseek_via_account] 登录响应格式错误: {data}")
        raise HTTPException(
            status_code=500, detail="Account login failed: invalid response format"
        )
    new_token = data["data"]["biz_data"]["user"].get("token")
    if not new_token:
        logger.error(f"[login_deepseek_via_account] 登录响应中缺少 token: {data}")
        raise HTTPException(
            status_code=500, detail="Account login failed: missing token"
        )
    account["token"] = new_token
    save_config(CONFIG)
    return new_token


def determine_mode_and_token(request: Request):
    """
    根据请求头 Authorization 判断使用哪种模式：
    - 如果 Bearer token 出现在 CONFIG["keys"] 中，则为配置模式，从 CONFIG["accounts"] 中随机选择一个账号（排除已尝试账号），
      检查该账号是否已有 token，否则调用登录接口获取；
    - 否则，直接使用请求中的 Bearer 值作为 DeepSeek token。
    结果存入 request.state.deepseek_token；配置模式下同时存入 request.state.account 与 request.state.tried_accounts。
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Unauthorized: missing Bearer token."
        )
    caller_key = auth_header.replace("Bearer ", "", 1).strip()
    config_keys = CONFIG.get("keys", [])
    if caller_key in config_keys:
        request.state.use_config_token = True
        request.state.tried_accounts = []
        selected_account = choose_new_account()
        if not selected_account:
            raise HTTPException(
                status_code=429,
                detail="No accounts configured or all accounts are busy.",
            )
        if not selected_account.get("token", "").strip():
            try:
                login_deepseek_via_account(selected_account)
            except Exception as e:
                logger.error(
                    f"[determine_mode_and_token] 账号 {get_account_identifier(selected_account)} 登录失败：{e}"
                )
                raise HTTPException(status_code=500, detail="Account login failed.")
        request.state.deepseek_token = selected_account.get("token")
        request.state.account = selected_account
    else:
        request.state.use_config_token = False
        request.state.deepseek_token = caller_key


def get_auth_headers(request: Request):
    """返回 DeepSeek 请求所需的公共请求头"""
    return {
        **HTTPConstants.BASE_HEADERS,
        "authorization": f"Bearer {request.state.deepseek_token}",
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:

        try:
            determine_mode_and_token(request)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code, content={"error": exc.detail}
            )
        except Exception as exc:
            logger.error(f"[chat_completions] determine_mode_and_token 异常: {exc}")
            return JSONResponse(
                status_code=500, content={"error": "Account login failed."}
            )
        req_data = await request.json()
        model = req_data.get("model")
        messages = req_data.get("messages", [])
        if not model or not messages:
            raise HTTPException(
                status_code=400, detail="Request must include 'model' and 'messages'."
            )

        model_lower = model.lower()
        if model_lower in ["deepseek-v3", "deepseek-chat"]:
            thinking_enabled = False
            search_enabled = False
        elif model_lower in ["deepseek-r1", "deepseek-reasoner"]:
            thinking_enabled = True
            search_enabled = False
        elif model_lower in ["deepseek-v3-search", "deepseek-chat-search"]:
            thinking_enabled = False
            search_enabled = True
        elif model_lower in ["deepseek-r1-search", "deepseek-reasoner-search"]:
            thinking_enabled = True
            search_enabled = True
        else:
            raise HTTPException(
                status_code=503, detail=f"Model '{model}' is not available."
            )

        tools_requested = req_data.get("tools") or []
        has_tools = len(tools_requested) > 0

        if has_tools:
            tool_schemas = []
            for tool in tools_requested:
                func = tool.get("function", {})
                tool_name = func.get("name", "unknown")
                tool_desc = func.get("description", "No description available")
                params = func.get("parameters", {})
                tool_info = f"Tool: {tool_name}\nDescription: {tool_desc}"
                if "properties" in params:
                    props = []
                    required = params.get("required", [])
                    for prop_name, prop_info in params["properties"].items():
                        prop_type = prop_info.get("type", "string")
                        prop_desc = prop_info.get("description", "")
                        is_req = " (required)" if prop_name in required else ""
                        props.append(
                            f"  - {prop_name}: {prop_type}{is_req} - {prop_desc}"
                        )
                    if props:
                        tool_info += f"\nParameters:\n{chr(10).join(props)}"
                tool_schemas.append(tool_info)
            tool_system_prompt = f"""You have access to the following tools:
{chr(10).join(tool_schemas)}
When you need to use tools, you can call multiple tools in a single response. Use this format:
{{"tool_calls": [{{"id": "call_xxx", "type": "function", "function": {{"name": "tool_name", "arguments": {{"param": "value"}}}}}}]}}
After calling tools, you will receive the results and move on."""
            system_found = False
            for msg in messages:
                if msg.get("role") == "system":
                    msg["content"] = msg["content"] + "\n\n" + tool_system_prompt
                    system_found = True
                    break
            if not system_found:
                messages.insert(0, {"role": "system", "content": tool_system_prompt})

        final_prompt = messages_prepare(messages)
        session_id = create_session(request)
        if not session_id:
            raise HTTPException(status_code=401, detail="invalid token.")
        pow_resp = get_pow_response(request)
        if not pow_resp:
            raise HTTPException(
                status_code=401,
                detail="Failed to get PoW (invalid token or unknown error).",
            )
        headers = {**get_auth_headers(request), "x-ds-pow-response": pow_resp}
        payload = {
            "chat_session_id": session_id,
            "parent_message_id": None,
            "prompt": final_prompt,
            "ref_file_ids": [],
            "thinking_enabled": thinking_enabled,
            "search_enabled": search_enabled,
        }
        deepseek_resp = call_completion_endpoint(payload, headers, max_attempts=3)
        if not deepseek_resp:
            raise HTTPException(status_code=500, detail="Failed to get completion.")
        created_time = int(time.time())
        completion_id = f"{session_id}"

        if bool(req_data.get("stream", False)):
            if deepseek_resp.status_code != 200:
                deepseek_resp.close()
                return JSONResponse(
                    content=deepseek_resp.content, status_code=deepseek_resp.status_code
                )

            def sse_stream():
                client_disconnected = False
                stream_completed = False
                try:
                    final_text = ""
                    final_thinking = ""
                    first_chunk_sent = False
                    result_queue = queue.Queue()
                    last_send_time = time.time()
                    citation_map = {}

                    def delete_deepseek_session():
                        """响应结束后删除 DeepSeek 会话"""
                        try:
                            headers = get_auth_headers(request)
                            payload = {"chat_session_id": session_id}
                            resp = requests.post(
                                DEEPSEEK_DELETE_SESSION_URL,
                                headers=headers,
                                json=payload,
                                impersonate="safari15_3",
                                timeout=3,
                            )
                            if resp.status_code == 200:
                                logger.info(
                                    f"[sse_stream] 响应结束，已删除会话 session={session_id}"
                                )
                            else:
                                logger.warning(
                                    f"[sse_stream] 删除会话失败: {resp.status_code}"
                                )
                        except Exception as e:
                            logger.warning(
                                f"[sse_stream] 调用 delete_session 失败: {e}"
                            )

                    def process_data():
                        ptype = "text"
                        try:
                            for raw_line in deepseek_resp.iter_lines():
                                try:
                                    line = raw_line.decode("utf-8")
                                except Exception as e:
                                    logger.warning(f"[sse_stream] 解码失败: {e}")

                                    error_type = (
                                        "thinking" if ptype == "thinking" else "text"
                                    )
                                    busy_content_str = f'{{"choices":[{{"index":0,"delta":{{"content":"解码失败，请稍候再试","type":"{error_type}"}}}}],"model":"","chunk_token_usage":1,"created":0,"message_id":-1,"parent_id":-1}}'
                                    try:
                                        busy_content = json.loads(busy_content_str)
                                        result_queue.put(busy_content)
                                    except json.JSONDecodeError:

                                        result_queue.put(
                                            {
                                                "choices": [
                                                    {
                                                        "index": 0,
                                                        "delta": {
                                                            "content": "解码失败",
                                                            "type": "text",
                                                        },
                                                    }
                                                ]
                                            }
                                        )
                                    result_queue.put(None)
                                    break
                                if not line:
                                    continue
                                if line.startswith("data:"):
                                    data_str = line[5:].strip()
                                    if data_str == "[DONE]":
                                        result_queue.put(None)
                                        break
                                    try:
                                        chunk = json.loads(data_str)
                                        if "response_message_id" in chunk:
                                            response_message_id = chunk[
                                                "response_message_id"
                                            ]
                                        if "v" in chunk:
                                            v_value = chunk["v"]

                                            content = ""
                                            if (
                                                "p" in chunk
                                                and chunk.get("p") == "response/status"
                                            ):
                                                if v_value == "FINISHED":
                                                    result_queue.put(None)
                                                    break
                                                continue
                                            if (
                                                "p" in chunk
                                                and chunk.get("p")
                                                == "response/search_status"
                                            ):
                                                continue
                                            if (
                                                "p" in chunk
                                                and chunk.get("p")
                                                == "response/thinking_content"
                                            ):
                                                ptype = "thinking"
                                            elif (
                                                "p" in chunk
                                                and chunk.get("p") == "response/content"
                                            ):
                                                ptype = "text"

                                            if isinstance(v_value, str):
                                                content = v_value

                                            elif isinstance(v_value, list):
                                                for item in v_value:
                                                    if (
                                                        item.get("p") == "status"
                                                        and item.get("v") == "FINISHED"
                                                    ):

                                                        result_queue.put(
                                                            {
                                                                "choices": [
                                                                    {
                                                                        "index": 0,
                                                                        "finish_reason": "stop",
                                                                    }
                                                                ]
                                                            }
                                                        )
                                                        result_queue.put(None)
                                                        return
                                                continue

                                            unified_chunk = {
                                                "choices": [
                                                    {
                                                        "index": 0,
                                                        "delta": {
                                                            "content": content,
                                                            "type": ptype,
                                                        },
                                                    }
                                                ],
                                                "model": "",
                                                "chunk_token_usage": len(content) // 4,
                                                "created": 0,
                                                "message_id": -1,
                                                "parent_id": -1,
                                            }
                                            result_queue.put(unified_chunk)
                                    except Exception as e:
                                        logger.warning(
                                            f"[sse_stream] 无法解析: {data_str}, 错误: {e}"
                                        )

                                        error_type = (
                                            "thinking"
                                            if ptype == "thinking"
                                            else "text"
                                        )
                                        busy_content_str = f'{{"choices":[{{"index":0,"delta":{{"content":"解析失败，请稍候再试","type":"{error_type}"}}}}],"model":"","chunk_token_usage":1,"created":0,"message_id":-1,"parent_id":-1}}'
                                        try:
                                            busy_content = json.loads(busy_content_str)
                                            result_queue.put(busy_content)
                                        except json.JSONDecodeError:

                                            result_queue.put(
                                                {
                                                    "choices": [
                                                        {
                                                            "index": 0,
                                                            "delta": {
                                                                "content": "解析失败",
                                                                "type": "text",
                                                            },
                                                        }
                                                    ]
                                                }
                                            )
                                        result_queue.put(None)
                                        break
                        except Exception as e:
                            logger.warning(f"[sse_stream] 错误: {e}")

                            try:
                                error_response = {
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {
                                                "content": "服务器错误，请稍候再试",
                                                "type": "text",
                                            },
                                        }
                                    ]
                                }
                                result_queue.put(error_response)
                            except Exception:

                                pass
                            result_queue.put(None)

                        finally:
                            deepseek_resp.close()

                    process_thread = threading.Thread(target=process_data)
                    process_thread.start()
                    try:
                        while True:
                            current_time = time.time()
                            if (
                                current_time - last_send_time
                                >= HTTPConstants.KEEP_ALIVE_TIMEOUT
                            ):
                                yield ": keep-alive\n\n"
                                last_send_time = current_time
                                continue
                            try:
                                chunk = result_queue.get(timeout=0.05)
                            except queue.Empty:
                                continue
                            if chunk is None:

                                prompt_tokens = len(final_prompt) // 4
                                thinking_tokens = len(final_thinking) // 4
                                completion_tokens = len(final_text) // 4
                                usage = {
                                    "prompt_tokens": prompt_tokens,
                                    "completion_tokens": thinking_tokens
                                    + completion_tokens,
                                    "total_tokens": prompt_tokens
                                    + thinking_tokens
                                    + completion_tokens,
                                    "completion_tokens_details": {
                                        "reasoning_tokens": thinking_tokens
                                    },
                                }
                                finish_chunk = {
                                    "id": completion_id,
                                    "object": "chat.completion.chunk",
                                    "created": created_time,
                                    "model": model,
                                    "choices": [
                                        {
                                            "delta": {},
                                            "index": 0,
                                            "finish_reason": "stop",
                                        }
                                    ],
                                    "usage": usage,
                                }
                                yield f"data: {json.dumps(finish_chunk, ensure_ascii=False)}\n\n"
                                yield "data: [DONE]\n\n"
                                last_send_time = current_time
                                break
                            new_choices = []
                            for choice in chunk.get("choices", []):
                                delta = choice.get("delta", {})
                                ctype = delta.get("type")
                                ctext = delta.get("content", "")
                                if choice.get("finish_reason") == "backend_busy":
                                    ctext = "服务器繁忙，请稍候再试"
                                if search_enabled and ctext.startswith("[citation:"):
                                    ctext = ""
                                if ctype == "thinking":
                                    if thinking_enabled:
                                        final_thinking += ctext
                                elif ctype == "text":
                                    final_text += ctext
                                delta_obj = {}
                                if not first_chunk_sent:
                                    delta_obj["role"] = "assistant"
                                    first_chunk_sent = True
                                if ctype == "thinking":
                                    if thinking_enabled:
                                        delta_obj["reasoning_content"] = ctext
                                elif ctype == "text":
                                    delta_obj["content"] = ctext
                                if delta_obj:
                                    new_choices.append(
                                        {
                                            "delta": delta_obj,
                                            "index": choice.get("index", 0),
                                        }
                                    )
                            if new_choices:
                                out_chunk = {
                                    "id": completion_id,
                                    "object": "chat.completion.chunk",
                                    "created": created_time,
                                    "model": model,
                                    "choices": new_choices,
                                }
                                yield f"data: {json.dumps(out_chunk, ensure_ascii=False)}\n\n"
                                last_send_time = current_time
                    except GeneratorExit:

                        logger.info(f"[sse_stream] 客户端断开连接 session={session_id}")
                        client_disconnected = True
                        raise
                except Exception as e:
                    logger.error(f"[sse_stream] 异常: {e}")
                    client_disconnected = True
                finally:

                    delete_deepseek_session()
                    if getattr(request.state, "use_config_token", False) and hasattr(
                        request.state, "account"
                    ):
                        release_account(request.state.account)

            return StreamingResponse(
                sse_stream(),
                media_type="text/event-stream",
                headers={"Content-Type": "text/event-stream"},
            )
        else:

            think_list = []
            text_list = []
            result = None
            citation_map = {}
            data_queue = queue.Queue()

            def delete_deepseek_session():
                """响应结束后删除 DeepSeek 会话"""
                try:
                    headers = get_auth_headers(request)
                    payload = {"chat_session_id": session_id}
                    resp = requests.post(
                        DEEPSEEK_DELETE_SESSION_URL,
                        headers=headers,
                        json=payload,
                        impersonate="safari15_3",
                        timeout=3,
                    )
                    if resp.status_code == 200:
                        logger.info(
                            f"[chat_completions] 响应结束，已删除会话 session={session_id}"
                        )
                    else:
                        logger.warning(
                            f"[chat_completions] 删除会话失败: {resp.status_code}"
                        )
                except Exception as e:
                    logger.warning(f"[chat_completions] 调用 delete_session 失败: {e}")

            def collect_data():
                nonlocal result
                ptype = "text"
                try:
                    for raw_line in deepseek_resp.iter_lines():
                        try:
                            line = raw_line.decode("utf-8")
                        except Exception as e:
                            logger.warning(f"[chat_completions] 解码失败: {e}")

                            if ptype == "thinking":
                                think_list.append("解码失败，请稍候再试")
                            else:
                                text_list.append("解码失败，请稍候再试")
                            data_queue.put(None)
                            break
                        if not line:
                            continue
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if data_str == "[DONE]":
                                data_queue.put(None)
                                break
                            try:
                                chunk = json.loads(data_str)

                                if "v" in chunk:
                                    v_value = chunk["v"]
                                    if (
                                        "p" in chunk
                                        and chunk.get("p") == "response/status"
                                    ):
                                        if v_value == "FINISHED":
                                            data_queue.put(None)
                                            break
                                        continue
                                    if (
                                        "p" in chunk
                                        and chunk.get("p") == "response/search_status"
                                    ):
                                        continue
                                    if (
                                        "p" in chunk
                                        and chunk.get("p")
                                        == "response/thinking_content"
                                    ):
                                        ptype = "thinking"
                                    elif (
                                        "p" in chunk
                                        and chunk.get("p") == "response/content"
                                    ):
                                        ptype = "text"

                                    if isinstance(v_value, str):
                                        if search_enabled and v_value.startswith(
                                            "[citation:"
                                        ):
                                            continue
                                        if ptype == "thinking":
                                            think_list.append(v_value)
                                        else:
                                            text_list.append(v_value)

                                    elif isinstance(v_value, list):
                                        for item in v_value:
                                            if (
                                                item.get("p") == "status"
                                                and item.get("v") == "FINISHED"
                                            ):

                                                final_reasoning = "".join(think_list)
                                                final_content = "".join(text_list)
                                                prompt_tokens = len(final_prompt) // 4
                                                reasoning_tokens = (
                                                    len(final_reasoning) // 4
                                                )
                                                completion_tokens = (
                                                    len(final_content) // 4
                                                )

                                                message_obj = {
                                                    "role": "assistant",
                                                    "content": final_content,
                                                    "reasoning_content": final_reasoning,
                                                }
                                                result = {
                                                    "id": completion_id,
                                                    "object": "chat.completion",
                                                    "created": created_time,
                                                    "model": model,
                                                    "choices": [
                                                        {
                                                            "index": 0,
                                                            "message": message_obj,
                                                            "finish_reason": "stop",
                                                        }
                                                    ],
                                                    "usage": {
                                                        "prompt_tokens": prompt_tokens,
                                                        "completion_tokens": reasoning_tokens
                                                        + completion_tokens,
                                                        "total_tokens": prompt_tokens
                                                        + reasoning_tokens
                                                        + completion_tokens,
                                                        "completion_tokens_details": {
                                                            "reasoning_tokens": reasoning_tokens
                                                        },
                                                    },
                                                }
                                                data_queue.put("DONE")
                                                return
                            except Exception as e:
                                logger.warning(
                                    f"[collect_data] 无法解析: {data_str}, 错误: {e}"
                                )

                                if ptype == "thinking":
                                    think_list.append("解析失败，请稍候再试")
                                else:
                                    text_list.append("解析失败，请稍候再试")
                                data_queue.put(None)
                                break
                except Exception as e:
                    logger.warning(f"[collect_data] 错误: {e}")

                    if ptype == "thinking":
                        think_list.append("处理失败，请稍候再试")
                    else:
                        text_list.append("处理失败，请稍候再试")
                    data_queue.put(None)
                finally:
                    deepseek_resp.close()
                    if result is None:

                        final_content = "".join(text_list)
                        final_reasoning = "".join(think_list)
                        prompt_tokens = len(final_prompt) // 4
                        reasoning_tokens = len(final_reasoning) // 4
                        completion_tokens = len(final_content) // 4

                        message_obj = {
                            "role": "assistant",
                            "content": final_content,
                            "reasoning_content": final_reasoning,
                        }
                        result = {
                            "id": completion_id,
                            "object": "chat.completion",
                            "created": created_time,
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "message": message_obj,
                                    "finish_reason": "stop",
                                }
                            ],
                            "usage": {
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": reasoning_tokens
                                + completion_tokens,
                                "total_tokens": prompt_tokens
                                + reasoning_tokens
                                + completion_tokens,
                            },
                        }
                    data_queue.put("DONE")

            collect_thread = threading.Thread(target=collect_data)
            collect_thread.start()

            def generate():
                last_send_time = time.time()
                try:
                    while True:
                        current_time = time.time()
                        if (
                            current_time - last_send_time
                            >= HTTPConstants.KEEP_ALIVE_TIMEOUT
                        ):
                            yield ""
                            last_send_time = current_time
                        if not collect_thread.is_alive() and result is not None:
                            yield json.dumps(result)
                            break
                        time.sleep(0.1)
                finally:

                    delete_deepseek_session()

            return StreamingResponse(generate(), media_type="application/json")
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
    except Exception as exc:
        logger.error(f"[chat_completions] 未知异常: {exc}")
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})
    finally:
        if getattr(request.state, "use_config_token", False) and hasattr(
            request.state, "account"
        ):
            release_account(request.state.account)


@app.post("/v1/chat/stop_stream")
async def stop_stream(request: Request):
    """
    停止正在进行的流式对话
    请求体示例:
    {
        "chat_session_id": "85437c2a-acf8-436a-a2ba-a4a110907fe7",
        "message_id": 2
    }
    """
    try:

        determine_mode_and_token(request)

        body = await request.json()
        chat_session_id = body.get("chat_session_id")
        message_id = body.get("message_id")
        if not chat_session_id:
            raise HTTPException(status_code=400, detail="缺少 chat_session_id 参数")

        headers = get_auth_headers(request)

        payload = {"chat_session_id": chat_session_id, "message_id": message_id}

        resp = requests.post(
            DEEPSEEK_STOP_STREAM_URL,
            headers=headers,
            json=payload,
            impersonate="safari15_3",
        )
        if resp.status_code == 200:
            logger.info(f"[stop_stream] 成功停止会话 {chat_session_id}")
            return JSONResponse(content={"success": True, "message": "已停止流式响应"})
        else:
            logger.warning(f"[stop_stream] 停止失败，状态码: {resp.status_code}")
            return JSONResponse(
                status_code=resp.status_code,
                content={"success": False, "message": f"停止失败: {resp.text}"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[stop_stream] 异常: {e}")
        raise HTTPException(status_code=500, detail=f"停止流式响应失败: {str(e)}")


@app.get("/")
def index(_: Request):
    return JSONResponse(content={"message": "Server is running."})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5001)
