import sys

#Считываем массив из параметров командной строки, начиная с индекса 1
array = [int(arg) for arg in sys.argv[1:]]

#Поиск повторяющихся элементов
repeats = []
seen = set()
for num in array:
    if num in seen:
        repeats.append(num)
    else:
        seen.add(num)

# Выводим результат
if repeats:
    print("Повторяющиеся элементы:", repeats)
else:
    print("Повторяющиеся элементы отсутствуют.")

#Преобразование массива
transformed_array = []
for num in array:
    if num < 10:
        transformed_array.append(0)
    elif num > 20:
        transformed_array.append(1)
    else:
        transformed_array.append(num)

#Вывод исходного и преобразованного массивов
print("Исходный массив:", " ".join(map(str, array)))
print("Преобразованный массив:", " ".join(map(str, transformed_array)))