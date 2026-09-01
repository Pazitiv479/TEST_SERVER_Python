import asyncio
import json
import websockets
import threading

# --- Глобальное состояние сервера ---
connected_clients = set()

next_message_id = 1
next_object_id = 1

# Глобальная ссылка на цикл событий asyncio (чтобы отправлять сообщения из потока меню)
main_loop = None

# --- Вспомогательные функции ---


async def broadcast(message: str):
    """Аналог BroadcastTextToAll из C++. Отправляет сообщение всем клиентам."""
    if not connected_clients:
        return 0

    tasks = []
    for client in connected_clients:
        tasks.append(client.send(message))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    sent_count = 0
    for result in results:
        if not isinstance(result, Exception):
            sent_count += 1

    return sent_count


def make_indexed_command(msg_id: int, inner_payload: dict) -> str:
    """Формирует JSON: {"id": msg_id, "data": inner_payload}"""
    command = {"id": msg_id, "data": inner_payload}
    return json.dumps(command)


def build_inner_command(name: str, data: dict) -> dict:
    """Формирует внутреннюю структуру команды."""
    return {"name": name, "data": data}


# --- Обработчик подключений ---


async def handler(websocket):
    """Обработчик нового WebSocket-соединения."""
    connected_clients.add(websocket)
    print(
        f"\n[ws] Новый клиент подключился. Текущее число клиентов: {len(connected_clients)}"
    )

    try:
        async for message in websocket:
            print(f"\n[ws recv] Сообщение от клиента: {message}")

            # Парсим сообщение от клиента
            try:
                outer = json.loads(message)
                # Внешняя структура: { id, isResult, data (строка JSON) }
                inner = (
                    json.loads(outer.get("data", "{}"))
                    if isinstance(outer.get("data"), str)
                    else outer.get("data", {})
                )

                cmd_name = inner.get("name")
                cmd_data = inner.get("data", {})

                if cmd_name == "click":
                    obj_id = cmd_data.get("id")
                    print(f"  → Клиент кликнул по объекту с ID={obj_id}")

                    # ТУТ БУДЕТ ВАША ЛОГИКА МАРС
                    # Например:
                    # if obj_id == 5:  # ID источника питания
                    #     # увеличить напряжение
                    #     # отправить update для источника и для стрелки вольтметра
                    #     pass

                else:
                    print(f"  → Получена команда: {cmd_name}, данные: {cmd_data}")

            except Exception as e:
                print(f"  → Ошибка парсинга: {e}")
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"\n[ws] Исключение: {e}")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        print(f"\n[ws] Клиент отключился. Осталось клиентов: {len(connected_clients)}")


# --- Меню консоли (в отдельном потоке) ---


