# Объявление для случаев некорректных сторон треугольника
class IncorrectTriangleSides(Exception):
    pass

# Функция для определения типа треугольника на основе длин его сторон
def get_triangle_type(a, b, c):
    # Проверка на положительность всех сторон треугольника
    if a <= 0 or b <= 0 or c <= 0:
        # Если хотя бы одна сторона отрицательная или равна нулю, то генерируется исключение
        raise IncorrectTriangleSides("Side lengths must be positive")
    # Проверка: сумма двух сторон должна быть больше третьей стороны
    if a + b <= c or a + c <= b or b + c <= a:
        # Если неравенство нарушено, то генерируется исключение
        raise IncorrectTriangleSides("Invalid side lengths for a triangle")
    # Проверка равносторонности
    if a == b == c:
        return "equilateral"  # Возвращается тип треугольника "равносторонний"
    # Проверка на равнобедренность
    elif a == b or a == c or b == c:
        return "isosceles"  # Возвращается тип треугольника "равнобедренный"
    else:
        return "nonequilateral"  # Возвращается тип треугольника "разносторонний
