from flask import Flask, request, abort
from flaskext.mysql import MySQL

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

import execjs

from datetime import datetime, timedelta

import re

import os

app = Flask(__name__)

#config
app.config['MYSQL_DATABASE_USER'] = '...'
app.config['MYSQL_DATABASE_PASSWORD'] = '...'
app.config['MYSQL_DATABASE_DB'] = '...'
app.config['MYSQL_DATABASE_HOST'] = '...'

# Channel Access Token
line_bot_api = LineBotApi('...')
# Channel Secret
handler = WebhookHandler('...')

errString = '輸入「星期日 90」\n會幫您紀錄為向曹賣買進的價格\n\n輸入「星期一 早上 90」\n會幫您紀錄為星期一早上的價格\n\n輸入「下午 90」\n會幫您紀錄為今日下午的價格\n\n輸入「90」\n會幫您紀錄為現在的價格\n\n輸入「0」\n會幫您清除現在的價格'

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理按鈕
@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    if (data == "buy"):
        message = TextSendMessage(text="多少錢呢？")
        line_bot_api.reply_message(event.reply_token, message)
    

# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    sourceType = event.source.type
    user_id = event.source.user_id
    profile = line_bot_api.get_profile(user_id)
    y = event.message.text
    print(y)

############

    calendar = (datetime.utcnow() + timedelta(hours=8)).isocalendar()
    week = calendar[1]
    day = calendar[2]
    if (day == 7):
        week = (datetime.utcnow() + timedelta(days=1) + timedelta(hours=8)).isocalendar()[1]
    ap = time = (datetime.utcnow() + timedelta(hours=8)).strftime("%p")

############
    
    dataListIndex = 0
    y = y.replace(" ", "")
    match = re.search('星期(.)([^0-9]*)([0-9]+)$', y)
    if (match):
        matchDay = match.group(1)
        matchAP = match.group(2)
        y = match.group(3)
        if (matchDay == '日' or matchDay == '天'):
            dataListIndex = 3
        else:
            offset = 0
            if (matchAP == '早上' or matchAP == '上午' or matchAP == '白天'):
                offset = 0
            elif (matchAP == '晚上' or matchAP == '下午'):
                offset = 1
            else:
                if (sourceType == 'user'):
                    message = TextSendMessage(text="格式錯誤")
                    errMessage = TextSendMessage(text=errString)
                    line_bot_api.reply_message(event.reply_token, [message, errMessage])
                return
            if (matchDay == '一'):
                dataListIndex = 4 + offset
            elif (matchDay == '二'):
                dataListIndex = 6 + offset
            elif (matchDay == '三'):
                dataListIndex = 8 + offset
            elif (matchDay == '四'):
                dataListIndex = 10 + offset
            elif (matchDay == '五'):
                dataListIndex = 12 + offset
            elif (matchDay == '六'):
                dataListIndex = 14 + offset
            else:
                if (sourceType == 'user'):
                    message = TextSendMessage(text="格式錯誤")
                    errMessage = TextSendMessage(text=errString)
                    line_bot_api.reply_message(event.reply_token, [message, errMessage])
                return
    else:
        match = re.search('([^0-9]*)([0-9]+)$', y)
        if (match):
            matchDay = day
            matchAP = match.group(1)
            y = match.group(2)
            
            if ('昨' in matchAP):
                matchDay = matchDay - 1
                if (matchDay == 0):
                    matchDay = 7
            if (matchDay == 7):
                dataListIndex = 3
            else:
                dataListIndex = (matchDay + 1) * 2
                
                if (matchAP == ''):
                    if (ap == "PM"):
                        dataListIndex = dataListIndex + 1
                elif ('早上' in matchAP or '上午' in matchAP or '白天' in matchAP):
                    dataListIndex = dataListIndex
                elif ('晚上' in matchAP or '下午' in matchAP):
                    dataListIndex = dataListIndex + 1
                else:
                    if (sourceType == 'user'):
                        message = TextSendMessage(text="格式錯誤")
                        errMessage = TextSendMessage(text=errString)
                        line_bot_api.reply_message(event.reply_token, [message, errMessage])
                    return
        else:
            if (sourceType == 'user'):
                message = TextSendMessage(text="格式錯誤")
                errMessage = TextSendMessage(text=errString)
                line_bot_api.reply_message(event.reply_token, [message, errMessage])
            return
            
############
    
    #init MySQL
    mysql = MySQL()
    mysql.init_app(app)
    connection = mysql.connect()
    cursor = connection.cursor()
    
############
    
    sql = "SELECT * FROM `turnip` WHERE `uid`=%s"
    cursor.execute(sql, (user_id,))
    data = cursor.fetchone()
    if (data):
        data = data[1:]
        if (data[1] == week - 1):
            data = [user_id, week, data[16], '', '', '', '', '', '', '', '', '', '', '', '', '', -1]
        elif (data[1] < week):
            data = [user_id, week, -1, '', '', '', '', '', '', '', '', '', '', '', '', '', -1]
    else:
        data = [user_id, week, -1, '', '', '', '', '', '', '', '', '', '', '', '', '', -1]
        sql = "INSERT INTO `turnip` (`uid`) VALUES (%s)"
        cursor.execute(sql, (user_id,))
        connection.commit()

