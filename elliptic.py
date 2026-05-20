from random import randint

class Ellipic:
    def __init__(self, p: int, a: int = 1, b: int = 1):
        is_prime = self.farm_theory(n=p, t=10)
        if not is_prime:
            raise ValueError(f"Число {p=} является составным!")
        
        self.a: int = a
        self.b: int = b
        self.p: int = p

        F_elems: dict[int] = self.__F()
        __X: dict[int] = self.__check_F_elems(F_elems=F_elems)
        self.POINTS: list[tuple] = self.__calculate_Y(X=__X)
        group_and_subgroups: tuple[dict[tuple]] = self.__calculate_ords()
        self.group = group_and_subgroups[0]
        self.subgroups = group_and_subgroups[1]
        self.ORDS = group_and_subgroups[2]


    def __F(self) -> list:
        F_elems = []
        limit = (self.p - 1) // 2
        for k in range(0, limit + 1):
            F_elems.append(k)
            if k != 0:
                F_elems.append(-k)
        return F_elems
    

    def __check_F_elems(self, F_elems: list) -> dict:
        X = {}
        for elem in F_elems:
            X[elem] = elem ** 2 % self.p
        return X
    

    def __calculate_Y(self, X: dict) -> list:
        POINTS = [0,]
        for x in X.keys():
            square_y = (x ** 3 + self.a * x + self.b) % self.p
            if square_y in X.values():
                Y = self.return_key_by_value(dict_=X, value=square_y)
                for y in Y:
                    POINTS.append((x, y))
        return POINTS
    

    def __calculate_O(self, point) -> tuple:
        P_dict = {
                        0: 0,
                        1: point,
                        }
        
        i = 2
        x3, y3 = 1, 1

        while True:
            if i % 2 == 0:
                x3, y3 = self.calculate_point(P=P_dict[i // 2],
                                              Q=P_dict[i // 2])
            else:
                k = i // 2
                n = i - k
                x3, y3 = self.calculate_point(P=P_dict[k],
                                              Q=P_dict[n])
                                              
            if x3 == 0 and y3 == 0:
                break

            P_dict[i] = (x3, y3) 
            i += 1
        
        
        return P_dict, i # Возвращение порядка группы O = i
    

    def calculate_point(self, P, Q) -> tuple:
        limit = (self.p - 1) // 2
        x1, y1 = P
        x2, y2 = Q

        # Случай 1, когда P(x) == Q(x) и P(y) != Q(y)
        if x1 == x2 and (y1 != y2 or y1 == y2 == 0):
            x3 = 0
            y3 = 0

        # Случай 2, когда P == Q
        elif x1 == x2 and y1 == y2:
            # ВЫЧИСЛЕНИЕ X3
            # Вычисление (3 * x1 ^ 2 + a) и (2 * y1)
            numerator = 3 * x1 ** 2 + self.a
            denumerator = 2 * y1

            # Вычисление (3 * x1 ^ 2 + a) ^ 2 и (2 * y1) ^ 2
            sqr_numerator = numerator ** 2
            sqr_denumerator = denumerator ** 2
            
            div = sqr_numerator * self.inv(sqr_denumerator, self.p)
            x3 = (div - 2 * x1) % self.p
            if x3 > limit:
                x3 -= self.p

            # ВЫЧИСЛЕНИЕ Y3
            numerator_mul_x1_sub_x3 = numerator * (x1 - x3)
            div = numerator_mul_x1_sub_x3 * self.inv(denumerator, self.p)
            
            y3 = (div - y1) % self.p
            if y3 > limit:
                y3 -= self.p

        # Случай 3, когда P != Q
        else:
            # ВЫЧИСЛЕНИЕ X3
            # Вычисление (y2-y1) и (x2-x1)
            y2_sub_y1 = y2 - y1
            x2_sub_x1 = x2 - x1

            # Вычисление (y2-y1)^2 и (x2-x1)^2
            sqr_y2_sub_y1 = y2_sub_y1 ** 2
            sqr_x2_sub_x1 = x2_sub_x1 ** 2

            div = sqr_y2_sub_y1 * self.inv(sqr_x2_sub_x1, self.p)
            x3 = (div - x1 - x2) % self.p
            if x3 > limit:
                x3 -= self.p

            # ВЫЧИСЛЕНИЕ Y3
            numerator = y2_sub_y1 * (x1 - x3)
            div = numerator * self.inv(x2_sub_x1, self.p)
            y3 = (div - y1) % self.p
            if y3 > limit:
                y3 -= self.p

        return (x3, y3)
    

    def __calculate_ords(self) -> dict[list]:
        """
        Рассчет всех возможных порядков для имеющихся точек поля
        """
        group: dict[list] = {'fundaments': [],
                              'points': []}
        subgroups: dict[list] = {}
        ords_list = []
        # Исключение нулевой точки эллиптической кривой путем среза списка
        for point in self.POINTS[1:]:
            _calc, O = self.__calculate_O(point=point)
            if O not in ords_list:
                ords_list.append(O)

            if O == len(self.POINTS):
                group['fundaments'].append(point)
                group['points'] = list(_calc.values())
            else:
                subgroups[point] = [_calc, O]

        ords_list.sort()
        return group, subgroups, ords_list


    @staticmethod
    def inv(x, p) -> int:
        return pow(x, -1, p)
        

    @staticmethod
    def return_key_by_value(dict_: dict, value):
        return [key for key, val in dict_.items() if val == value]
    

    @staticmethod
    def filter_by_ord(subgroups: dict, O: int):
        return {
            point: stats
            for point, stats in subgroups.items()
            if stats[1] == O
        }
    

    @staticmethod
    def farm_theory(n: int, t: int):
        k = n - 1
        if n in (2, 3):
            return True
        
        for _ in range(t):
            a = randint(2, k)
            r = Ellipic.mod_pow(a=a, k=k, n=n)
            if r != 1:
                return False

        return True
    

    @staticmethod
    def mod_pow(a: int, k: int, n: int) -> int:
        """
        Возведение a в степень k по модулю n с формированием таблицы вычислений.

        Таблица содержит:
            k – текущий бит показателя степени,
            A – значение A на шаге,
            b – значение b на шаге.

        :return: (результат, таблица вычислений)
        """
        # Шаг 1
        b = 1
        if k == 0:
            return b

        # Шаг 2
        A = a % n

        rows = []

        # Шаг 3 (бит k0)
        k0 = k & 1
        if k0 == 1:
            b = A

        # состояние до цикла
        rows.append({"k": k0, "A": A, "b": b})

        t = k.bit_length() - 1

        # Шаг 4
        for i in range(1, t + 1):
            # 4.1
            A = (A * A) % n

            # текущий бит
            ki = (k >> i) & 1

            # 4.2
            if ki == 1:
                b = (A * b) % n

            rows.append({"k": ki, "A": A, "b": b})

        return b
        

if __name__ == "__main__":
    E = Ellipic(p=997, a=42, b=5)
    prime_ords = {}
    counter = 0
    for O in E.ORDS:
        if E.farm_theory(n=O, t=10):
            prime_ords[counter] = O
            counter += 1
    if not prime_ords:
        raise ValueError("Не вычислено ни одного простого "
                         "порядка подгруппы эллиптической кривой\n"
                         "Задайте другие параметры эллиптической кривой")
    
    print(f"Найдено {len(prime_ords)} простых порядков подгруппы "
        "эллиптической кривой")
    for key, val in prime_ords.items():
        print(key, val, sep=': ')

    while True:
        ord_idx = int(input(f"Выберите подгруппу по номеру (0-{len(prime_ords)-1}): "))
        if 0 <= ord_idx <= (len(prime_ords)-1):
            break

    q = prime_ords[ord_idx]

    filtered_subgroups = E.filter_by_ord(subgroups=E.subgroups, O=q)
    print(filtered_subgroups)
    available_points = {
                        idx: point
                        for idx, point in enumerate(filtered_subgroups.keys())
    }

    print(f"Найдено {len(available_points)} подгрупп с порядком {q=}")

    for key, val in available_points.items():
        print(key, val, sep=': ')

    while True:
        P_idx = int(input(f"Выберите образующую точку подгруппы по номеру (0-{len(prime_ords)-1}): "))
        if 0 <= P_idx <= (len(available_points)-1):
            break

    P = available_points[P_idx]
    calculations_P_subgroup = filtered_subgroups[P][0]

    print(f'Выбрана подгруппа порядка {q=}\n'
          f"Выбрана образующая точка подгруппы {P=}\n"
          f" Вычисления для выбранной образующей точки {P=}: "
          f"{calculations_P_subgroup}")