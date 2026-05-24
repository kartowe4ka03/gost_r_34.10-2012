import os
import sys
import json
import logging
# python-dotenv для безопасной загрузки переменных из .env
try:
    from dotenv import load_dotenv
except ImportError:
    print(
        "[ОШИБКА] Библиотека python-dotenv не установлена.\n"
        "Выполните: pip install python-dotenv",
        file=sys.stderr,
    )
    sys.exit(1)

from pathlib import Path
from shutil import copy2

from params import Params


logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# Чтение-запись файла
# ══════════════════════════════════════════════════════════════════
def read_file(filename: Path) -> bytes:
    """
    Читает файл и возвращает его содержимое в виде bytes.

    Файл всегда читается в бинарном режиме: AES оперирует байтами,
    а не строками. Текстовые файлы проходят через байтовый конвейер
    точно так же, как бинарные — на уровне шифрования нет разницы.

    Params:
        filename (Path): Путь к файлу.

    Returns:
        data (bytearray): Содержимое файла. При ошибке — завершение программы.
    """
    logger.debug("Чтение файла: %s", filename)

    if not filename.exists():
        logger.error("Файл не найден: %s", filename)
        sys.exit(1)

    if not filename.is_file():
        logger.error("Указанный путь не является файлом: %s", filename)
        sys.exit(1)

    try:
        data = filename.read_bytes()
        logger.debug(
            "Файл успешно прочитан: %s (%d байт).", filename, len(data)
        )
        return data

    except PermissionError:
        logger.error("Нет прав доступа для чтения файла: %s", filename)
    except OSError as e:
        logger.error("Ошибка чтения файла '%s': %s", filename, e)

    sys.exit(1)


def write_file(
    source_file: Path,
    signature: bytes,
    overwrite: bool = False,
) -> Path:
    """
    Сохранение подписанного файла и ЭЦП.

    Структура:

    signatures/
    └── initial_text.txt/
        ├── initial_text.txt
        └── signature.sig

    Args:
        source_file:
            Исходный файл для подписания.

        signature:
            Байты ЭЦП.

        overwrite:
            Разрешение переподписания.

    Returns:
        Path:
            Путь к каталогу подписи.

    Raises:
        FileNotFoundError:
            Исходный файл не существует.

        FileExistsError:
            Переподписание запрещено пользователем.
    """
    # -----------------------------------------
    # Проверка существования исходного файла
    # -----------------------------------------
    if not source_file.exists():
        raise FileNotFoundError(
            f"Файл не найден: {source_file}"
        )

    # =========================================
    # 1. Проверка/создание папки signatures
    # =========================================
    Params.SIGNATURES_DIR.mkdir(exist_ok=True)

    # =========================================
    # 2. Каталог конкретного файла
    # =========================================
    file_dir = Params.SIGNATURES_DIR / source_file.name

    if file_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"Переподписание файла "
                f"'{source_file.name}' запрещено "
                f"(overwrite=False)"
            )
    else:
        file_dir.mkdir()

    # =========================================
    # 3. Копирование исходного файла
    # =========================================
    destination_file = file_dir / source_file.name

    copy2(
        src=source_file,
        dst=destination_file
    )

    # =========================================
    # 4. Сохранение подписи
    # =========================================
    signature_path = file_dir / f"{source_file.name}.sig"

    with signature_path.open("wb") as f:
        f.write(signature)

    return file_dir


def save_signature_params(
    filepath: str | Path,
    a: int,
    b: int,
    p: int,
    q: int,
    P: tuple[int, int],
    Q: tuple[int, int],
    bits: int = 256,
) -> None:
    """
    Сохранение параметров проверки ЭЦП в JSON-файл.

    Args:
        filepath: путь к JSON-файлу
        a: параметр эллиптической кривой
        b: параметр эллиптической кривой
        p: модуль конечного поля
        q: порядок подгруппы эллиптической кривой
        P: базовая точка (образующий элемент подгруппы)
        Q: открытый ключ Q = dP
        bits: режим хэширования ГОСТ (256 или 512)

    Raises:
        ValueError: если переданы некорректные параметры
    """
    if bits not in (256, 512):
        raise ValueError("bits должен быть 256 или 512")

    data = {
        "elliptic": {
            "a": a,
            "b": b,
            "p": p,
        },
        'q': q,
        "P": list(P),
        "Q": list(Q),
        "HASHSIZE": bits,
    }

    filepath = Params.SIGNATURES_DIR / filepath.name / "METADATA.json"

    with filepath.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )


