class Ellipic:
    def __init__(self, p: int, a: int, b: int, q: int, P: tuple[int, int]):
        """
        Эллиптическая кривая для ЭЦП ГОСТ Р 34.10-2012.

        Кривая:
            y² = x³ + ax + b (mod p)

        Attributes:
            P:
                Базовая точка (генератор подгруппы)

            q:
                Порядок подгруппы

            a:
                Коэффициент эллиптической кривой

            b:
                Коэффициент эллиптической кривой

            p:
                Простое число конечного поля
        """                                        
        self.a: int = a
        self.b: int = b
        self.p: int = p
        self.q: int = q
        self.P: tuple[int, int] = P

        # Бесконечно удалённая точка O
        self.O = 0


    def calculate_new_point(
        self,
        P: tuple[int, int], 
        n: int
    ) -> tuple[int, int] | None:
        """
        Вычисление новой точки:

            Q = nP

        Args:
            n:
                Скаляр.

        Returns:
            Точка Q = nP
            или None (бесконечно удалённая точка).
        """
        if n < 0:
            raise ValueError("n должно быть >= 0")

        if n == 0:
            return self.O

        result = self.O

        while n:
            # Если младший бит = 1
            if n & 1:
                result = self._calculate_point(P=result, Q=P)

            # Удвоение точки
            P = self._calculate_point(P=P, Q=P)

            n >>= 1

        return result
    

    def _calculate_point(
                         self, 
                         P: tuple[int, int], 
                         Q: tuple[int, int]
        ) -> tuple[int, int]:
        """
        Сложение двух точек эллиптической кривой.

        Args:
            P:
                Первая точка

            Q:
                Вторая точка

        Returns:
            P + Q
        """

        # O + Q = Q
        if P is self.O:
            return Q

        # P + O = P
        if Q is self.O:
            return P
        
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


    @staticmethod
    def inv(x, p) -> int:
        return pow(x, -1, p)
        

if __name__ == "__main__":
    E = Ellipic(p=13, a=4, b=6, q=7, P=(-2, 4))
    Q = E.calculate_new_point(P=(-2, -4), n=2)
    print(Q)