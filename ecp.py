from pygost.gost3411_12 import GOST341112
from elliptic import Ellipic
from random import randint


def get_ecp_params(a: int, 
                   b: int, 
                   p: int, 
                   q: int,
                   P: tuple[int, int],
                   d: int = 0,
                   mode: str = 'generate'
    ) -> tuple[Ellipic, tuple[int, int], int] | Ellipic:
    E = Ellipic(p=p, a=a, b=b, q=q, P=P)

    if mode == 'generate' and not d:
        while True:
            d = int(input(f"Укажите значение для ключа подписи (0 < d < {q}): "))
            if 0 < d < q:
                break

        Q: tuple[int, int] = E.calculate_new_point(P=E.P, n=d)

        return E, Q, d
    
    return E


def generate_ecp(message: bytes,
                 E: Ellipic,
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

    e = alpha % E.q
    if e == 0:
        e = 1

    # Шаг 3: Сгенерировать целое число 0 < k < q
    while True:
        k: int = randint(1, E.q - 1) # т.к. метод выбирает число из промежутка [a, b]

        # Шаг 4: Вычислить C, r
        C: tuple[int, int] = E.calculate_new_point(P=E.P, n=k)
        X: int = C[0]
        r: int = X % E.q

        if r == 0:
            continue
    
        # Шаг 5: Вычислить число s
        s: int = (r * d + k * e) % E.q
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
               Q: tuple,
               bits: int = 256,) -> bool:
    
    # Шаг 0: Проверка
    if bits not in (256, 512):
        raise ValueError("bits должен быть 256 или 512")
    
    # Шаг 1: Получить значения r, s из ksi
    half = len(ksi) // 2

    r = int.from_bytes(ksi[:half], 'big')
    s = int.from_bytes(ksi[half:], 'big')

    if not (0 < r < E.q) or not (0 < s < E.q):
        return False

    # Шаг 2: Генерация хеша исходного текста   
    gost = GOST341112(data=message, digest_size=bits)
    H = gost.hexdigest()

    # Шаг 3: Вычислить alpha, e
    alpha = int.from_bytes(bytes.fromhex(H), 'big')

    e = alpha % E.q
    if e == 0:
        e = 1

    # Шаг 4: Вычислить v = e^(-1)(mod q)
    v: int = E.inv(x=e, p=E.q)

    # Шаг 5: Вычислить значения z1 = sv(mod q) и z2 = -rv(mod q)
    z1: int = (s * v) % E.q
    z2: int = (-r * v) % E.q

    # Шаг 6: Вычислить C=z1*P + z2* Q
    z1P = E.calculate_new_point(P=E.P, n=z1)
    z2Q = E.calculate_new_point(P=Q, n=z2)
    C = E._calculate_point(P=z1P, Q=z2Q)
    x: int = C[0]
    R: int = x % E.q

    return True if R == r else False


if __name__ == "__main__":
    test_message = b'Hello, world!'

    E, Q, d = get_ecp_params(a=4, b=6, p=13, q=7, P=(-2, 4))
    ksi= generate_ecp(message=test_message, E=E, d=d)

    is_valid = verify_ecp(message=test_message, ksi=ksi, E=E, Q=Q)
    
    print(is_valid)
    