def load_signature_params(filepath: str | Path) -> dict:
    """
    Чтение параметров проверки ЭЦП из JSON-файла.

    Args:
        filepath: путь к JSON-файлу

    Returns:
        Словарь параметров:
        {
            'a': int,
            'b': int,
            'p': int,
            'q': int,
            'P': tuple[int, int],
            'Q': tuple[int, int],
            'HASHSIZE': int
        }

    Raises:
        FileNotFoundError: файл не найден
        ValueError: JSON содержит некорректные данные
    """
    filepath = Path(filepath)

    with filepath.open("r", encoding="utf-8") as f:
        data = json.load(f)

    bits = data["HASHSIZE"]

    if bits not in (256, 512):
        raise ValueError("Некорректное значение bits")

    params = {
              "ELLIPTIC_PARAMS": {
                                  "a": data["elliptic"]["a"],
                                  "b": data["elliptic"]["b"],
                                  "p": data["elliptic"]["p"],
                                  "q": data["q"],
                                  "P": tuple(data["P"]),
              },
              "Q": tuple(data["Q"]),
              "HASHSIZE": bits,
    }

    return params


# ──────────────────────────────────────────────────────────────────────
# Загрузка и валидация конфигурации
# ──────────────────────────────────────────────────────────────────────
def load_config() -> dict:
    """
    Загружает конфигурацию из .env-файла, валидирует все параметры
    и возвращает готовый словарь.

    Returns:
        config (dict): Словарь с валидированными параметрами конфигурации.

    Raises:
        SystemExit(1): При отсутствии обязательных параметров или
                       обнаружении некорректных значений.
    """
    logger = logging.getLogger(__name__)
    errors: list[str] = []
    config: dict = {}
    elliptic_params: dict = {}

    if Params.ENV_FILE.exists():
        load_dotenv(dotenv_path=Params.ENV_FILE)
        logger.info("Конфигурация загружена из: %s", Params.ENV_FILE)
    else:
        logger.warning(
            "Файл .env не найден (%s). "
            "Используются переменные окружения системы (если заданы).",
            Params.ENV_FILE,
        )

    # ── Логирование ───────────────────────────────────────────────────
    log_level = os.environ.get("LOG_LEVEL", "DEBUG").strip().upper()
    if log_level not in Params._VALID_LOG_LEVELS:
        logger.warning(
            "LOG_LEVEL: недопустимое значение '%s'. Установлен уровень DEBUG.",
            log_level,
        )
        log_level = "DEBUG"

    config['LOG_LEVEL'] = log_level
    
    # ── Файлы ─────────────────────────────────────────────────────────
    default_input_file  = Path(os.environ.get("DEFAULT_INPUT_FILE",  "initial_text.txt").strip())

    config['INPUT_FILE'] = default_input_file

    # ── Режим работы ───────────────────────────────────────────────────
    app_mode = os.environ.get("APP_MODE", "generate").strip().lower()
    if app_mode not in Params._VALID_APP_MODES:
        errors.append(
            f"APP_MODE: недопустимое значение '{app_mode}'. "
            f"Допустимые: {', '.join(sorted(Params._VALID_APP_MODES))}."
        )

    config['APP_MODE'] = app_mode

    # ── Поведение приложения ──────────────────────────────────────────
    overwrite_raw = os.environ.get("OVERWRITE", "true")
    try:
        if overwrite_raw.strip().lower() == "true":
            overwrite = True
        
        elif overwrite_raw.strip().lower() == "false":
            overwrite = False

        else:
            raise ValueError(
                            f"OVERWRITE имеет недопустимое значение '{overwrite_raw}'. "
                            f"Допустимые значения: true, false."
            )

    except ValueError as e:
        errors.append(str(e))
        overwrite = True

    config['OVERWRITE'] = overwrite

    # ── Параметры эллиптической кривой ────────────────────────────────
    a = os.environ.get('a', '')
    if not a:
        errors.append(f"Elliptic param a: не задан коэффициент эллиптической кривой: {a=}.")
        a = '0'

    elliptic_params['a'] = int(a.upper(), base=16)

    b = os.environ.get('b', 0)
    if not b:
        errors.append(f"Elliptic param b: не задан коэффициент эллиптической кривой: {b=}.")
        b = '0'
    
    elliptic_params['b'] = int(b.upper(), base=16)

    p = os.environ.get('p', 0)
    if not p:
        errors.append(f"Elliptic param p: не задан модуль эллиптической кривой: {p=}.")
        p = '0'

    elliptic_params['p'] = int(p.upper(), base=16)

    q = os.environ.get('q', 0)
    if q:
        q = int(q.upper(), base=16)

    else:
        errors.append(f"Elliptic param q: не задан порядок подгруппы эллиптической кривой: {q=}.")
        q = 0

    elliptic_params['q'] = q

    x_P = os.environ.get('x_P', 0)
    if not x_P:
        errors.append(f"Elliptic param x_P: не задана координата X точки эллиптической кривой: {x_P=}.")
        x_P = '0'

    y_P = os.environ.get('y_P', 0)
    if not y_P:
        errors.append(f"Elliptic param y_P: не задана координата Y точки эллиптической кривой: {y_P=}.")
        y_P = '0'
    
    P: tuple[int, int] = (
                          int(x_P.upper(), base=16), 
                          int(y_P.upper(), base=16)
    )

    elliptic_params['P'] = P

    config['ELLIPTIC_PARAMS'] = elliptic_params

    d = os.environ.get('d', 0)
    if d:
        d = int(d.upper(), base=16)
        if not (0 < d < q):
            errors.append(f"Elliptic param d: недопустимое значение: {d=}.\n"
                            f"Границы: 0 < {d=} < {q=}")
            
    else:
        d = 0
    
    config['d'] = d

    # ── Размер хеш-кода ──────────────────────────────────────────────────
    try:
        bits = int(os.environ.get("HASHSIZE", "256").strip())
        if bits not in Params._VALID_HASH_SIZES:
            raise ValueError
    except ValueError:
        bits = 256
        errors.append(
            f"Hashsize param bits: недопустимое значение. "
            f"Допустимые: {', '.join(str(s) for s in sorted(Params._VALID_HASH_SIZES))}."
        )

    config['HASHSIZE'] = bits
        
    # ── Вывод всех ошибок и выход ─────────────────────────────────────
    if errors:
        logger.error("Обнаружены ошибки конфигурации (%d):", len(errors))
        for i, err in enumerate(errors, start=1):
            logger.error("  %d) %s", i, err)
        sys.exit(1)

    logger.debug("Конфигурация успешно загружена и валидирована.")
    logger.debug("  LOGGING LEVEL = %s", config["LOG_LEVEL"])
    logger.debug("  APP_MODE      = %s", config["APP_MODE"])
    logger.debug("  OVERWRITE     = %s", config["OVERWRITE"])
    logger.debug("  Elliptic:")
    logger.debug("  a             = %s", elliptic_params['a'])
    logger.debug("  b             = %s", elliptic_params['b'])
    logger.debug("  p             = %s", elliptic_params['p'])
    logger.debug("  Subgroup params:")
    logger.debug("  q             = %s", elliptic_params['q'])
    logger.debug("  P             = %s", elliptic_params['P'])
    logger.debug("  d             = %s", config['d'] if config['d'] else "Undefined")
    logger.debug("  HASHSIZE      = %s", config['HASHSIZE'])

    return config


if __name__ == "__main__":
    my_string = "2BB312A43BD2CE6E0D020613C857ACDDCFBF061E91E5F2C3F32447C259F39B2С83АВ156D77F1496BF7EB3351Е1EE4E43DC1A18В91B24640B6DBB92CB1ADD371Е"
    print(my_string.replace('А', 'A').replace('В', 'B').replace('С', 'C').replace('Е', 'E'))