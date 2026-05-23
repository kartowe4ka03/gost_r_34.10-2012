import sys
import logging
from pathlib import Path
from argparse import ArgumentParser, Namespace

from params import Params
from handler import (read_file, write_file, load_config, 
                     save_signature_params, load_signature_params)
from ecp import generate_ecp, verify_ecp


# ======================================================================
# Настройка логирования
# ======================================================================
def setup_logging(log_level: str = "DEBUG") -> None:
    """
    Конфигурирует корневой логгер: вывод в stdout и в файл одновременно.

    Params:
        log_level (str): Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    root_logger = logging.getLogger()

    # Защита от повторной инициализации
    if root_logger.handlers:
        return
    
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger.setLevel(numeric_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Обработчик вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)

    # Обработчик записи в файл
    file_handler = logging.FileHandler(Params.LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)  # В файл пишем всё, включая DEBUG

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def arg_parse(config: dict) -> Namespace:
    """
    Парсинг аргументов командной строки.

    Args:
        config (dict): Словарь параметров из .env

    Returns:
        args (Namespace): Параметры запуска.
    """
    parser = ArgumentParser(
        prog="gost-ecp",
        description="Формирование и проверка ЭЦП ГОСТ Р 34.10-2012"
    )

    # ----------------------------
    # Общие аргументы
    # ----------------------------
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        default=config["INPUT_FILE"],
        help="Файл для подписания или проверки"
    )

    # ----------------------------
    # Режимы работы
    # ----------------------------
    mode_group = parser.add_mutually_exclusive_group(required=False)

    mode_group.add_argument(
        "-g",
        "--generate",
        action="store_true",
        help="Режим формирования ЭЦП"
    )

    mode_group.add_argument(
        "-v",
        "--verify",
        action="store_true",
        help="Режим проверки ЭЦП"
    )

    # ----------------------------
    # Аргументы generate
    # ----------------------------
    parser.add_argument(
        "--bits",
        type=int,
        choices=(256, 512),
        default=256,
        help="Длина хэш-кода: 256 или 512 (по умолчанию 256)"
    )

    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        default=False,
        help="Запретить переподписание документа"
    )

    # ----------------------------
    # Аргументы verify
    # ----------------------------
    parser.add_argument(
        "--sign",
        type=Path,
        help="Файл подписи"
    )

    parser.add_argument(
        "--metadata",
        type=Path,
        help="JSON-файл с параметрами подписи"
    )

    args = parser.parse_args()

    # ======================================================
    # Валидация аргументов режима verify
    # ======================================================
    if args.verify:
        if not args.metadata or not args.sign:
            parser.error(
                "--metadata и --sign обязательны"
                "в режиме --verify"
            )

    return args


# ══════════════════════════════════════════════════════════════════════
# Применение аргументов CLI поверх конфигурации
# ══════════════════════════════════════════════════════════════════════
def _merge_args_into_config(config: dict, args: Namespace) -> dict:
    """
    Объединяет конфигурацию из .env с аргументами CLI.
    Аргументы CLI имеют приоритет над значениями из .env.

    Args:
        config (dict):              Конфигурация из .env.
        args (argparse.Namespace):  Аргументы из командной строки.

    Returns:
        dict: Итоговая конфигурация.
    """
    logger = logging.getLogger(__name__)

    # Входной / выходной файл
    config["INPUT_FILE"]  = args.file

    # Направление операции: CLI-флаги перекрывают APP_MODE из .env
    if args.generate:
        config['APP_MODE'] = "generate"

        # Запрет перезаписи: --no-overwrite перекрывает OVERWRITE_OUTPUT=true
        if args.no_overwrite:
            config["OVERWRITE"] = False
    elif args.verify:
        config['APP_MODE'] = "verify"
        config['SIGN'] = args.sign
        config['METADATA'] = args.metadata

    # Иначе остаётся значение из .env

    config['HASHSIZE'] = args.bits

    logger.debug("Итоговая конфигурация после слияния с CLI:")
    logger.debug("  app_mode        = %s", config["APP_MODE"])
    logger.debug("  input_file      = %s", config["INPUT_FILE"])

    if args.verify:
        logger.debug("  overwrite_output= %s", config["OVERWRITE"])

    return config


def main():
    """
    Точка входа программы. Управляет полным жизненным циклом проекта:

    1. Bootstrap-логирование (DEBUG) до загрузки .env.
    2. Загрузка и валидация конфигурации из .env.
    3. Переинициализация логирования с уровнем из конфига.
    4. Парсинг аргументов CLI и слияние с конфигурацией.
    5. Проверка входного файла и условия перезаписи.
    6. Запуск операции подписания или проверки подписи.
    """
    # Шаг 1: bootstrap-логирование — нужно уже при load_config()
    setup_logging("DEBUG")
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Запуск ЭЦП-утилиты")
    logger.info("Корень проекта: %s", Params.PROJECT_ROOT)

    # Шаг 2: получение пользовательского уровня логирования
    config = load_config()

    # Шаг 3: переинициализация логирования с уровнем из конфига
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    setup_logging(config['LOG_LEVEL'])
    # Логгер нужно получить заново — уровень мог измениться
    logger = logging.getLogger(__name__)

    # Шаг 4: парсинг CLI
    args: Namespace = arg_parse(config=config)
    config = _merge_args_into_config(config, args)
    MODE = config['APP_MODE']

    if MODE == 'generate':
        match config['d']:
            case 0: logger.info("Ручной режим подписания файла")
            case _: logger.info("Автоматический режим подписания файла")

    elif MODE == 'verify':
            filename: Path  = config["INPUT_FILE"].name
            filename_ecp_dir = Params.SIGNATURES_DIR / filename

            if not filename_ecp_dir.exists():
                raise FileNotFoundError(f"Не найдена директория подписанного файла: {filename}")

            config['SIGN'] = filename_ecp_dir / f"{filename}.sig"

            if not config['SIGN'].exists():
                raise FileNotFoundError(f"Не найден файл ЭЦП для документа: {filename}")

            config['METADATA'] = filename_ecp_dir / "METADATA.json"

            if not config['METADATA'].exists():
                raise FileNotFoundError(f"Не найдены метаданные для ЭЦП документа: {filename}")

    # Шаг 5: проверка входного файла
    input_path: Path  = config["INPUT_FILE"]
    if not input_path.exists():
        logger.error("Входной файл не найден: %s", input_path)
        sys.exit(1)

    if not input_path.is_file():
        logger.error("Указанный путь не является файлом: %s", input_path)
        sys.exit(1)

    # Шаг 6: чтение входных файлов
    data = read_file(filename=input_path)
    logger.debug("Прочитано %d байт.", len(data))

    if MODE == 'verify':
        KSI: bytes = read_file(filename=config['SIGN'])
        METADATA: dict = load_signature_params(filepath=config['METADATA'])

    # Шаг 7: запуск операции
    logger.info(
        "Операция: %s | Размер хеш-кода: %s | Файл: %s",
        config["APP_MODE"].upper(),
        config["HASHSIZE"],
        input_path,
    )

    if MODE == 'generate':
        logger.info("Начало подписания: %s", input_path)

        KSI, Q = generate_ecp(
                           message=data,
                           elliptic_params=config['ELLIPTIC_PARAMS'],
                           d=config['d'],
                           bits=config['HASHSIZE'],
        )

        output_path = write_file(
                                 source_file=input_path,
                                 signature=KSI,
                                 overwrite=config['OVERWRITE'],
        )
        save_signature_params(
                              filepath=input_path,
                              **config['ELLIPTIC_PARAMS'],
                              Q=Q,
                              bits=config['HASHSIZE'],
        )

        logger.info("Документ %s подписан и сохранен → %s", input_path, output_path)

    elif MODE == 'verify':
        logger.info("Начало проверки подписи: %s", input_path)
        is_verified = verify_ecp(
                                 message=data,
                                 ksi=KSI,
                                 elliptic_params=METADATA['ELLIPTIC_PARAMS'],
                                 Q=METADATA['Q'],
                                 bits=METADATA['HASHSIZE']
        )
        if is_verified:
            logger.info(
                        "Подпись %s ДЕЙСТВИТЕЛЬНА для документа %s", 
                        config['SIGN'],
                        input_path,
            )
            
        else:
            logger.error(
                           "Подпись %s НЕДЕЙСТВИТЕЛЬНА для документа %s", 
                           config['SIGN'],
                           input_path,
            )

if __name__ == "__main__":
    main()