from flask import Flask, request, jsonify
import random
import requests

app = Flask(__name__)

# Раздел 1. Подготовка сервера с API.

# 1. GET /number/
# Реализовать GET эндпоинт /number/, который принимает параметр
# запроса – param с числом. Вернуть рандомно сгенерированное
# число, умноженное на значение из параметра в формате JSON.
@app.route('/number/', methods=['GET'])
def get_number():
    param = request.args.get('param', type=float)

    if param is None:
        return jsonify({'error': 'Parameter "param" is required'}), 400

    random_num = random.random()  # Случайное число от 0 до 1
    result = random_num * param

    # Создаем словарь и преобразуем его в JSON-ответ
    return jsonify({
        "random_number": random_num,
        "result": result
    })


# 2. POST /number/
# Реализовать POST эндпоинт /number/, который принимает в теле
# запроса JSON с полем jsonParam. Вернуть сгенерировать рандомно
# число, умноженное на то, что пришло в JSON и рандомно выбрать операцию.
@app.route('/number/', methods=['POST'])
def post_number():
    # Получаем JSON данные из тела запроса
    data = request.get_json()

    # Извлекаем значение параметра jsonParam из JSON
    json_param = data.get('jsonParam')
    json_param = float(json_param)
    random_num = random.random()

    # Выбираем случайную операцию из списка доступных
    operation = random.choice(['+', '-', '*', '/'])

    # Выполняем выбранную операцию между случайным числом и параметром
    if operation == '+':
        result = random_num + json_param
    elif operation == '-':
        result = random_num - json_param
    elif operation == '*':
        result = random_num * json_param
    else:
        result = random_num / json_param

    # Возвращаем результат в формате JSON
    return jsonify({
        "random_number": random_num,
        "operation": operation,
        "result": result
    })


# 3. DELETE /number/
# Реализовать DELETE эндпоинт /number/, в ответе сгенерировать
# число и рандомную операцию.
@app.route('/number/', methods=['DELETE'])
def delete_number():
    random_num = random.random()
    operation = random.choice(['+', '-', '*', '/'])
    return jsonify({
        "random_number": random_num,
        "operation": operation
    })


# Раздел II. Отправка запросов на сервер с API.
def send_requests_to_api():
    base_url = "http://127.0.0.1:5000/number/"

    # 1. GET запрос
    get_param = random.randint(1, 10)
    get_response = requests.get(f"{base_url}/?param={get_param}")
    get_data = get_response.json()
    get_result = get_data['result']
    print(f"GET запрос (param={get_param}):")
    print(f"   Результат: {get_result}")

    # 2. POST запрос
    post_value = random.randint(1, 10)
    post_response = requests.post(
        f"{base_url}/",
        json={"jsonParam": post_value},
        headers={"Content-Type": "application/json"}
    )
    post_data = post_response.json()
    post_result = post_data['result']
    post_op = post_data['operation']
    print(f"\nPOST запрос (jsonParam={post_value}):")
    print(f"   Результат: {post_result}")
    print(f"   Операция: {post_op}")

    # 3. DELETE запрос
    delete_response = requests.delete(f"{base_url}/")
    delete_data = delete_response.json()
    delete_num = delete_data['random_number']
    delete_op = delete_data['operation']
    print(f"\nDELETE запрос:")
    print(f"   Результат: {delete_num}")
    print(f"   Операция: {delete_op}")

    # 4. Вычисления
    # Сначала: GET_result <POST_op> POST_result
    if post_op == '+':
        intermediate = get_result + post_result
    elif post_op == '-':
        intermediate = get_result - post_result
    elif post_op == '*':
        intermediate = get_result * post_result
    elif post_op == '/':
        if post_result == 0:
            print("Ошибка: деление на ноль (POST результат = 0)")
            return
        else:
            intermediate = get_result / post_result

    # Затем: результат <DELETE_op> DELETE_result
    if delete_op == '+':
        total = intermediate + delete_num
    elif delete_op == '-':
        total = intermediate - delete_num
    elif delete_op == '*':
        total = intermediate * delete_num
    elif delete_op == '/':
        if delete_num == 0:
            print("Ошибка: деление на ноль (DELETE число = 0)")
            return
        else:
            total = intermediate / delete_num

    final_result = int(total)

    # Вывод финального выражения
    print("\nИтоговый результат:")
    print(f"   Выражение: ({get_result}) {post_op} "
          f"({post_result}) {delete_op} ({delete_num})")
    print(f"   Результат: {final_result}")


# Раздел III. Отправка запросов на сервер с API.
# curl.exe -X GET http://localhost:5000/number/?param=$((1 + $RANDOM % 10))
# curl.exe -X POST -H "Content-Type: application/json" -d "{\`"jsonParam\`":$((1 + $RANDOM % 10))}" http://localhost:5000/number/
# curl.exe -X DELETE http://localhost:5000/number/

# Запуск приложения
if __name__ == "__main__":
    choice = input(
        "Выберите режим:\n1 - Запустить сервер\n2 - Отправить запросы (клиент)\nВаш выбор: "
    )

    if choice == "1":
        app.run(debug=False)
    elif choice == "2":
        send_requests_to_api()
    else:
        print("Неверный выбор. Введите 1 или 2.")