############

    dataList=list(data)
    if (y == '0'):
        dataList[dataListIndex] = ''
    else:
        dataList[dataListIndex] = y

############
        
    p = [0, 0, 0, 0]
    posList = [[], [], [], []]
    with open('./predictions.js') as f:
        ctx = execjs.compile(f.read())
        dics = ctx.call('calculateOutput', dataList[3], [dataList[4], dataList[5], dataList[6], dataList[7], dataList[8], dataList[9], dataList[10], dataList[11], dataList[12], dataList[13], dataList[14], dataList[15]], False, dataList[2])
        index = 0
        for i in range(len(dics)):
            if (i == 0):
                continue
            index = dics[i]['pattern_number']
            p[index] = dics[i]['category_total_probability']
            posList[index].append(dics[i])

    for i in range(len(p)):
        if (p[i] >= 1):
            dataList[16] = i
            break

############
        
    templateText = ""
    patterns = ["波型", "三期型", "遞減型", "四期型"]
    phases = ["星期日", "星期日", "星期一早上", "星期一下午", "星期二早上", "星期二下午", "星期三早上", "星期三下午", "星期四早上", "星期四下午", "星期五早上", "星期五下午", "星期六早上", "星期六下午"]
    currentPhase = day * 2
    if (ap == "PM"):
        currentPhase = currentPhase + 1
    if (day == 7):
        currentPhase = 2
    for i in range(len(p)):
        if (p[i] >= 1):
            templateText = templateText + "%s"%(patterns[i])
            weekMax = posList[i][0]['weekMax']
            comment = "\n請趕快賣出"
            if (i == 0):
                prices = posList[i][0]['prices']
                for j in range(len(prices)):
                    if (prices[j]['max'] == weekMax):
                        comment = "\n請在%d~%d的價格時賣出"%(prices[j]['min'], prices[j]['max'])
                        break
            elif (i == 1 or i == 3):
                for j in range(len(posList[i])):
                    prices = posList[i][j]['prices']
                    for k in range(len(prices)):
                        if (k <= currentPhase):
                            continue
                        if (prices[k]['max'] == weekMax):
                            if (len(posList[i]) == 1):
                                comment = "\n請在%s賣出"%(phases[k])
                            else:
                                comment = "\n可望最早在%s有%d~%d的價格"%(phases[k], prices[k]['min'], prices[k]['max'])
                            break
                    if (comment != "\n請趕快賣出"):
                        break
            templateText = templateText + comment
            break
        elif (p[i] != 0):
            if (len(templateText) != 0):
                templateText = templateText + "\n"
            templateText = templateText + "%s:%d%%"%(patterns[i], (p[i]+0.005)*100)

    if (dataList[16] < 0):
        for i in range(len(p)):
            if (p[i] != 0):
                weekMax = posList[i][0]['weekMax']
                if (i == 1 or i == 3):
                    comment = ""
                    for j in range(len(posList[i])):
                        prices = posList[i][j]['prices']
                        for k in range(len(prices)):
                            if (k <= currentPhase):
                                continue
                            if (prices[k]['max'] == weekMax):
                                comment = "\n如果是%s，可望最早在%s有%d~%d的價格"%(patterns[i], phases[k], prices[k]['min'], prices[k]['max'])
                                break
                        if (comment != ""):
                            break
                    templateText = templateText + comment
                    break
            
    if (day == 7 and y.isdigit()):
        message = TextSendMessage(text="一顆%s鈴錢～漲價吧～漲價的話～就太好了～"%(y))
        line_bot_api.reply_message(event.reply_token, message)
    else:
        buttons_template_message = TemplateSendMessage(
            alt_text="結果",
            template=ButtonsTemplate(
                text=templateText,
                actions=[
                    URIAction(
                        label='View Detail',
                        uri="https://turnipprophet.io/?prices=%s.%s.%s.%s.%s.%s.%s.%s.%s.%s.%s.%s.%s&pattern=%d"%(dataList[3], dataList[4], dataList[5], dataList[6], dataList[7], dataList[8], dataList[9], dataList[10], dataList[11], dataList[12], dataList[13], dataList[14], dataList[15], dataList[2])
                    )
                ]
            )
        )        
        line_bot_api.reply_message(event.reply_token, buttons_template_message)

    data = tuple(dataList)

############

    print(data)
    sql = "UPDATE `turnip` SET week=%s, pattern=%s, sun=%s, monA=%s, monP=%s, tueA=%s, tueP=%s, wedA=%s, wedP=%s, thuA=%s, thuP=%s, friA=%s, friP=%s, satA=%s, satP=%s, result=%s WHERE uid=%s"
    cursor.execute(sql, (data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11], data[12], data[13], data[14], data[15], data[16], data[0]))
    connection.commit()

import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