def console_menu_thread(loop):
    """Синхронный цикл меню, работающий в отдельном потоке."""
    global next_message_id, next_object_id

    while True:
        print("\n=== Меню команд ===")
        print("1) Создать объект")
        print("2) Обновить объект")
        print("3) Показать число подключённых клиентов")
        print("4) Генерация терреина")
        print("5) Сгенерировать шестерёнку")
        print("0) Выход")

        choice = input("Выберите пункт (0-3): ")

        if choice == "0":
            print("Выход. Остановка сервера...")
            # Останавливаем асинхронный цикл, что приведёт к завершению программы
            loop.call_soon_threadsafe(loop.stop)
            break

        elif choice == "1":
            obj_type = (
                input("Введите тип объекта (cube, sphere, cone, cylinder, torus): ")
                or "cube"
            )
            try:
                px = int(input("Позиция X: ") or "0")
                py = int(input("Позиция Y: ") or "0")
                pz = int(input("Позиция Z: ") or "0")
                sx = int(input("Масштаб X: ") or "1")
                sy = int(input("Масштаб Y: ") or "1")
                sz = int(input("Масштаб Z: ") or "1")
                cr = int(input("Цвет R (0-255): ") or "128")
                cg = int(input("Цвет G (0-255): ") or "128")
                cb = int(input("Цвет B (0-255): ") or "128")
            except ValueError:
                print("Ошибка ввода! Введите числа.")
                continue

            current_obj_id = next_object_id
            next_object_id += 1

            create_data = {
                "id": current_obj_id,
                "object_type": obj_type,
                "position": [px, py, pz],
                "scale": [sx, sy, sz],
                "color": [cr, cg, cb],
            }

            inner = build_inner_command("create", create_data)
            current_msg_id = next_message_id
            next_message_id += 1
            final_message = make_indexed_command(current_msg_id, inner)

            print(f"Отправляем: {final_message}")

            # Отправляем сообщение через event loop главного потока
            asyncio.run_coroutine_threadsafe(broadcast(final_message), loop)

        elif choice == "2":
            try:
                obj_id = int(input("Введите id объекта для обновления: "))
                px = int(input("Позиция X: ") or "0")
                py = int(input("Позиция Y: ") or "0")
                pz = int(input("Позиция Z: ") or "0")
            except ValueError:
                print("Ошибка ввода!")
                continue

            update_data = {"id": obj_id, "position": [px, py, pz]}

            inner = build_inner_command("update", update_data)
            current_msg_id = next_message_id
            next_message_id += 1
            final_message = make_indexed_command(current_msg_id, inner)

            print(f"Отправляем: {final_message}")
            asyncio.run_coroutine_threadsafe(broadcast(final_message), loop)

        elif choice == "3":
            print(f"Подключено клиентов: {len(connected_clients)}")

        elif choice == "4":
            # Процедурная генерация ландшафта
            try:
                size_x = int(input("Размер по X (например 20): ") or "20")
                size_z = int(input("Размер по Z (например 20): ") or "20")
                px = int(input("Позиция X: ") or "0")
                py = int(input("Позиция Y: ") or "0")
                pz = int(input("Позиция Z: ") or "0")
            except ValueError:
                print("Ошибка ввода!")
                continue

            current_obj_id = next_object_id
            next_object_id += 1

            create_data = {
                "id": current_obj_id,
                "object_type": "terrain",  # <--- Новый тип объекта
                "position": [px, py, pz],
                "geometry": [size_x, size_z, 0],  # Передадим размеры
                "scale": [1, 1, 1],
                "color": [128, 128, 128],
            }

            inner = build_inner_command("create", create_data)
            current_msg_id = next_message_id
            next_message_id += 1
            final_message = make_indexed_command(current_msg_id, inner)

            print(f"Отправляем: {final_message}")
            asyncio.run_coroutine_threadsafe(broadcast(final_message), loop)

        elif choice == "5":
            # Процедурная генерация шестерёнки
            try:
                radius = int(input("Радиус шестерёнки (например 2): ") or "2")
                teeth = int(input("Количество зубьев (например 12): ") or "12")
                thickness = int(input("Толщина (например 1): ") or "1")
                px = int(input("Позиция X: ") or "0")
                py = int(input("Позиция Y: ") or "0")
                pz = int(input("Позиция Z: ") or "0")
            except ValueError:
                print("Ошибка ввода!")
                continue

            current_obj_id = next_object_id
            next_object_id += 1

            create_data = {
                "id": current_obj_id,
                "object_type": "gear",  # <--- Новый тип
                "position": [px, py, pz],
                # Передаем параметры: [радиус, толщина, кол-во зубьев]
                "geometry": [radius, thickness, teeth],
                "scale": [1, 1, 1],
                "color": [150, 150, 150],  # Серый металлический цвет
            }

            inner = build_inner_command("create", create_data)
            current_msg_id = next_message_id
            next_message_id += 1
            final_message = make_indexed_command(current_msg_id, inner)

            print(f"Отправляем: {final_message}")
            asyncio.run_coroutine_threadsafe(broadcast(final_message), loop)

        else:
            print("Пункт меню не распознан, повторите.")


# --- Точка входа ---


async def main():
    """Запускает WebSocket сервер и меню консоли."""
    global main_loop
    main_loop = asyncio.get_running_loop()

    port = 5001

    # Используем 127.0.0.1 вместо localhost во избежание проблем с IPv6
    server = await websockets.serve(handler, "127.0.0.1", port)

    print(f"WebSocket сервер запущен и слушает порт {port}")
    print(f"Подключите клиент к ws://127.0.0.1:{port}")
    print("После подключения вы сможете отправлять команды через эту консоль.\n")

    # Запускаем меню в отдельном потоке (daemon=True означает, что поток умрёт вместе с программой)
    menu_thread = threading.Thread(
        target=console_menu_thread, args=(main_loop,), daemon=True
    )
    menu_thread.start()

    try:
        # Бесконечный цикл ожидания, пока меню не остановит loop
        await asyncio.Future()
    except asyncio.CancelledError:
        pass
    finally:
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nСервер принудительно остановлен.")
