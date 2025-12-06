import sys
import re
import yaml
import argparse


def mask(n):
    """Создает битовую маску из n единиц. Например, mask(3) вернет 0b111 (7)"""
    return (1 << n) - 1


def assemble_load(const):
    """Формирование команды загрузки константы (A=180, 3 байта)
    Биты 0-7: A=180 (0xB4)
    Биты 8-18: константа (11 бит)
    Результат: новое значение на стеке
    """
    cmd = 180 | ((const & mask(11)) << 8)  # Применяем маску для 11 бит и сдвигаем
    return cmd.to_bytes(3, 'little')  # Преобразуем в 3 байта


def assemble_read(addr):
    """Формирование команды чтения из памяти (A=172, 5 байт)
    Биты 0-7: A=172 (0xAC)
    Биты 8-35: адрес (28 бит)
    Результат: новое значение на стеке
    """
    cmd = 172 | ((addr & mask(28)) << 8)  # Применяем маску для 28 бит и сдвигаем
    return cmd.to_bytes(5, 'little')  # Преобразуем в 5 байт


def assemble_write():
    """Формирование команды записи в память (A=61, 1 байт)
    Биты 0-7: A=61 (0x3D)
    Адрес и значение берутся со стека
    """
    cmd = 61  # Код операции
    return cmd.to_bytes(1, 'little')  # Преобразуем в 1 байт


def assemble_rol():
    """Формирование команды побитового циклического сдвига влево (A=249, 1 байт)
    Биты 0-7: A=249 (0xF9)
    Значение для сдвига и количество бит берутся со стека
    """
    cmd = 249  # Код операции
    return cmd.to_bytes(1, 'little')  # Преобразуем в 1 байт


def assemble(program):
    """Ассемблирование программы в машинный код
    Принимает промежуточное представление программы и возвращает байт-код
    """
    bytecode = b""
    # Обрабатываем каждую команду из промежуточного представления
    for cmd in program:
        if cmd['op'] == 'load':
            bytecode += assemble_load(cmd['const'])  # Формируем команду загрузки константы
        elif cmd['op'] == 'read':
            bytecode += assemble_read(cmd['addr'])  # Формируем команду чтения из памяти
        elif cmd['op'] == 'write':
            bytecode += assemble_write()  # Формируем команду записи в память
        elif cmd['op'] == 'rol':
            bytecode += assemble_rol()  # Формируем команду циклического сдвига
    return bytecode  # Возвращаем итоговый байт-код


def test_assembler():
    """Функция для юнит-тестирования генерации байт-кода"""
    assert list(assemble_load(684)) == [0xB4, 0xAC, 0x02], "Ошибка в команде load(684)"

    assert list(assemble_read(783)) == [0xAC, 0x0F, 0x03, 0x00, 0x00], "Ошибка в команде read(783)"

    assert list(assemble_write()) == [0x3D], "Ошибка в команде write()"

    assert list(assemble_rol()) == [0xF9], "Ошибка в команде rol()"

    print("Success")


# Модифицированная функция main() для запуска тестов
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', nargs='?', help='Input assembly file (YAML format)')
    parser.add_argument('output', nargs='?', help='Output binary file')
    parser.add_argument('--test', action='store_true', help='Show intermediate representation and bytecode')
    parser.add_argument('--run-tests', action='store_true', help='Run built-in unit tests')
    args = parser.parse_args()

    # Запуск юнит-тестов вместо основной логики
    if args.run_tests:
        test_assembler()
        return

    # Проверка обязательных аргументов при отсутствии флага тестов
    if not args.input or not args.output:
        parser.error("INPUT and OUTPUT files are required unless --run-tests is specified")

    # Чтение исходного файла
    try:
        with open(args.input, 'r') as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"Error parsing YAML: {e}")
                return
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found")
        return  # Выход при ошибке

    # Проверка структуры YAML
    if not isinstance(data, dict) or 'program' not in data:
        print("Error: YAML must contain a 'program' key at top level")
        return

    program_yaml = data['program']
    if not isinstance(program_yaml, list):
        print("Error: 'program' must be a list of commands")
        return

    # Конвертация YAML в промежуточное представление
    program = []
    for idx, cmd in enumerate(program_yaml):
        if not isinstance(cmd, dict):
            print(f"Error at command {idx}: command must be a dictionary")
            return

        op = cmd.get('op')
        if op is None:
            print(f"Error at command {idx}: missing 'op' field")
            return

        try:
            if op == 'load':
                if 'arg' not in cmd:
                    print(f"Error at command {idx}: 'load' requires 'arg' field")
                    return
                program.append({'op': 'load', 'const': int(cmd['arg'])})
            elif op == 'read':
                if 'arg' not in cmd:
                    print(f"Error at command {idx}: 'read' requires 'arg' field")
                    return
                program.append({'op': 'read', 'addr': int(cmd['arg'])})
            elif op == 'write':
                program.append({'op': 'write'})
            elif op == 'rol':
                program.append({'op': 'rol'})
            else:
                print(f"Error at command {idx}: unsupported operation '{op}'")
                return
        except (TypeError, ValueError) as e:
            print(f"Error at command {idx}: invalid argument value - {e}")
            return

    # Если включен тестовый режим, выводим промежуточное представление
    if args.test:
        print("Intermediate representation:")
        for cmd in program:
            print(cmd)

    # Сборка в машинный код
    bytecode = assemble(program)

    # Сохранение результата в выходной файл
    with open(args.output, 'wb') as f:
        f.write(bytecode)

    # Вывод статистики
    print(f"Assembled {len(program)} commands")
    print(f"Output file size: {len(bytecode)} bytes")

    # Если включен тестовый режим, выводим байт-код в шестнадцатеричном формате
    if args.test:
        print("\nBytecode (hex):")
        for i in range(0, len(bytecode), 16):  # Выводим по 16 байт в строке
            chunk = bytecode[i:i + 16]
            hex_values = ' '.join([f'0x{b:02X}' for b in chunk])  # Форматируем в hex
            print(f'{i:04X}: {hex_values}')  # Выводим с адресом в формате 0000:


# Точка входа в программу
if __name__ == '__main__':
    main()