import argparse
from logging import INFO, FileHandler, Formatter, getLogger, StreamHandler, DEBUG

from . import NAME_LOGER
from .argparse import ThrowingArgumentParser
from .addgglloc import AddGglLoc, AddGglLocException, DEFAULT_DIR_JPEG_INPUT, DEFAULT_DIR_GOOGLE_LOCATION_LOG, DEFAULT_DIR_OUTPUT, DEFAULT_TOLERANCE_SEC

logger = getLogger(NAME_LOGER)
logger.setLevel(INFO)

def _main() -> None:
    """メイン関数"""
    try:
        _initLogger()
        logger.info("[START] addgglloc")
        args = _parseArgs()
        logger.info(f"args:{vars(args)}")

        addgglloc = AddGglLoc()
        addgglloc.googleLocationLogDir = args.google
        addgglloc.jpegInputDir = args.jpeg
        addgglloc.outputDir = args.output
        addgglloc.execute()
    except AddGglLocException as e:
        logger.error(f"[ABORT] {e.message}")
    finally:
        logger.info("[END] addgglloc")

def _initLogger():
    global logger
    sHandler = StreamHandler()
    sHandler.setLevel(INFO)
    sHandler.setFormatter(Formatter("[%(levelname)7s]\t%(message)s"))
    logger.addHandler(sHandler)

    fHandler = FileHandler("addgglloc.log", encoding="utf-8")
    fHandler.setLevel(DEBUG)
    fHandler.setFormatter(Formatter("%(asctime)s\t[%(levelname)7s]\t%(message)s"))
    logger.addHandler(fHandler)

def _parseArgs() -> argparse.Namespace:
    """ コマンドラインパラメータを解析 """
    parser = ThrowingArgumentParser()
    parser.description = "グーグルロケーション履歴のJSONファイルを元に、JPEGファイルに位置情報を付与します。"
    parser.add_argument("-j", "--jpeg", type=str,
                        metavar="path",
                        default=DEFAULT_DIR_JPEG_INPUT,
                        help=f"ここで指定されたディレクトリ配下からJPEGファイルを検索します。 デフォルト値： \"{DEFAULT_DIR_JPEG_INPUT}\"")
    parser.add_argument("-g", "--google", type=str,
                        metavar="path",
                        default=DEFAULT_DIR_GOOGLE_LOCATION_LOG,
                        help=f"ここで指定されたディレクトリ配下からGoogleロケーション履歴ファイルを検索します。 デフォルト値：\"{DEFAULT_DIR_GOOGLE_LOCATION_LOG}\"")
    parser.add_argument("-o", "--output", type=str,
                        metavar="path",
                        default=DEFAULT_DIR_OUTPUT,
                        help=f"ここで指定されたディレクトリ配下に、処理済みのJPEGが格納されます。 デフォルト値：\"{DEFAULT_DIR_OUTPUT}\"")
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    _main()
