# -*- coding: utf8 -*-
import datetime
import re
from typing import List, Union

from serial import Serial, SerialException


class DeltaUPS():
    """
        UPS Product page
        https://www.deltapowersolutions.com/zh-tw/mcis/6kva-12kva-single-phase-ups-n-series-old-model.php

        UPS user manual
        https://www.deltapowersolutions.com/media/download/Manual-UPS-N-6-12kVA-leo-zh-tw.pdf
    """

    """
        Request / Respone Data
        +--------+--------+--------+--------+---------------+-----------------------+
        | Header |   ID   |  Type  | Length |     Data      | Checksum (not used ?) |
        +--------+--------+--------+--------+---------------+-----------------------+
        | 1 byte | 2 byte | 1 byte | 3 byte | 128 bytes max |        2 byte         |
        +--------+--------+--------+--------+---------------+-----------------------+
    """

    def __init__(self, port: int, *args, **kwargs) -> None:
        self.serial = Serial(*args, **kwargs)
        self.serial.port = port

    def receive_data(self) -> Union[str, None]:
        read_data = None
        try:
            with self.serial as ser:
                # decode
                read_data = ser.read(137).decode("ASCII")
        except SerialException:
            # TODO: handle SerialException
            pass
        finally:
            return read_data

    def send_data(self, data: str) -> None:
        try:
            with self.serial as ser:
                ser.write((f"~00P{len(data):03d}" + data).encode("ASCII"))
        except SerialException:
            # TODO: handle SerialException
            pass

    @staticmethod
    def parse_result_data(pattern: str, data: str) -> List[Union[int, None]]:
        if data is None:
            return [None for _ in pattern.split(";")]
        else:
            return [int(iter_data) if iter_data != "" else None for iter_data in re.search(pattern, data).group().split(";")]

    @property
    def input_status(self) -> List[Union[int, float, None]]:
        """
            <input_line>;<input_frequency>;<input_voltage>

            e.g. '1;600;2190'
        """
        self.send_data("STI")
        line, freq, volt = self.parse_result_data(
            r"\d{0,1};\d{0,3};\d{0,4}", self.receive_data())
        return line, freq / 10 if freq else None, volt / 10 if volt else None

    @property
    def output_status(self) -> List[Union[int, float, None]]:
        """
            <output_mode>;<output_frequency>;<output_line>;<output_voltage>;<output_ampere>;<output_watt>;<output_percent>

            e.g. '0;600;1;2210;;03169;037'
        """
        self.send_data("STO")
        mode, freq, line, volt, amp, watt, percent = self.parse_result_data(
            r"\d{0,1};\d{0,3};\d{0,1};\d{0,4};\d{0,5};\d{0,6};\d{0,3}", self.receive_data())
        return mode, freq / 10 if freq else None, line, volt / 10 if volt else None, amp / 10 if amp else None, watt, percent

    @property
    def battery_status(self) -> List[Union[int, float, None]]:
        """
            <battery_condition>;<battery_status>;<battery_charge>;<seconds_on_battery>;<estimated_minutes_remaining>;<estimated_charge_remaining>;<battery_voltage>;<battery_ampere>;<internal_temperature>;<battery_level>

            e.g. '0;0;1;;;000;2720;;031;100'
        """
        self.send_data("STB")
        condition, status, charge, seconds, estimated_minutes, estimated_charge, volt, amp, temp, level = self.parse_result_data(
            r"\d{0,1};\d{0,1};\d{0,1};\d{0,5};\d{0,4};\d{0,3};\d{0,4};\d{0,4};\d{0,3};\d{0,3}", self.receive_data())
        return condition, status, charge, seconds, estimated_minutes, estimated_charge, volt / 10 if volt else None, amp / 10 if amp else None, temp, level

    @property
    def battery_replacement_date(self) -> List[Union[datetime.date, None]]:
        """
            <lastdate(YYYYMMDD)>;<nextdate(YYYYMMDD)>

            e.g. '20170322;20200322'
        """
        self.send_data("BRD")
        last_date, next_date = self.parse_result_data(
            r"\d{0,8};\d{0,8}", self.receive_data())
        return datetime.datetime.strptime(str(last_date), "%Y%m%d").date() if last_date else None, datetime.datetime.strptime(str(next_date), "%Y%m%d").date() if next_date else None
