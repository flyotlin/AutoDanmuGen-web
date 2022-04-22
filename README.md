# AutoDanmuGen-web
Web UI powered by [AutoDanmuGen](https://github.com/flyotlin/AutoDanmuGen) library.

This web application visually shows what's being done by AutoDanmuGen library.

## Anouncement
Most of the code is adapted from livebot.

## 功能
使用 livebot 及 AutoDanmuGen 函式庫，針對某部影片及其彈幕進行自動彈幕生成。

上傳指定的影片 (.mp4) 以及 彈幕檔案 (.ass) 後，AutoDanmuGen-web 支援以 livebot 對此影片進行 **test** 及 **predict**。

此外，AutoDanmuGen-web 在 **test** 或 **predict** 後，會將最終結果以 UI 的方式顯示出來。

## UI views
### 1. index (`index.html`)
歡迎頁面，功能包含：
1. Jumbo Banner
2. 上傳影片 (.mp4) 及其字幕檔案 (.ass)
### 2. preview (`preview.html`)
上傳影片及字幕檔案成功後會導向此頁面。

preview 會將上傳的影片以 html tag `video` 顯示出來讓使用者進行預覽。

上方提供 2 個功能按鈕，`test` 以及 `predict`。點擊按鈕時，會跳出帶有 form 的 modal。

`test` 的 modal 會將字幕檔中所有彈幕於 form 中列出，並在彈幕旁加上 checkbox。送出後讓 Flask WebServer 知道要對哪些彈幕進行 test。

`predict` 的 modal 提供 input 選取時間，送出後預測該時間點應該出現哪一則彈幕。

以上兩個 modal `test` 及 `predict` 中的 form 送出 (submit) 後會向 Flask WebServer 發送 POST request，並且導向 result 頁面。


### 3. result (`result.html`)

result 頁面一開始會持續向 Flask WebServer polling test 或 predict 的進度。

未完成會顯示 loading now (Maybe a skeleton loader page)，**實作主要是設定一個 setTimeout，在裡面每隔幾秒就進行 polling，當 `POST /poll` 回傳 "done" 時才 removeTimeout。**

完成後顯示 test / predict 結果，UI 大致如下：

![](https://i.imgur.com/eHi7nJl.png)

:::info

:bulb: **Behind the scene: POST Request** 

`test` 及 `predict` 的 form 發出 POST request 後，無論 test 或 predict 結束與否，Flask WebServer 會直接將 user 導向 result 頁面。

在 result 頁面時，持續向 Flask WebServer polling test 或 predict 是否完成。尚未完成時會暫時顯示 skeleton loader，並且適時提示目前進度。

:::
## Flask Web Server API EndPoints
### `GET /`
Get and Render `index.html`

### `GET /preview`
Get and Render `preview.html`。

POST /upload 成功後才會 redirect 到此 route。

#### Arguments
* `?id` (**required**): 影片 id

### `GET /result`
Get and Render `result.html`。

POST /test 或者 POST /predict 成功後才會 redirect 到此 route。

#### Arguments
* `?id` (**required**): 影片 id

### `GET /poll`
`result.html` 用來檢查 test / predict 是否完成。

完成後會在 data 中回傳 "done"，若失敗則回傳 "failed"，若還在各階段則會分別回傳:
1. "Extracting Video Frames"
2. "Converting .txt to .json"
3. "Adding Context into .json"
4. "Adding Context into -context.json"
5. "Testing / Predicting"

使用回傳字串可以直接放到 skeleton loader 中提示目前在哪個 stage，像是 "Extracting Video Frames Now..."

#### Arguments
* `?id` (**required**): 影片 id

### `POST /upload`
`index.html` 在上傳影片及彈幕檔案時使用。

#### Files Data
* `video` (**required**): 影片 .mp4 檔案
* `comment` (**required**): 影片彈幕 .ass 檔案

### `POST /test`
進行 test。

會直接 redirect 到 `result.html`，並且使用另一個 thread 於背景執行 test 的相關指令

#### Data
* `checked_comment_id`: 被勾選需要進行 test 的彈幕。若沒有任何彈幕被勾選，於前端就需要警告使用者。

### `POST /predict`