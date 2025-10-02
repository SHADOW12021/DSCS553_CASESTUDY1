import gradio as gr
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
import os
import openai

pipe = None
stop_inference = False

load_dotenv(".env")  
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
    accent-color: #4CAF50;  /* changes the slider thumb & track color */
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
            model_name = "Qwen/Qwen3-0.6B"
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForCausalLM.from_pretrained(model_name)
            pipe = (tokenizer, model)

        tokenizer, model = pipe

    
        messages = [{"role": "system", "content": system_message}]
        messages.extend(history)
        messages.append({"role": "user", "content": message + " /no_think"})

        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        inputs = tokenizer(text, return_tensors="pt")
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
        )[0][len(inputs.input_ids[0]):].tolist()

        response = tokenizer.decode(output_ids, skip_special_tokens=True)
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
            model="Qwen/Qwen3-Coder-30B-A3B-Instruct:fireworks-ai",
            messages=clean_messages,
            max_tokens=max_tokens,
            stream=True,
            temperature=temperature,
            top_p=top_p,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                response += chunk.choices[0].delta.content
                yield response


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
    demo.launch()