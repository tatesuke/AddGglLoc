
from datetime import datetime, timedelta, timezone
from logging import getLogger
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, cast
import dataclasses
import re

import piexif

from . import NAME_LOGER
from .location_log import LocationLog
from .google_location_log_loader import GoogleLocationLogLoader, InvalidFileFormatException


DEFAULT_DIR_JPEG_INPUT = "./picture"
""" 位置情報付与対象の画像が格納されているディレクトリのデフォルト値"""

DEFAULT_DIR_GOOGLE_LOCATION_LOG = "./google"
""" グーグルのロケーション履歴が格納されているルートディレクトリのデフォルト値 """

DEFAULT_DIR_OUTPUT = "./output"
""" 位置情報を付与した画像を出力するディレクトリのデフォルト値 """

DEFAULT_TOLERANCE_SEC = 5 * 60
""" 撮影時間と位置情報のタイムスタンプがこれ以下の値ならその位置情報を採用するデフォルト値 """


logger = getLogger(NAME_LOGER)


@dataclasses.dataclass
class AddGglLoc(object):
    """ グーグルロケーション履歴を元に写真に位置情報を付与する。 """

    # 位置情報付与対象の画像が格納されているディレクトリ（この配下を再帰的に探します）。
    jpegInputDir: str = dataclasses.field(default=DEFAULT_DIR_JPEG_INPUT)

    # グーグルのロケーション履歴が格納されているルートディレクトリ（この配下を再帰的に探します）。
    googleLocationLogDir: str = \
        dataclasses.field(default=DEFAULT_DIR_GOOGLE_LOCATION_LOG)

    # 位置情報を付与した画像を出力するディレクトリ。
    outputDir: str = dataclasses.field(default=DEFAULT_DIR_OUTPUT)

    # 撮影時間と位置情報を紐付ける時間の範囲（秒）。タイムスタンプの差がこれ以下の値ならその位置情報を採用します
    toleranceSec: int = dataclasses.field(default=DEFAULT_TOLERANCE_SEC)

    def execute(self) -> None:
        """ 処理を実行する """

        locationLogs = self._loadLocationLogs(self.googleLocationLogDir)
        if len(locationLogs) == 0:
            logger.info("グーグルロケーション履歴ファイルが見つかりませんでした。")
            return

        jpegFiles: List[str] = self._listJpegFiles(self.jpegInputDir)
        if len(jpegFiles) == 0:
            logger.info("JPEGファイルが見つかりませんでした。")
            return

        total = len(jpegFiles)
        for i, jpegFile in enumerate(jpegFiles):
            try:
                result = self._processFile(locationLogs, jpegFile)
            except Exception as e:
                result = FileProcessResult("ERROR", errorMsg=f"{e}")

            # TODO 例外系はdebugログ出したほうが親切なんだろうな
            if result.status == "ERROR":
                logger.error(
                    f"({i}/{total})\t{jpegFile}\t{result.status}\t{result.errorMsg}"
                )
            elif result.status == "WARN":
                logger.warning(
                    f"({i}/{total})\t{jpegFile}\t{result.status}\t{result.successMsg}\t{result.errorMsg}"
                )
            else:
                logger.info(
                    f"({i}/{total})\t{jpegFile}\t{result.status}\t{result.successMsg}"
                )

        logger.info(f"{len(jpegFiles)}個のJPEGファイルを処理しました。")

    def _loadLocationLogs(self, baseDir: str) -> List[LocationLog]:
        """ ロケーション履歴ファイルを読み込む """

        logger.info("[START]\tGoogleロケーション履歴を読み込みます。")

        if not os.path.isdir(baseDir):
            raise AddGglLocException(f"ディレクトリが見つかりません:'{baseDir}'")

        jsonFiles = [
            os.path.join(curDir, file)
            for curDir, _, files in os.walk(baseDir)
            for file in files
            if file.endswith(".json")
        ]
        total = len(jsonFiles)
        logger.info(f"{total}個のJSONファイルが見つかりました。")

        fileNum = 0
        locationLogs = []
        for i, file in enumerate(jsonFiles):
            try:
                tempLocationLogs = GoogleLocationLogLoader.load(file)
            except InvalidFileFormatException as e:
                logger.warning(
                    f"({i}/{total})\t{file}\tSKIP\t読み込めないファイル構造です: {e.message}")
                continue
            except Exception as e:
                logger.error(f"({i}/{total})\t{file}\tSKIP\t想定外のエラーが発生しました。")
                continue

            fileNum += 1
            locationLogs.extend(tempLocationLogs)
            logger.info(f"({i}/{total})\t{file}\tLOADED")

        # 2部探索するためにソートしておく
        locationLogs.sort(key=lambda l: l.timestamp)

        logger.info(
            f"[END]\t{fileNum}個のロケーション履歴ファイルが見つかり、{len(locationLogs)}個のロケーションログを読み込みました。")

        return locationLogs

    def _listJpegFiles(self, baseDir: str) -> List[str]:
        """ JPEGファイルを列挙する """

        logger.info("[START]\tJPEGファイルを検索します。")

        if not os.path.isdir(baseDir):
            raise AddGglLocException(f"ディレクトリが見つかりません:'{baseDir}'")

        def isJpeg(filePath: str) -> bool:
            extention = filePath.split(".")[-1].lower()
            return (extention == "jpg") or (extention == "jpeg")
        jpegFiles = [
            os.path.join(curDir, file)
            for curDir, _, files in os.walk(baseDir)
            for file in files
            if isJpeg(file)
        ]

        logger.info(f"[END]\t{len(jpegFiles)}個のJPEGファイルが見つかりました。")

        return jpegFiles

    def _processFile(self, locationLogs, file) -> "FileProcessResult":
        """ 1ファイル処理する。 """

        result: Optional[FileProcessResult] = None

        # Exifを辞書として読み込む
        exifDict: Dict[str, Any] = cast(Dict[str, Any], piexif.load(f"{file}"))

        # 既にGPS情報が格納されていたら終了
        if self._hasLocationLog(exifDict):
            return FileProcessResult("SKIP", successMsg="ロケーション情報がすでに存在します。")

        # タイムスタンプに紐づく位置情報を取得
        shootingDateTime = self._getShootingDate(exifDict)
        locationLog = self._matchLocationLog(locationLogs, shootingDateTime)

        # 位置情報が取得できなければ終了
        if locationLog is None:
            return FileProcessResult("SKIP", successMsg="どのロケージョン履歴ともマッチしませんでした。")

        # 位置情報を辞書に書き込む
        exifDict = locationLog.writeTo(exifDict)

        # ExifIFD.SceneTypeにbyte以外のデータが入っていることがまれにある。
        # byte以外のデータだとpiexif.insertに失敗するのでbyteにして入れ直す。
        if (piexif.ExifIFD.SceneType in exifDict['Exif']) and type(exifDict['Exif'][piexif.ExifIFD.SceneType]) is int:
            exifDict['Exif'][piexif.ExifIFD.SceneType] = bytes(
                [exifDict['Exif'][piexif.ExifIFD.SceneType]]
            )
            result = FileProcessResult(
                "WARN",
                errorMsg="'ExifIFD.SceneType'がbyte型でなかったので、byte型に変換しました。"
            )

        # 出力先ディレクトリ作成
        pathFromBase = Path(file).relative_to(self.jpegInputDir)
        outputPath = Path(self.outputDir, pathFromBase)
        try:
            os.makedirs(outputPath.parent, exist_ok=True)
        except Exception as e:
            return FileProcessResult("ERROR", errorMsg=f"ディレクトリを作成できませんでした:'{outputPath.parent}'.")

        # 位置情報付与して出力
        exifBytes = piexif.dump(exifDict)
        piexif.insert(exifBytes, file, outputPath)

        result = FileProcessResult("ADDED") if result is None else result
        result.successMsg = f"({locationLog.lat}, {locationLog.lon}) {'' if locationLog.areaInformation is None else f',{locationLog.areaInformation}'}"

        return result

    def _hasLocationLog(self, exifDict: Dict[str, Any]) -> bool:
        """ すでに位置情報を保持していればTrueを返す。 """
        gpsIdf = exifDict.get("GPS")

        return gpsIdf is not None \
            and piexif.GPSIFD.GPSLatitudeRef in gpsIdf \
            and piexif.GPSIFD.GPSLatitude in gpsIdf \
            and piexif.GPSIFD.GPSLongitudeRef in gpsIdf \
            and piexif.GPSIFD.GPSLongitude in gpsIdf

    def _matchLocationLog(self, locationLogs: List[LocationLog], shootingDateTime: Optional[datetime]) -> Optional[LocationLog]:
        """ 撮影時間における位置情報を返す。推測できなければNoneを返す。 """

        if shootingDateTime is None:
            return None

        # 位置情報を2分探索
        left = 0
        right = len(locationLogs) - 1
        center = 0
        while (left <= right):
            center = left + int((right - left) / 2)
            centerDateTime = locationLogs[center].timestamp
            if centerDateTime == shootingDateTime:
                break
            if shootingDateTime > centerDateTime:
                left = center + 1
            else:
                right = center - 1

        # 最終的にたどり着いた位置情報と撮影時間とだいたい同じであればその位置情報を採用
        delta = locationLogs[center].timestamp - shootingDateTime
        if delta.total_seconds() <= self.toleranceSec:
            return locationLogs[center]

        return None

    def _getShootingDate(self, exifDict) -> Optional[datetime]:
        """ 撮影時間を返す """

        dateTimeOriginal = exifDict["Exif"].get(
            piexif.ExifIFD.DateTimeOriginal)
        if dateTimeOriginal is None:
            return None

        # `dateTimeOriginal`のb`yyyy:MM:dd hh:mm:ss`をパースする
        # TODO 正規表現はコンパイルしておいたほうが早いかも
        dateTimeOriginalStr = dateTimeOriginal.decode()
        m = re.match(
            r"([0-9]{4}):([0-9]{2}):([0-9]{2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})", dateTimeOriginalStr)
        if m is None:
            raise AddGglLocException(
                f"EXIF内の`dateTimeOriginal`を解釈できません({dateTimeOriginalStr})。")

        year = int(m.groups()[0])
        month = int(m.groups()[1])
        day = int(m.groups()[2])
        hour = int(m.groups()[3])
        minute = int(m.groups()[4])
        sec = int(m.groups()[5])

        return datetime(year, month, day, hour, minute, sec, tzinfo=timezone(timedelta(hours=+9), 'JST'))

@dataclasses.dataclass
class FileProcessResult:

    status: Literal["ADDED", "SKIP", "ERROR", "WARN"]
    successMsg: Optional[str] = dataclasses.field(default=None)
    errorMsg: Optional[str] = dataclasses.field(default=None)
    exeption: Optional[Exception] = dataclasses.field(default=None)


class AddGglLocException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message



