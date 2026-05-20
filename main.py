import sys
import logging
from pathlib import Path
from argparse import ArgumentParser, Namespace

from params import Params
from handler import (read_file, write_file, load_config, 
                     save_signature_params, load_signature_params)
from ecp import get_ecp_params, generate_ecp, verify_ecp


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


def arg_parse() -> Namespace:
    """
    Парсинг аргументов командной строки.

    Returns:
        argparse.Namespace с параметрами запуска.
    """
    parser = ArgumentParser(
        prog="gost-ecp",
        description="Формирование и проверка ЭЦП ГОСТ Р 34.10-2012"
    )

    # ----------------------------
    # Общие аргументы
    # ----------------------------
    parser.add_argument(
        "-r",
        "--read",
        action="store_true",
        required=False,
        help="Режим чтения конфигурации из файла виртуального окружения"
    )

    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        required=False,
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
        "-e",
        "--elliptic",
        nargs=3,
        metavar=("A", "B", "P"),
        type=int,
        help="Параметры эллиптической кривой: a b p"
    )

    parser.add_argument(
        "--bits",
        type=int,
        choices=(256, 512),
        default=256,
        help="Длина хэш-кода: 256 или 512 (по умолчанию 256)"
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Разрешить переподписание документа"
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
    # Валидация аргументов режима generate
    # ======================================================
    if args.generate:
        if args.elliptic is None:
            parser.error(
                "--elliptic обязателен в режиме "
                "--generate"
            )

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


def main():
    # Шаг 1: bootstrap-логирование — нужно уже при load_config()
    setup_logging("DEBUG")
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Запуск ЭЦП-утилиты")
    logger.info("Корень проекта: %s", Params.PROJECT_ROOT)

    # Шаг 2: получение пользовательского уровня логирования
    LOG_LEVEL = load_config(mode='logging')

    # Шаг 3: переинициализация логирования с уровнем из конфига
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    setup_logging(LOG_LEVEL)
    # Логгер нужно получить заново — уровень мог измениться
    logger = logging.getLogger(__name__)

    # Шаг 4: парсинг CLI
    AUTO = False
    ecp_params = {}
    args = arg_parse()
    if args.read:
        AUTO = True
        config = load_config()
        mode = config['APP_MODE']
        input_path: Path = config['INPUT_FILE']

        if mode == 'generate':
            OVERWRITE = config['OVERWRITE']
            ecp_params = config.copy()
            del ecp_params['HASHSIZE'], \
                ecp_params['INPUT_FILE'],\
                ecp_params['APP_MODE'],\
                ecp_params['OVERWRITE']
            # a = config['a']
            # b = config['b']
            # p = config['p']
            # q = config['q']
            # P = config['P']
            # d = config['d']
            bits = config['HASHSIZE']

        elif mode == 'verify':
            # sign = config['SIGN']
            # metadata = config['METADATA']
            sign_path = Params.PROJECT_ROOT / 'signatures' / input_path / f'{input_path}.sig'
            metadata_path = Params.PROJECT_ROOT / 'signatures' / input_path / 'METADATA.JSON'
            ecp_params = load_signature_params(filepath=metadata_path)

    else:
        if args.generate:
            mode = args.generate
            OVERWRITE = args.overwrite
            ecp_params = {
                      'a': args.elliptic[0],
                      'b': args.elliptic[1],
                      'p': args.elliptic[2],
            }
            bits = args.bits

        elif args.verify:
            mode = args.verify
            sign_path = args.sign
            metadata_path = args.metadata
            ecp_params = load_signature_params(filepath=metadata_path)

        elif not args.generate and not args.verify:
            raise ValueError("Отсутствует аргумент -g/--generate или -v/--verify\n"
                             "Справка: python main.py --help")
            
        input_path: Path = args.file

    # Шаг 5: чтение входного файла
    data = read_file(filename=input_path)
    logger.debug("Прочитано %d байт.", len(data))

    # Шаг 6: запуск операции
    E, q, \
    P, calculations_P_subgroup, \
    Q, calculations_Q_subgroup, d = get_ecp_params(**ecp_params,
                                                       auto=AUTO,)
    if mode == 'generate':
        ksi = generate_ecp(
                           message=data,
                           q=q,
                           calculations_P_subgroup=calculations_P_subgroup,
                           d=d,
                           bits=bits)
        
        output = write_file(
                            source_file=input_path,
                            signature=ksi,
                            overwrite=OVERWRITE
        )

        save_signature_params(
                              filepath=output / "METADATA.JSON",
                              **ecp_params,
                              bits=bits
        )
        
    elif mode == 'verify':
        ksi = read_file(filename=sign_path)
        is_verify = verify_ecp(
                                message=data,
                                ksi=ksi,
                                E=E,
                                q=q,
                                calculations_P_subgroup=calculations_P_subgroup,
                                calculations_Q_subgroup=calculations_Q_subgroup,
                                bits=bits
        )
        if is_verify:
            print(True)

        else:
            print(False)

if __name__ == "__main__":
    main()