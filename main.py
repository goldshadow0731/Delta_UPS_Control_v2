# -*- coding: utf8 -*-
import json
import os
import socket

from apscheduler.schedulers.blocking import BlockingScheduler
from paho.mqtt import publish
from dotenv import load_dotenv

from ups import DeltaUPS


load_dotenv(f"{os.path.dirname(os.path.abspath(__name__))}/.env")

# UPS
deltaups = DeltaUPS(os.environ.get("SERIAL_PORT"),
                    baudrate=2400, timeout=1)


def publish_ups_data():
    send_data = {
        "temp": None,
        "input": dict.fromkeys(["line", "freq", "volt"]),
        "output": dict.fromkeys(
            ["mode", "freq", "line", "volt", "amp", "watt", "percent"]),
        "battery": {
            "status": dict.fromkeys(
                ["health", "status", "chargeMode", "volt", "remainPercent"]),
            "lastChange": dict.fromkeys(["year", "month", "day"]),
            "nextChange": dict.fromkeys(["year", "month", "day"])
        }
    }

    # --> Input Status
    line, freq, volt = deltaups.input_status
    send_data["input"].update({
        "line": line,
        "freq": freq,
        "volt": volt
    })

    # --> Output Status
    mode, freq, line, volt, amp, watt, percent = deltaups.output_status
    send_data["output"].update({
        "mode": [
            "Normal (市電輸入)",
            "Battery (電池轉換)",
            "Bypass(3phase Reserve Power Path)",
            "Reducing",
            "Boosting",
            "Manual Bypass (手動屏蔽)",
            "Other (其他)",
            "No output (無輸出)"
        ][mode],
        "freq": freq,
        "line": line,
        "volt": volt,
        "amp": amp if amp else round(watt / volt, 3),
        "watt": round(watt / 1000, 3),
        "percent": percent
    })

    # --> Battery Status
    condition, status, charge, _, _, _, volt, _, temp, level = deltaups.battery_status
    send_data["temp"] = temp
    send_data["battery"]["status"].update({
        "health": ["Good (良好)", "Weak (虛弱)", "Replace (需更換)"][condition],
        "status": ["OK (良好)", "Low (低電量)", "Depleted (耗盡)"][status],
        "chargeMode": [
            "Floating charging (微量充電)",
            "Boost charging (快速充電)",
            "Resting (休眠)",
            "Discharging (未充電)"
        ][charge],
        "volt": volt,
        "remainPercent": level
    })

    # --> Battery Replacement Date
    last_date, next_date = deltaups.battery_replacement_date
    send_data["battery"].update({
        "lastChange": {
            "year": last_date.year if last_date else None,
            "month": last_date.month if last_date else None,
            "day": last_date.day if last_date else None,
        },
        "nextChange": {
            "year": next_date.year if next_date else None,
            "month": next_date.month if next_date else None,
            "day": next_date.day if next_date else None,
        }
    })

    publish.single(
        f"UPS/{os.environ.get('DEVICE_NUMBER')}/Monitor",
        json.dumps(send_data),
        hostname=os.environ.get("MQTT_IP"),
        port=int(os.environ.get("MQTT_PORT"))
    )


if __name__ == "__main__":
    # set cron job
    scheduler = BlockingScheduler()
    scheduler.add_job(publish_ups_data, "interval", seconds=5)
    scheduler.start()
