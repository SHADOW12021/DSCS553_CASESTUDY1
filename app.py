import gradio as gr
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
from pathlib import Path
import os
import openai
import time
from prometheus_client import start_http_server, Counter, Summary

pipe = None
stop_inference = False

# --- Prometheus metrics ---
REQUEST_COUNTER       = Counter('app_requests_total',               'Total number of requests')
SUCCESSFUL_REQUESTS   = Counter('app_successful_requests_total',    'Total number of successful requests')
FAILED_REQUESTS       = Counter('app_failed_requests_total',        'Total number of failed requests')
REQUEST_DURATION      = Summary('app_request_duration_seconds',     'Time spent processing request')

# --- Additional Prometheus metrics ---
ACTIVE_REQUESTS        = Counter('app_active_requests_total',        'Number of currently active requests')
TOKEN_USAGE            = Counter('app_tokens_generated_total',       'Total number of tokens generated across all responses')
REQUEST_ERRORS_BY_TYPE = Counter('app_request_errors_by_type_total', 'Number of failed requests grouped by error type', ['error_type'])
REQUEST_LATENCY        = Summary('app_request_latency_seconds',      'Latency distribution of requests')

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

HF_TOKEN = os.getenv("HF_TOKEN")
if HF_TOKEN is None:
    raise ValueError("HF_TOKEN not found in environment or .env file")

# Fancy styling
fancy_css = """
#main-container {
    background-color: #FFFFFF;
    font-family: 'Arial', sans-serif;
}
.gradio-container {
    max-width: 700px;
    margin: 0 auto;
    padding: 20px;
    background: #FFFFFF;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    border-radius: 10px;
}
.gr-button {
    background-color: #4CAF50;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 10px 20px;
    cursor: pointer;
    transition: background-color 0.3s ease;
}
.gr-button:hover {
    background-color: #274596;
}
.my-slider input {
    accent-color: #4CAF50;
}
.my-chatbox {
    background-color: rgb(37, 150, 190) !important;
    border-radius: 12px;
    padding: 10px;
}
.gr-slider input {
    color: #4CAF50;
}
.gr-chat {
    font-size: 16px;
}
#title {
    text-align: center;
    font-size: 2em;
    margin-bottom: 20px;
    color: #000000;
}
"""

def respond(
    message,
    history: list[dict[str, str]],
    max_tokens,
    temperature,
    top_p,
    use_local_model: bool,
):
    global pipe
    REQUEST_COUNTER.inc()
    ACTIVE_REQUESTS.inc()
    start_t = time.perf_counter()
    
    try:
        system_message = (
            "You are Gandalf from The Lords of the Rings. "
            "You do not have knowledge from modern technologies "
            "and only have information about magic and lord of the rings information. "
            "You love speaking in riddles."
        )
        messages = [{"role": "system", "content": system_message}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})
        response = ""

        if use_local_model:
            print("[MODE] local")
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch

            if pipe is None:
                model_id = "allenai/Olmo-3-7B-Instruct"
                tokenizer = AutoTokenizer.from_pretrained(model_id)
                model = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    device_map="auto",
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
                )
                model.eval()
                pipe = (tokenizer, model)

            tokenizer, model = pipe

            full_prompt = ""
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                full_prompt += f"{role}: {content}\n"
            full_prompt += "Gandalf:"

            inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)

            output_ids = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=temperature,
                top_p=top_p,
            )

            response = tokenizer.decode(output_ids[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            SUCCESSFUL_REQUESTS.inc()
            TOKEN_USAGE.inc(len(output_ids[0]))
            yield response.strip()

        else:
            print("[MODE] api")

            client = openai.OpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=HF_TOKEN,
            )

            clean_messages = []
            for m in messages:
                clean_messages.append({
                    "role": m.get("role", "user"),
                    "content": m.get("content", ""),
                })

            stream = client.chat.completions.create(
                model="Qwen/Qwen3-Coder-30B-A3B-Instruct:nebius",
                messages=clean_messages,
                max_tokens=max_tokens,
                stream=True,
                temperature=temperature,
                top_p=top_p,
            )

            token_count = 0
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    text_piece = chunk.choices[0].delta.content
                    response += text_piece
                    token_count += len(text_piece.split())
                    yield response

            SUCCESSFUL_REQUESTS.inc()
            TOKEN_USAGE.inc(token_count)
                    
    except Exception as e:
        FAILED_REQUESTS.inc()
        REQUEST_ERRORS_BY_TYPE.labels(error_type=type(e).__name__).inc()
        yield f"Error: {e}"
    finally:
        duration = time.perf_counter() - start_t
        REQUEST_DURATION.observe(duration)
        REQUEST_LATENCY.observe(duration)
        ACTIVE_REQUESTS.dec()

chatbot = gr.ChatInterface(
    fn=respond,
    additional_inputs=[
        gr.Slider(minimum=1, maximum=2048, value=512, step=1, label="Max new tokens"),
        gr.Slider(minimum=0, maximum=2, value=0.7, step=0.1, label="Temperature"),
        gr.Slider(minimum=0.1, maximum=1.0, value=0.95, step=0.05, label="Top-p (nucleus sampling)"),
        gr.Checkbox(label="Use Local Model", value=False),
    ],
    type="messages",
)

with gr.Blocks(css=gr.themes.Glass()) as demo:
    with gr.Row():
        gr.Markdown("<h1 style='text-align: center; color: white;'>🔮 Talking With Gandalf 🪄</h1>")
    chatbot.render()

if __name__ == "__main__":
    start_http_server(8000)
    demo.launch(server_name="0.0.0.0", server_port=7860)
