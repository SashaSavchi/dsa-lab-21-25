import unittest  #для создания модульных тестов
from triangle_func import get_triangle_type, IncorrectTriangleSides

# Определение класса TestTriangleFunction, наследующегося от unittest.TestCase
class TestTriangleFunction(unittest.TestCase):
    # Метод для тестирования равностороннего треугольника
    def test_equilateral(self):
        # Проверка, что функция возвращает ожидаемый тип треугольника для равных сторон
        self.assertEqual(get_triangle_type(5, 5, 5), "equilateral")

    # Метод для тестирования равнобедренного треугольника
    def test_isosceles(self):
        # Проверка, что функция возвращает ожидаемый тип треугольника для равнобедренного треугольника
        self.assertEqual(get_triangle_type(5, 5, 3), "isosceles")

    # Метод для тестирования разностороннего треугольника
    def test_nonequilateral(self):
        # Проверка, что функция возвращает ожидаемый тип треугольника для разностороннего треугольника
        self.assertEqual(get_triangle_type(3, 4, 5), "nonequilateral")

    # Метод для тестирования некорректной длины стороны
    def test_invalid_side_length(self):
        # Проверка, что функция вызывает исключение для некорректной длины стороны
        with self.assertRaises(IncorrectTriangleSides):
            get_triangle_type(-1, 2, 3)

    # Метод для тестирования некорректного треугольника
    def test_invalid_triangle(self):
        # Проверка, что функция вызывает исключение для некорректного треугольника
        with self.assertRaises(IncorrectTriangleSides):
            get_triangle_type(1, 1, 3)

# Если скрипт запускается напрямую, запускаются все тесты
if __name__ == '__main__':
    unittest.main()
