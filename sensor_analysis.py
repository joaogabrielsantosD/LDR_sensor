import csv
import os
import matplotlib.pyplot as plt
import numpy as np
import statistics as stats
from collections import defaultdict

INPUT_FILE = "logs/data_serial3.csv"
OUTPUT_FILE = "results/duty_result3.txt"

os.makedirs("results", exist_ok=True)

def read_data(file_path):
    """Reads the CSV and returns a list of dictionaries with numeric values."""
    data = []
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)  # skip header

        for row in reader:
            if not row or len(row) < 2:
                continue

            timestamp = row[0]
            # the second field contains duty,led_raw,led_mv,ldr_raw,ldr_mv (+ trailing comma)
            values = row[1].split(",")

            # remove empty strings (caused by the trailing comma at the end)
            values = [v for v in values if v.strip() != ""]

            if len(values) < 5:
                continue  # incomplete row, ignore

            try:
                duty = int(values[0])
                led_raw = float(values[1])
                led_mv = float(values[2])
                ldr_raw = float(values[3])
                ldr_mv = float(values[4])
            except ValueError:
                continue  # row with invalid data, ignore

            data.append({
                "timestamp": timestamp,
                "duty": duty,
                "led_raw": led_raw,
                "led_mv": led_mv,
                "ldr_raw": ldr_raw,
                "ldr_mv": ldr_mv,
            })

    return data


def group_by_duty(data):
    """Groups numeric values by duty."""
    groups = defaultdict(lambda: defaultdict(list))
    for row in data:
        duty = row["duty"]
        for column in ("led_raw", "led_mv", "ldr_raw", "ldr_mv"):
            groups[duty][column].append(row[column])
    return groups


def calculate_statistics(groups):
    """Calculates mean and (sample) standard deviation for each column, grouped by duty."""
    result = []
    for duty in sorted(groups.keys()):
        row = {"duty": duty, "sample_count": len(groups[duty]["led_raw"])}
        # for column in ("led_raw", "led_mv", "ldr_raw", "ldr_mv"):
        for column in ("led_mv", "ldr_mv"):
            values = groups[duty][column]
            mean = stats.mean(values)
            # sample standard deviation (n-1); requires at least 2 values
            std_dev = stats.stdev(values) if len(values) > 1 else 0.0
            row[f"{column}_mean"] = mean
            row[f"{column}_std"] = std_dev
        result.append(row)
    return result


def save_results(result, file_path):
    columns = [
        "duty", "sample_count",
        # "led_raw_mean", "led_raw_std",
        "led_mv_mean", "led_mv_std",
        # "ldr_raw_mean", "ldr_raw_std",
        "ldr_mv_mean", "ldr_mv_std",
    ]
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in result:
            writer.writerow(row)


def display_results(result):
    print(f"{'duty':>5} | {'n':>4} | {'led_raw (m±sd)':>18} | {'led_mv (m±sd)':>16} | "
          f"{'ldr_raw (m±sd)':>18} | {'ldr_mv (m±sd)':>16}")
    print("-" * 90)
    for row in result:
        print(f"{row['duty']:>5} | {row['sample_count']:>4} | "
            #   f"{row['led_raw_mean']:>8.2f}±{row['led_raw_std']:<6.2f} | "
              f"{row['led_mv_mean']:>7.2f}±{row['led_mv_std']:<6.2f} | "
            #   f"{row['ldr_raw_mean']:>8.2f}±{row['ldr_raw_std']:<6.2f} | "
              f"{row['ldr_mv_mean']:>7.2f}±{row['ldr_mv_std']:<6.2f}")


def build_led_volt_values(result):
    v = []
    for row in result:
        v.append((row['led_mv_mean'] / 1000))
    return v


def build_ldr_volt_values(result):
    v = []
    for row in result:
        v.append((row['ldr_mv_mean'] / 1000))
    return v


def plot_voltage_graph(led, ldr):
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(led, ldr, marker='o', linestyle='-', linewidth=2.0, color='b', label='LDR vs LED')

    ax.set_title("LDR Voltage vs LED/PWM Voltage", fontsize=14, fontweight='bold')
    ax.set_xlabel("LED Voltage (V)", fontsize=12)
    ax.set_ylabel("LDR Voltage (V)", fontsize=12)

    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend(loc='best')

    max_x = max(led) if led else 5.0
    max_y = max(ldr) if ldr else 5.0
    ax.set_xlim(0, max(3.3, max_x * 1.1))
    ax.set_ylim(0, max(3.3, max_y * 1.1))

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    data = read_data(INPUT_FILE)
    print(f"Total valid rows read: {len(data)}")

    groups = group_by_duty(data)
    result = calculate_statistics(groups)

    # display_results(result)
    save_results(result, OUTPUT_FILE)
    print(f"\nResults saved to: {OUTPUT_FILE}")

    led_volt = build_led_volt_values(result)
    ldr_volt = build_ldr_volt_values(result)
    # print(led_volt)
    # print(ldr_volt)

    plot_voltage_graph(led_volt, ldr_volt)