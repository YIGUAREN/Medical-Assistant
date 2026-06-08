import os

def get_abs_path(relative_path: str) -> str:
    """
    获取相对于项目根目录的绝对路径。
    项目根目录为 backend/.. 即 Medical-Assistant/
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    return os.path.join(project_root, relative_path)
