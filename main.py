import sys
import argparse
from pathlib import Path
from ecp import generate_ecp
from elliptic import Ellipic


def arg_parse():
    parser = argparse.ArgumentParser(
        description="ГОСТ Р 34.10-2012 - Электронная цифровая подпись"
    )
    parser.add_argument("file", nargs="?", help="Файл для подписания (stdin если не указан)")
    parser.add_argument("--bits", type=int, choices=[256, 512], default=256,
                        help="Длина хэш-кода: 256 (по умолчанию) или 512")
    parser.add_argument("--test", action="store_true",
                        help="Самопроверка по контрольным примерам стандарта")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Ошибка: файл '{args.file}' не найден.", file=sys.stderr)
            sys.exit(1)
        data = path.read_bytes()
        source = str(path)
    else:
        data = sys.stdin.buffer.read()
        source = "<stdin>"


def main():
    return
    