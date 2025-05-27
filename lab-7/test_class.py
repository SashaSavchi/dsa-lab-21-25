# Импорт класса Triangle и пользовательского исключения IncorrectTriangleSides из модуля triangle_class
from triangle_class import Triangle, IncorrectTriangleSides
# Импорт библиотеки pytest для проведения тестирования
import pytest

# Функция для тестирования создания треугольника с некорректными сторонами
def test_triangle_creation():
    # Проверка, что инициализация треугольника с нулевыми сторонами вызывает исключение
    with pytest.raises(IncorrectTriangleSides):
        Triangle(0, 0, 0)

    # Проверка, что инициализация треугольника с отрицательной стороной вызывает исключение
    with pytest.raises(IncorrectTriangleSides):
        Triangle(-1, 2, 3)

    # Проверка, что инициализация треугольника с некорректными сторонами вызывает исключение
    with pytest.raises(IncorrectTriangleSides):
        Triangle(1, 1, 3)

# Функция для тестирования методов класса Triangle
def test_triangle_methods():
    # Создание экземпляра треугольника с заданными сторонами
    triangle1 = Triangle(3, 4, 5)
    # Проверка, что метод triangle_type возвращает корректный тип треугольника
    assert triangle1.triangle_type() == "nonequilateral"
    # Проверка, что метод perimeter возвращает корректный периметр треугольника
    assert triangle1.perimeter() == 12

    # Создание экземпляра равностороннего треугольника
    triangle2 = Triangle(5, 5, 5)
    # Проверка, что метод triangle_type возвращает корректный тип треугольника
    assert triangle2.triangle_type() == "equilateral"
    # Проверка, что метод perimeter возвращает корректный периметр треугольника
    assert triangle2.perimeter() == 15

    # Создание экземпляра равнобедренного треугольника
    triangle3 = Triangle(7, 7, 10)
    # Проверка, что метод triangle_type возвращает корректный тип треугольника
    assert triangle3.triangle_type() == "isosceles"
    # Проверка, что метод perimeter возвращает корректный периметр треугольника
    assert triangle3.perimeter() == 24

# Проверка, что скрипт запускается напрямую, и запуск всех тестов
if __name__ == "__main__":
    pytest.main()
