from pygost.gost3411_12 import GOST341112
from elliptic import Ellipic
from random import randint
from pathlib import Path


def get_ecp_params(a: int, 
                   b: int, 
                   p: int, 
                   q: int = 0,
                   P: tuple[int, int] = 0,
                   Q: tuple[int, int] = 0,
                   d: int = 0,
                   auto: bool = False):
    E = Ellipic(p=p, a=a, b=b)

    if not auto:
        prime_ords: dict[int: int] = {}
        counter: int = 0
        for O in E.ORDS:
            if E.farm_theory(n=O, t=10):
                prime_ords[counter] = O
                counter += 1

        if not prime_ords:
            raise ValueError("Не вычислено ни одного простого "
                            "порядка подгруппы эллиптической кривой\n"
                            "Задайте другие параметры эллиптической кривой")
        
        print(f"Найдено {len(prime_ords)} простых порядков подгруппы эллиптической кривой")

        while True:
            ord_idx: int = int(input(f"Выберите подгруппу по номеру (0-{len(prime_ords)-1}): "))
            if 0 <= ord_idx <= (len(prime_ords)-1):
                break

        q: int = prime_ords[ord_idx]

    filtered_subgroups: dict[tuple: list] = E.filter_by_ord(subgroups=E.subgroups, O=q)
    
    if not auto: 
        available_points = {
                            idx: point
                            for idx, point in enumerate(filtered_subgroups.keys())
        }

        print(f"Найдено {len(available_points)} образующих точек подгруппы с порядком {q=}")

        while True:
            P_idx = int(input(f"Выберите образующую точку подгруппы по номеру (0-{len(available_points)-1}): "))
            if 0 <= P_idx <= (len(available_points)-1):
                break

        P: tuple[int, int] = available_points[P_idx]
        print(f'Выбрана подгруппа порядка {q=}\n'
          f"Выбрана образующая точка подгруппы {P=}")

    calculations_P_subgroup: dict[int: tuple] = filtered_subgroups[P][0]
    
    if not auto:
        while True:
            d = int(input(f"Укажите значение для ключа подписи (0 < d < {q}): "))
            if 0 < d < q:
                break
    if not Q:
        Q: tuple[int, int] = calculations_P_subgroup[d]

    calculations_Q_subgroup = filtered_subgroups[Q][0]

    return E, q, P, calculations_P_subgroup, Q, calculations_Q_subgroup, d


def generate_ecp(message: bytes,
                 q: int,
                 calculations_P_subgroup: dict[int: tuple],
                 d: int, 
                 bits: int = 256,):
    """
    
    """
    # Шаг 0: Проверка
    if bits not in (256, 512):
        raise ValueError("bits должен быть 256 или 512")

    # Шаг 1: Генерация хеша исходного текста   
    gost = GOST341112(data=message, digest_size=bits)
    H = gost.hexdigest()

    # Шаг 2: Вычислить alpha, e
    alpha = int.from_bytes(bytes.fromhex(H), 'big')

    e = alpha % q
    if e == 0:
        e = 1

    # Шаг 3: Сгенерировать целое число 0 < k < q
    while True:
        k: int = randint(1, q - 1) # т.к. метод выбирает число из промежутка [a, b]

        # Шаг 4: Вычислить C, r
        C: tuple[int, int] = calculations_P_subgroup[k]
        x: int = C[0]
        r: int = x % q

        if r == 0:
            continue
    
        # Шаг 5: Вычислить число s
        s: int = (r * d + k * e) % q
        if s != 0:
            break
    
    # Шаг 6: Вычислить двоичные вектора r и s
    byte_length = bits // 8
    r_bytes = r.to_bytes(byte_length, 'big')
    s_bytes = s.to_bytes(byte_length, 'big')

    # Получение ЭЦП: ksi = r || s
    ksi: bytes = r_bytes + s_bytes

    return ksi


def verify_ecp(message: bytes, 
               ksi: bytes, 
               E: Ellipic,
               q: int,
               calculations_P_subgroup: dict[int: tuple],
               calculations_Q_subgroup: dict[int: tuple],
               bits: int = 256,):
    
    # Шаг 0: Проверка
    if bits not in (256, 512):
        raise ValueError("bits должен быть 256 или 512")
    
    # Шаг 1: Получить значения r, s из ksi
    half = len(ksi) // 2

    r = int.from_bytes(ksi[:half], 'big')
    s = int.from_bytes(ksi[half:], 'big')

    if not (0 < r < q) or not (0 < s < q):
        return False

    # Шаг 2: Генерация хеша исходного текста   
    gost = GOST341112(data=message, digest_size=bits)
    H = gost.hexdigest()

    # Шаг 3: Вычислить alpha, e
    alpha = int.from_bytes(bytes.fromhex(H), 'big')

    e = alpha % q
    if e == 0:
        e = 1

    # Шаг 4: Вычислить v = e^(-1)(mod q)
    v: int = E.inv(x=e, p=q)

    # Шаг 5: Вычислить значения z1 = sv(mod q) и z2 = -rv(mod q)
    z1: int = (s * v) % q
    z2: int = (-r * v) % q

    # Шаг 6: Вычислить C=z1*P + z2* Q
    z1P = calculations_P_subgroup[z1]
    z2Q = calculations_Q_subgroup[z2]
    C = E.calculate_point(P=z1P, Q=z2Q)
    x: int = C[0]
    R: int = x % q

    return True if R == r else False


if __name__ == "__main__":
    test_message = b'Hello, world!'

    E, q, P, calculations_P_subgroup, Q, calculations_Q_subgroup, d = get_ecp_params(a=42, b=5, p=103)
    ksi= generate_ecp(message=test_message,
                       q=q,
                       calculations_P_subgroup=calculations_P_subgroup,
                       d=d)

    is_valid = verify_ecp(message=test_message,
                      ksi=ksi,
                      E=E,
                      q=q,
                      calculations_Q_subgroup=calculations_Q_subgroup,
                      calculations_P_subgroup=calculations_P_subgroup)
    
    print(is_valid)
    