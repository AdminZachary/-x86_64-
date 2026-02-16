from huggingface_hub import hf_hub_download
import sys
sys.path.insert(0, '.')
hf_hub_download(
    repo_id='Qwen/Qwen1.5-1.8B-Chat-GGUF',
    filename='qwen1_5-1_8b-chat-q4_k_m.gguf',
    local_dir='/home/zwj/llm_assistant/models'
)
print('Model downloaded successfully!')
