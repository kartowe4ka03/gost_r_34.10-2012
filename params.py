from pathlib import Path

class Params:
    def get_datetime_now():
        """
        Получить текущую дату до секунды
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")
    

    # ---------------------------------------------
    # Константы
    # ---------------------------------------------
    PROJECT_ROOT = Path(__file__).parent.resolve()
    LOG_FILE = PROJECT_ROOT / "logs" / f"{get_datetime_now()}.log"
    ENV_FILE = PROJECT_ROOT / ".env"
    SIGNATURES_DIR = PROJECT_ROOT / "signatures/"

    # Допустимые значения для переменных конфигурации
    _VALID_HASH_SIZES  = {256, 512}
    _VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    _VALID_APP_MODES  = {"generate", "verify"}