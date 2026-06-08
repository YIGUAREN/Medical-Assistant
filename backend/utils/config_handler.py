from backend.utils.path_tool import get_abs_path
import yaml

def load_prompts_config(config_path: str = None, encoding='utf-8-sig'):
    if config_path is None:
        config_path = get_abs_path('backend/config/prompts.yml')
    with open(config_path, 'r', encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)

def load_chroma_config(config_path: str = None, encoding='utf-8-sig'):
    if config_path is None:
        config_path = get_abs_path('backend/config/chroma.yml')
    with open(config_path, 'r', encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)

prompts_config = load_prompts_config()
chroma_config = load_chroma_config()
