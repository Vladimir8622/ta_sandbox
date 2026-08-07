"""
Собирает датасет data/datasets/moex_adjusted_stock/ из сырых CSV в
data/MOEX/adjusted_stock/1d/ (одна цена close на инструмент в день,
без OHLC - источник, okama.io/adjusted_close, ничего кроме close не отдаёт).

Каждый инструмент - отдельный parquet-файл (date, close), не сводная
таблица: датасет сознательно не завязан на формат одной цены, чтобы
завтра расширить до полного OHLCV без пересборки схемы.

Как определяется "инструмент попадает в датасет":
  START_DATE <= первая дата в его истории  И  последняя дата >= END_DATE.
Сам датасет при этом ВСЕГДА обрезается ровно по окну [START_DATE, END_DATE],
даже если у инструмента есть история за его пределами.

Как считаются пропуски (NaN):
  единая сетка дат = объединение уникальных дат ПО ВСЕМ инструментам,
  прошедшим фильтр покрытия, в пределах [START_DATE, END_DATE].
  Т.к. выходные общие для всей биржи, в объединении их в принципе нет -
  остаются только реальные дыры в конкретных инструментах.

Идемпотентность: по умолчанию скрипт ДОБАВЛЯЕТ файлы, которых ещё нет в
датасете, и НЕ ТРОГАЕТ уже существующие. FORCE_REBUILD полностью сносит
папку датасета и пересобирает с нуля - это специально сделано жёстким
переключателем, а не "тихим" поведением, см. предупреждение в конце файла.
"""
import sys
import shutil
from pathlib import Path
from datetime import datetime

import pandas as pd
import yaml

if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(root_dir))


# ============================== ФЛАГИ ==================================

# Окно, которое должен покрывать инструмент, чтобы попасть в датасет.
START_DATE = "2023-08-20"
END_DATE = "2026-07-05"

# True: инструмент обязан покрывать весь [START_DATE, END_DATE] целиком.
# Пока всегда True по смыслу задачи - вынесено в флаг на случай, если
# понадобится другой режим отбора позже.
REQUIRE_FULL_COVERAGE = True

# True: выкинуть из датасета любой инструмент, у которого дата хотя бы
# на один день не совпадает с общей сеткой (объединением дат всех
# инструментов, прошедших фильтр покрытия). Отдельно от REQUIRE_FULL_COVERAGE:
# тот фильтрует по годам покрытия, этот - по дырам внутри уже выбранного окна.
DROP_INSTRUMENTS_WITH_GAPS = False

# True: снести data/datasets/moex_adjusted_stock/ целиком и пересобрать
# заново. False: инструменты, для которых parquet уже лежит в датасете,
# не трогаем - только докидываем недостающие.
FORCE_REBUILD = True

MAX_ALLOWED_NAN_PCT = 5.0   # максимально допустимый процент пропусков (NaN)

SOURCE_DIR = root_dir / "data" / "MOEX" / "adjusted_stock" / "1d"
DATASET_DIR = root_dir / "data" / "datasets" / "moex_adjusted_stock"

# =========================================================================


def check_source_dir(source_dir: Path) -> list[Path]:
    """
    Проверка, что сырые данные реально лежат на месте, прежде чем строить
    из них датасет - чтобы не собрать "датасет" из трёх файлов молча.
    """
    if not source_dir.exists():
        raise FileNotFoundError(
            f"Папка с сырыми данными не найдена: {source_dir}. "
            f"Сначала запустите загрузчик."
        )

    csv_files = sorted(source_dir.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"В {source_dir} нет ни одного .csv файла. Датасет строить не из чего."
        )

    print(f"[source] найдено {len(csv_files)} csv-файлов в {source_dir}")
    return csv_files


def load_and_clean_csv(path: Path) -> pd.DataFrame:
    """
    Читает один сырой CSV (колонки begin,close), минимально чистит:
    сортировка по дате, дедуп дублирующихся дат (последнее значение
    выигрывает - предполагаем, что оно точнее), отбрасывание строк с
    нечитаемой датой или ценой. Это дешёвая страховка от кривого ответа
    API, а не полноценная валидация данных - тяжёлую чистку (согласование
    OHLC и т.п.) есть смысл делать, когда появится реальный OHLCV.
    """
    df = pd.read_csv(path)
    df['begin'] = pd.to_datetime(df['begin'], errors='coerce')
    df['close'] = pd.to_numeric(df['close'], errors='coerce')

    before = len(df)
    df = df.dropna(subset=['begin', 'close'])
    df = df.drop_duplicates(subset='begin', keep='last')
    df = df.sort_values('begin').reset_index(drop=True)
    dropped = before - len(df)

    if dropped:
        print(f"[clean] {path.stem}: отброшено {dropped} битых/дублирующихся строк из {before}")

    return df


