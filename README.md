# addgglloc

AddGoogleLocation、グーグルのロケーション履歴ファイルをもとにJPEGファイルに位置情報を付与するコマンドラインアプリです。

※このソフトウェアを利用して大切なファイルを破壊したとしても責任は負いません。

## 使い方

Python3の実行環境が必要です。まずはPython3を導入してください。  

* https://docs.python.org/ja/3/using/index.html

### クローン

まずこのプロジェクトをクローンしてください。

```
git clone https://github.com/tatesuke/AddGglLoc.git
```


### 依存モジュールダウンロード
次に以下コマンドで依存ライブラリをダウンロードしてください。
（venvを利用していますが必須ではありません。意味を理解できる方は必ずしもvenvを利用する必要はありません）

```
cd AddGglLoc
python3 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 実行

グーグルロケーション履歴のJSONファイルを元にJPEGファイルに位置情報を付与するには、次のコマンドを実行してください。

```
python -m addgglloc \
    -j "JPEGファイルが格納されたフォルダのパス" \
    -g "Googleロケーション履歴が格納されたフォルダのパス" \
    -o "処理済み画像を出力するディレクトリ"
```

正確なusageは以下になります。

```
usage: python -m addgglloc [-h] [-j path] [-g path] [-o path]

グーグルロケーション履歴のJSONファイルを元に、JPEGファイルに位置情報を付与します。

options:
  -h, --help            show this help message and exit
  -j path, --jpeg path  ここで指定されたディレクトリ配下からJPEGファイルを検索します。
                        デフォルト値： "./picture"
  -g path, --google path
                        ここで指定されたディレクトリ配下からGoogleロケーション履歴ファイルを検索します。
                        デフォルト値："./google"
  -o path, --output path
                        ここで指定されたディレクトリ配下に、処理済みのJPEGが格納されます。
                        デフォルト値："./output"
```


事故防止のため、このコマンドは元のファイルを**変更しません**。
"-o"で指定したフォルダに位置情報を付与した画像が出力されるので、意図しないデータ変更やファイル破損がないことを確認した上で元画像に上書きしてください。

出力フォルダには入力画像と同じディレクトリ構造で処理画像が出力されるため、上書きはドラッグアンドドロップやコピーペーストで簡単に実施できます。
