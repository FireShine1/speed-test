#!/usr/bin/env python3
"""Замер скорости скачивания: N последовательных запросов к одному URL.

Использует только стандартную библиотеку Python (3.9+).
"""

import argparse
import sys
import time
import urllib.error
import urllib.request

CHUNK_SIZE = 64 * 1024  # читаем ответ кусками по 64 КиБ
USER_AGENT = "internet-speed-test/1.0"


def fetch(url: str, timeout: float) -> tuple[int, float]:
    """Скачивает url целиком. Возвращает (кол-во байт, время в секундах)."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            # Просим не отдавать закэшированную копию из промежуточных прокси.
            "Cache-Control": "no-cache",
            # Без сжатия: считаем реальные байты, пришедшие по сети.
            "Accept-Encoding": "identity",
        },
    )
    size = 0
    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
    elapsed = time.perf_counter() - start
    return size, elapsed


def format_bytes(num: float) -> str:
    """Человекочитаемый размер в десятичных единицах (1 МБ = 1 000 000 байт)."""
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if num < 1000:
            return f"{num:.2f} {unit}"
        num /= 1000
    return f"{num:.2f} ТБ"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Замер скорости скачивания по указанному URL."
    )
    parser.add_argument("url", help="адрес файла для скачивания (http/https)")
    parser.add_argument(
        "-n", "--count", type=int, default=10,
        help="количество последовательных запросов (по умолчанию 10)",
    )
    parser.add_argument(
        "-t", "--timeout", type=float, default=30.0,
        help="таймаут сокета в секундах (по умолчанию 30)",
    )
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count должен быть >= 1")
    if not args.url.startswith(("http://", "https://")):
        parser.error("URL должен начинаться с http:// или https://")
    return args


def main() -> int:
    args = parse_args()
    print(f"URL: {args.url}")
    print(f"Запросов: {args.count}\n")

    sizes: list[int] = []
    times: list[float] = []

    for i in range(1, args.count + 1):
        try:
            size, elapsed = fetch(args.url, args.timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            # HTTPError — подкласс URLError, сюда же попадают 404/500.
            print(f"[{i:>2}/{args.count}] ошибка: {exc}", file=sys.stderr)
            continue
        sizes.append(size)
        times.append(elapsed)
        speed = size * 8 / elapsed / 1_000_000 if elapsed > 0 else 0.0
        print(f"[{i:>2}/{args.count}] {format_bytes(size):>12}  "
              f"{elapsed:7.3f} с  {speed:8.2f} Мбит/с")

    if not times:
        print("\nНи один запрос не завершился успешно.", file=sys.stderr)
        return 1

    total_bytes = sum(sizes)
    total_time = sum(times)
    avg_time = total_time / len(times)
    # Средняя скорость = весь объём / всё время скачивания
    # (а не среднее арифметическое скоростей отдельных запросов).
    speed_mbit = total_bytes * 8 / total_time / 1_000_000
    speed_mbyte = total_bytes / total_time / 1_000_000

    print("\nИтого:")
    print(f"  Успешных запросов:     {len(times)} из {args.count}")
    print(f"  Среднее время запроса: {avg_time:.3f} с")
    print(f"  Всего скачано:         {format_bytes(total_bytes)} ({total_bytes} байт)")
    print(f"  Скорость скачивания:   {speed_mbit:.2f} Мбит/с ({speed_mbyte:.2f} МБ/с)")
    return 0 if len(times) == args.count else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nПрервано пользователем.", file=sys.stderr)
        sys.exit(130)