def covers_window(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> bool:
    if df.empty:
        return False
    return df['begin'].iloc[0] <= start and df['begin'].iloc[-1] >= end


def slice_to_window(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    mask = (df['begin'] >= start) & (df['begin'] <= end)
    return df.loc[mask].reset_index(drop=True)


def max_consecutive_gap(missing_positions: list[int]) -> int:
    """
    Наибольшее число ПОДРЯД идущих пропущенных точек на общей сетке дат
    (не календарных дней - именно шагов сетки, выходных в сетке и так нет).
    """
    if not missing_positions:
        return 0
    longest = current = 1
    for prev, curr in zip(missing_positions, missing_positions[1:]):
        if curr == prev + 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def build_dataset():
    start = pd.Timestamp(START_DATE)
    end = pd.Timestamp(END_DATE)

    csv_files = check_source_dir(SOURCE_DIR)

    if FORCE_REBUILD and DATASET_DIR.exists():
        print(f"[force] сношу {DATASET_DIR} и пересобираю с нуля")
        shutil.rmtree(DATASET_DIR)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    # --- шаг 1: читаем всё, фильтруем по покрытию окна ---
    covered = {}      # symbol -> DataFrame, обрезанный до окна
    dropped_coverage = []

    for path in csv_files:
        symbol = path.stem
        df = load_and_clean_csv(path)

        if REQUIRE_FULL_COVERAGE and not covers_window(df, start, end):
            dropped_coverage.append(symbol)
            continue

        covered[symbol] = slice_to_window(df, start, end)

    print(f"[coverage] прошли фильтр покрытия: {len(covered)} из {len(csv_files)}")
    if dropped_coverage:
        print(f"[coverage] выкинуто по покрытию: {len(dropped_coverage)} "
              f"(нет данных на весь диапазон {START_DATE}..{END_DATE})")

    if not covered:
        raise RuntimeError(
            f"Ни один инструмент не покрывает окно {START_DATE}..{END_DATE}. "
            f"Датасет строить не из чего - проверьте флаги или сырые данные."
        )

    # --- шаг 2: единая сетка дат = объединение дат всех, кто прошёл покрытие ---
    all_dates = sorted(set().union(*[set(df['begin']) for df in covered.values()]))
    grid = pd.Index(all_dates)
    print(f"[grid] общая сетка дат: {len(grid)} точек, "
          f"{grid.min().date()} .. {grid.max().date()}")

    # --- шаг 3: считаем NaN относительно сетки, опционально режем по дырам ---
    stats = {}
    for symbol, df in covered.items():
        own_dates = set(df['begin'])
        missing_mask = [d not in own_dates for d in grid]
        missing_positions = [i for i, m in enumerate(missing_mask) if m]

        nan_count = len(missing_positions)
        stats[symbol] = {
            'nan_count': nan_count,
            'nan_pct': round(100 * nan_count / len(grid), 3),
            'max_gap_grid_steps': max_consecutive_gap(missing_positions),
        }

    if MAX_ALLOWED_NAN_PCT < 100:
        before = set(covered)
        covered = {s: df for s, df in covered.items() if stats[s]['nan_pct'] <= MAX_ALLOWED_NAN_PCT}
        dropped_by_nan = before - set(covered)
        if dropped_by_nan:
            print(f"[nan_filter] выкинуто по проценту NaN (> {MAX_ALLOWED_NAN_PCT}%): {len(dropped_by_nan)}")
        if not covered:
            raise RuntimeError(f"После фильтрации по NaN не осталось инструментов — слишком строгий порог {MAX_ALLOWED_NAN_PCT}%")

    if DROP_INSTRUMENTS_WITH_GAPS:
        before = set(covered)
        covered = {s: df for s, df in covered.items() if stats[s]['nan_count'] == 0}

        if not covered:
            raise RuntimeError(
                "DROP_INSTRUMENTS_WITH_GAPS=True выкинул ВСЕ инструменты без "
                "исключения - похоже на слишком строгий фильтр, а не на "
                "реальное отсутствие данных. Прогон остановлен, датасет не собран."
            )

        dropped_gaps = before - set(covered)
        if dropped_gaps:
            print(f"[gaps] выкинуто по дырам относительно сетки: {len(dropped_gaps)}")

    # --- шаг 4: пишем parquet, уважая идемпотентность ---
    written, skipped = [], []
    for symbol, df in covered.items():
        out_path = DATASET_DIR / f"{symbol}.parquet"

        if out_path.exists() and not FORCE_REBUILD:
            skipped.append(symbol)
            continue

        out_df = df.rename(columns={'begin': 'date'})[['date', 'close']]
        out_df.to_parquet(out_path, index=False)
        written.append(symbol)

    print(f"[write] записано: {len(written)}, пропущено (уже было): {len(skipped)}")

    # --- шаг 5: description.txt ---
    final_symbols = sorted(covered.keys())
    avg_nan_pct = sum(stats[s]['nan_pct'] for s in final_symbols) / len(final_symbols)
    max_nan_pct_symbol = max(final_symbols, key=lambda s: stats[s]['nan_pct'])
    max_gap_symbol = max(final_symbols, key=lambda s: stats[s]['max_gap_grid_steps'])

    description = f"""moex_adjusted_stock
Собран: {datetime.now().isoformat(timespec='seconds')}

Источник: okama.io, adjusted_close, дневные данные. ВНИМАНИЕ: в источнике
есть только close, ни open/high/low/volume в датасете нет и быть не может -
это ограничение источника, а не забытая колонка.

Окно датасета: {START_DATE} .. {END_DATE}
Инструментов в датасете: {len(final_symbols)}
Инструментов не прошло фильтр покрытия окна: {len(dropped_coverage)}
Флаги сборки: REQUIRE_FULL_COVERAGE={REQUIRE_FULL_COVERAGE}, \
DROP_INSTRUMENTS_WITH_GAPS={DROP_INSTRUMENTS_WITH_GAPS}, FORCE_REBUILD={FORCE_REBUILD}

Общая сетка дат: {len(grid)} точек ({grid.min().date()} .. {grid.max().date()}),
построена как объединение торговых дат всех инструментов, прошедших фильтр
покрытия. Выходные в сетке отсутствуют сами по себе (никто не торгует по
выходным), так что оставшиеся пропуски - это реальные дыры в конкретных
инструментах, а не биржевые нерабочие дни.

Пропуски (NaN) относительно общей сетки:
  средний % пропусков по инструментам: {avg_nan_pct:.3f}%
  больше всего пропусков: {max_nan_pct_symbol} ({stats[max_nan_pct_symbol]['nan_pct']}%)
  самая длинная непрерывная дыра (в шагах сетки): {max_gap_symbol} \
({stats[max_gap_symbol]['max_gap_grid_steps']} точек подряд)

Полная статистика по каждому инструменту - в config.yaml.
"""
    (DATASET_DIR / "description.txt").write_text(description, encoding='utf-8')

    # --- шаг 6: config.yaml ---
    config = {
        'name': 'moex_adjusted_stock',
        'built_at': datetime.now().isoformat(timespec='seconds'),
        'window': {'start': START_DATE, 'end': END_DATE},
        'flags': {
            'require_full_coverage': REQUIRE_FULL_COVERAGE,
            'drop_instruments_with_gaps': DROP_INSTRUMENTS_WITH_GAPS,
            'force_rebuild': FORCE_REBUILD,
        },
        'instrument_count': len(final_symbols),
        'instruments': {
            symbol: {
                'nan_count': stats[symbol]['nan_count'],
                'nan_pct': stats[symbol]['nan_pct'],
                'max_gap_grid_steps': stats[symbol]['max_gap_grid_steps'],
            }
            for symbol in final_symbols
        },
    }
    with open(DATASET_DIR / "config.yaml", 'w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

    print(f"[done] датасет собран в {DATASET_DIR}")

    if not FORCE_REBUILD and skipped:
        print(
            "[warning] часть инструментов не перезаписана (уже были в датасете). "
            "Если с прошлого прогона поменялись флаги (например, "
            "DROP_INSTRUMENTS_WITH_GAPS) - датасет сейчас смесь старой и новой "
            "логики отбора. Если нужна гарантированная консистентность "
            "относительно текущих флагов - запустите с FORCE_REBUILD=True."
        )


if __name__ == "__main__":
    build_dataset()