a = float(input("Введите первое число: "))
b = float(input("Введите второе число: "))
c = float(input("Введите третье число: "))
print("В интервале от 0 до 50:")
for i in (a, b, c):
    if 0 < i < 51:
        print(i)
    