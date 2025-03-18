num = float(input("Введите вещественное число: "))
a = []
for i in range(1, 11):
    mult = num * i
    a.append(round(mult, 2))
print(a)