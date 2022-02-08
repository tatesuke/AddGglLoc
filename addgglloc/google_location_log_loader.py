

import datetime
import json
from logging import getLogger
from typing import Any, Dict, List

from . import NAME_LOGER
from .location_log import LocationLog


logger = getLogger(NAME_LOGER)


class GoogleLocationLogLoader(object):
    """ Googleのロケーション履歴ファイル(.json)を読みこむ """

    @classmethod
    def load(cls, fileName: str) -> List[LocationLog]:
        """ Googleのロケーション履歴ファイル(.json)を読み込み、LocationLogの配列にして返す。
        戻り値はソートされていない。
        """
        
        with open(fileName, "r", encoding="utf-8") as f:
            try:
                file = json.load(f)
            except json.decoder.JSONDecodeError as e:
                raise InvalidFileFormatException("Json parse error.") from e

        # 以下構造を読み込む
        # {
        #     "timelineObjects": [
        #         {
        #             "activitySegment": {(略)}
        #         },{
        #             "placeVisit": {(略)}
        #         },
        #         ・・・
        #     ]
        # }
        try:
            locationLogs = []
            for timelineObject in file["timelineObjects"]:
                if "activitySegment" in timelineObject:
                    locationLogs.extend(
                        cls._processActivtySegment(
                            timelineObject["activitySegment"])
                    )
                elif "placeVisit" in timelineObject:
                    locationLogs.extend(
                        cls._processPlaceVisit(timelineObject["placeVisit"])
                    )
        except KeyError as e:
            keyName = e.args[0]
            raise InvalidFileFormatException(f"Json key '{keyName}' not found.")  from e
        except Exception as e:
            raise InvalidFileFormatException(f"{e}")  from e
        
        return locationLogs

    @classmethod
    def _processActivtySegment(cls, activtySegment: Dict[str, Any]) -> List[LocationLog]:
        """ ActivtySegmentを読み込む """

        # `activitySegment`は移動を表します。
        # {
        #   "activitySegment": {
        #     "startLocation": {
        #       "latitudeE7": 355050042,
        #       "longitudeE7": 1387341570,
        #     },
        #     "endLocation": {
        #       "latitudeE7": 354423067,
        #       "longitudeE7": 1386030378,
        #     },
        #     "duration": {
        #       "startTimestamp": "2018-04-16T03:22:42.995Z",
        #       "endTimestamp": "2018-04-16T05:19:38.001Z"
        #     },
        #     (略)
        #     "simplifiedRawPath": {
        #       "points": [
        #         {
        #           "latE7": 355081374,
        #           "lngE7": 1387612949,
        #           "accuracyMeters": 10,
        #           "timestamp": "2018-04-16T03:32:38.003Z"
        #         },
        #         (略)
        #         {
        #           "latE7": 354743523,
        #           "lngE7": 1385758080,
        #           "accuracyMeters": 5,
        #           "timestamp": "2018-04-16T05:09:10.498Z"
        #         }
        #       ]
        #     },
        #     (略)
        #   }
        # }

        locationLogs = []

        if "latitudeE7" in activtySegment["startLocation"]:
            locationLogs.append(LocationLog(**{
                "timestamp": cls._convertTimestamp(activtySegment["duration"]["startTimestamp"]),
                "lat": cls._e7ToDegree(activtySegment["startLocation"]["latitudeE7"]),
                "lon": cls._e7ToDegree(activtySegment["startLocation"]["longitudeE7"]),
            }))
        if "latitudeE7" in activtySegment["endLocation"]:
            locationLogs.append(LocationLog(**{
                "timestamp": cls._convertTimestamp(activtySegment["duration"]["endTimestamp"]),
                "lat": cls._e7ToDegree(activtySegment["endLocation"]["latitudeE7"]),
                "lon": cls._e7ToDegree(activtySegment["endLocation"]["longitudeE7"]),
            }))

        if "simplifiedRawPath" not in activtySegment:
            return locationLogs

        for p in activtySegment["simplifiedRawPath"]["points"]:
            locationLogs.append(LocationLog(**{
                "timestamp": cls._convertTimestamp(p["timestamp"]),
                "lat": cls._e7ToDegree(p["latE7"]),
                "lon": cls._e7ToDegree(p["lngE7"]),
            }))

        return locationLogs

    @classmethod
    def _processPlaceVisit(cls, placeVisitSegment: Dict[str, Any]) -> List[LocationLog]:
        """ PlaceVisitを読み込みます。 """
        # {
        #   "placeVisit": {
        #     "location": {
        #       "latitudeE7": 354423067,
        #       "longitudeE7": 1386030378,
        #       "placeId": "ChIJ3fdiwnbnG2ARgw16pm1gZ50",
        #       "address": "日本、〒401-0337 山梨県南都留郡富士河口湖町本栖２１２",
        #       "name": "Fuji Motosuko Resort",
        #       (略)
        #     },
        #     "duration": {
        #       "startTimestamp": "2018-04-16T05:19:38.001Z",
        #       "endTimestamp": "2018-04-16T05:35:21.010Z"
        #     },
        #      (略)
        #   }
        # }
        locationLogs = []

        if "latitudeE7" not in placeVisitSegment["location"]:
            return locationLogs

        lat = cls._e7ToDegree(placeVisitSegment["location"]["latitudeE7"])
        lon = cls._e7ToDegree(placeVisitSegment["location"]["longitudeE7"])
        name = placeVisitSegment.get("name")

        start = cls._convertTimestamp(
            placeVisitSegment["duration"]["startTimestamp"])
        end = cls._convertTimestamp(
            placeVisitSegment["duration"]["endTimestamp"])

        # 到着時間のログを作成
        current = start
        locationLogs.append(LocationLog(**{
            "timestamp": start,
            "lat": lat,
            "lon": lon,
            "areaInformation": name
        }))

        # 到着から出発までの間のログを作成
        # TODO 5分は可変にしたほうがいいんだろうな
        while (end - current).total_seconds() > (5 * 60):
            current = current + datetime.timedelta(minutes=5)
            locationLogs.append(LocationLog(**{
                "timestamp": current,
                "lat": lat,
                "lon": lon,
                "areaInformation": name
            }))

        # 出発時間のログを作成
        locationLogs.append(LocationLog(**{
            "timestamp": end,
            "lat": lat,
            "lon": lon,
            "areaInformation": name
        }))

        return locationLogs

    @staticmethod
    def _convertTimestamp(timestampStr: str) -> datetime.datetime:
        """ 文字列からタイムスタンプを作成 """

        # なぜだかミリセカンドが入っていたりいなかったりするので処理分岐
        try:
            return datetime.datetime.strptime(timestampStr, "%Y-%m-%dT%H:%M:%S.%f%z")
        except ValueError:
            return datetime.datetime.strptime(timestampStr, "%Y-%m-%dT%H:%M:%S%z")

    @staticmethod
    def _e7ToDegree(e7: int) -> float:
        """ e7型式を角度に変換 """

        e7Str = str(e7)
        degree = int(e7Str[:-7]) + (int(e7Str[-7:]) / 10000000)
        return degree

class InvalidFileFormatException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message