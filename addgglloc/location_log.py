import copy
import dataclasses
import datetime
import math
from typing import Any, Dict, Literal, Optional, Tuple

import piexif


@dataclasses.dataclass(frozen=True)
class LocationLog:
    """ 「いつ」、「どこ」にいたかを保持するデータクラス """

    # タイムスタンプ
    timestamp: datetime.datetime

    # 緯度
    lat: float

    # 経度
    lon: float

    # 場所の名称
    areaInformation: Optional[str] = dataclasses.field(default=None)

    def writeTo(self, exifDict: Dict[str, Any]) -> Dict[str, Any]:
        """ 渡されたExif辞書のコピーを作成し、そこに位置情報を書き込む """

        copyExifDict = copy.deepcopy(exifDict)
        copyGpsIdf = copyExifDict["GPS"]

        lat, latRef = self._degreeToDmsRef(self.lat, "lat")
        lon, lonRef = self._degreeToDmsRef(self.lon, "lon")
        dateStamp = self.timestamp.strftime("%Y:%m:%d")
        hour = (self.timestamp.hour, 1)
        minute = (self.timestamp.minute, 1)
        sec = (self.timestamp.second, 1)

        if piexif.GPSIFD.GPSVersionID not in copyGpsIdf:
            copyGpsIdf[piexif.GPSIFD.GPSVersionID] = (2, 0, 0, 0)
        copyGpsIdf[piexif.GPSIFD.GPSLatitudeRef] = latRef.encode()
        copyGpsIdf[piexif.GPSIFD.GPSLatitude] = lat
        copyGpsIdf[piexif.GPSIFD.GPSLongitudeRef] = lonRef.encode()
        copyGpsIdf[piexif.GPSIFD.GPSLongitude] = lon
        copyGpsIdf[piexif.GPSIFD.GPSDateStamp] = dateStamp.encode()
        copyGpsIdf[piexif.GPSIFD.GPSTimeStamp] = (hour, minute, sec)
        if self.areaInformation is not None:
            copyGpsIdf[piexif.GPSIFD.GPSAreaInformation] = self.areaInformation.encode()

        return copyExifDict

    @staticmethod
    def _degreeToDmsRef(degree: float, axis: Literal["lat", "lon"]) -> Tuple[Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]], str]:
        """ 度数表記を((D, M, S), Ref)表記に変換する

        (出典) https://www.benricho.org/calculate/degree.html
        【例】「35.67度」を 60進数（度・分・秒）に変換する。
        度 = 整数のみを取り出す ⇒ 35
        分 = 小数点以下を取り出し、60 を掛け、整数部分を取り出す。
            0.67 * 60 = 40.2 ⇒ 40
        秒 = 分での計算の小数点以下を取り出し、60 を掛ける。
            0.2 * 60 = 12
        度・分・秒を組み合わせ、35度 40分 12秒となる。
        """
        if degree >= 0:
            ref = "N" if axis == "lat" else "E"
        else:
            ref = "S" if axis == "lat" else "W"

        dec1, deg = math.modf(degree)
        dec2, min_,  = math.modf(dec1 * 60)
        sec = dec2 * 60
        return (((int(deg), 1), (int(min_), 1), (int(sec), 1)), ref)
