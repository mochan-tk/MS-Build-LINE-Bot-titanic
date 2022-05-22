import logging
import os
import json
import azure.functions as func
from azure.cosmos import CosmosClient

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, StickerSendMessage, PostbackEvent, PostbackAction, QuickReply, QuickReplyButton
)

import urllib.request
import json
import os
import ssl

import ast

# LINE
channel_secret = os.getenv('CHANNEL_SECRET', None)
channel_access_token = os.getenv('CHANNEL_ACCESS_TOKEN', None)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

## Azure CosmosDB
cosmos_endpoint = os.getenv('COSMOSDB_ACCOUNT', None)
cosmos_key = os.getenv('COSMOSDB_KEY', None)
cosmos_client = CosmosClient(cosmos_endpoint, credential=cosmos_key)
database_name = os.getenv('COSMOSDB_DATABASENAME', None)
database = cosmos_client.get_database_client(database_name)
cosmos_container_name = os.getenv('COSMOSDB_CONTAINERNAME', None)
cosmos_container = database.get_container_client(cosmos_container_name)

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # get x-line-signature header value
    signature = req.headers['x-line-signature']

    # get request body as text
    body = req.get_body().decode("utf-8")
    logging.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        func.HttpResponse(status_code=400)

    return func.HttpResponse('OK')


@handler.add(PostbackEvent)
def handle_postback(event):
    question = 0
    item = {}
    ## ユーザの入力をDBから取得
    for i in cosmos_container.query_items(
            query=f'SELECT * FROM {cosmos_container_name} r WHERE r.id="{event.source.user_id}"',
            enable_cross_partition_query=True):
        question = i['question']
        item = i

    if question == 0:
        ## ユーザの入力保存
        cosmos_container.upsert_item({
                'id': event.source.user_id,
                'user_id': event.source.user_id,
                'question': 1,
                'pclass': event.postback.data
            }
        )
        ## メッセージ送信
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="年齢はいくつですか？")) 
            
    elif question == 4:
        # male = 0
        # female = 0
        # if event.postback.data == "male":
        #     male = 1
        # else:
        #     female = 1
        ## ユーザの入力保存
        cosmos_container.upsert_item({
                'id': event.source.user_id,
                'user_id': event.source.user_id,
                'question': 5,
                'pclass': item['pclass'],
                'age': item['age'],
                'sibsp': item['sibsp'],
                'parch': item['parch'],
                'sex': event.postback.data
            }
        )     
        ## メッセージ送信   
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text='乗船した港はどれですか？',
                quick_reply=QuickReply(
                    items=[
                        QuickReplyButton(
                            action=PostbackAction(label="Cherbourg", data="C", display_text="Cherbourg")
                        ),
                        QuickReplyButton(
                            action=PostbackAction(label="Queenstown", data="Q", display_text="Queenstown")
                        ),
                        QuickReplyButton(
                            action=PostbackAction(label="Southampton", data="S", display_text="Southampton")
                        )
                    ])))  
            
    elif question == 5:
        # embarked_S = 0
        # embarked_C = 0
        # embarked_Q = 0
        
        # if event.postback.data == 'S':
        #     embarked_S = 1
        # elif event.postback.data == 'C':
        #     embarked_C = 1
        # else:
        #     embarked_Q = 1
        ## ユーザの入力保存
        cosmos_container.upsert_item({
                'id': event.source.user_id,
                'user_id': event.source.user_id,
                'question': 6,
                'pclass': item['pclass'],
                'age': item['age'],
                'sibsp': item['sibsp'],
                'parch': item['parch'],
                'sex': item['sex'],
                'embarked': event.postback.data
            }
        )       
        ## ユーザの入力をDBから取得
        pclass = ''
        sex = ''
        age = ''
        sibsp = ''
        parch = ''
        embarked = ''
        for item in cosmos_container.query_items(
                query=f'SELECT * FROM {cosmos_container_name} r WHERE r.id="{event.source.user_id}"',
                enable_cross_partition_query=True):
            pclass = item['pclass']
            sex = item['sex']
            age = item['age']
            sibsp = item['sibsp']
            parch = item['parch']
            embarked = item['embarked']

        ## 生存予測
        allowSelfSignedHttps(True) # this line is needed if you use self-signed certificate in your scoring service.

        # Request data goes here
        data = {
            "data":
            [
                {
                        'PassengerId': "0",
                        'Survived': "0",
                        'Pclass': pclass,
                        'Name': "example_value",
                        'Sex': sex,
                        'Age': age,
                        'SibSp': sibsp,
                        'Parch': parch,
                        'Ticket': "example_value",
                        'Fare': "0",
                        'Cabin': "example_value",
                        'Embarked': embarked,
                },
            ],
        }

        body = str.encode(json.dumps(data))

        url = 'http://9f9f1553-059a-49a5-9d7d-9e86d4b8305e.japaneast.azurecontainer.io/score'
        api_key = '' # Replace this with the API key for the web service
        headers = {'Content-Type':'application/json', 'Authorization':('Bearer '+ api_key)}

        req = urllib.request.Request(url, body, headers)

        result = ''
        json_result = {}
        j_dict = {}
        try:
            logging.info('try in2')
            response = urllib.request.urlopen(req)

            result = response.read().decode("utf8", 'ignore')
            json_result = json.loads(result)
            logging.info(type(result))
            #json_result = json.load(result)
            logging.info(type(json_result))
            logging.info(str(json_result))

            j_dict = ast.literal_eval(json_result)
            logging.info(type(j_dict['result']))
            logging.info(str(j_dict['result']))
        except urllib.error.HTTPError as error:
            logging.info('except in')
            logging.info("The request failed with status code: " + str(error.code))

            result = 'Error'
            # Print the headers - they include the requert ID and the timestamp, which are useful for debugging the failure
            logging.info(error.info())
            logging.info(json.loads(error.read().decode("utf8", 'ignore')))

        ## メッセージ送信   
        if j_dict['result'][0] == 1:
            line_bot_api.reply_message(
                event.reply_token,
                [TextSendMessage(
                    text='安心してください。あなたは無事に帰ってこれるでしょう。'),
                    StickerSendMessage(
                    package_id='11537',
                    sticker_id='52002735')]) 
        else:
            line_bot_api.reply_message(
                event.reply_token,
                [TextSendMessage(
                    text='あなたには困難な運命が待ち受けている...かもしれません...'),
                    StickerSendMessage(
                    package_id='11537',
                    sticker_id='52002755')]) 

    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='『予測』とメッセージを送ってみてください。'))


@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    if '予測' == event.message.text:
        ## ユーザの入力保存
        cosmos_container.upsert_item({
                'id': event.source.user_id,
                'user_id': event.source.user_id,
                'question': 0
            }
        )
        ## メッセージ送信
        line_bot_api.reply_message(
            event.reply_token,
            [TextSendMessage(text='🤔あたながもし、あのタイタニック号に乗船していたらどうなっていたのか...少し垣間見てみましょう🛳'),
            TextSendMessage(
                text='チケットのクラスはどれですか？',
                quick_reply=QuickReply(
                    items=[
                        QuickReplyButton(
                            action=PostbackAction(label="1st", data="1", display_text="1st")
                        ),
                        QuickReplyButton(
                            action=PostbackAction(label="2nd", data="2", display_text="2nd")
                        ),
                        QuickReplyButton(
                            action=PostbackAction(label="3rd", data="3", display_text="3rd")
                        )
                    ]))]) 
    else:
        question = 0
        item = {}
        ## ユーザの入力をDBから取得
        for i in cosmos_container.query_items(
                query=f'SELECT * FROM {cosmos_container_name} r WHERE r.id="{event.source.user_id}"',
                enable_cross_partition_query=True):
            question = i['question']
            item = i

        if question == 1:
            ## ユーザの入力保存
            cosmos_container.upsert_item({
                    'id': event.source.user_id,
                    'user_id': event.source.user_id,
                    'question': 2,
                    'pclass': item['pclass'],
                    'age': event.message.text
                }
            )
            ## メッセージ送信
            line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='乗船している兄弟・配偶者の人数を教えてください。')) 
            
        elif question == 2:
            ## ユーザの入力保存
            cosmos_container.upsert_item({
                    'id': event.source.user_id,
                    'user_id': event.source.user_id,
                    'question': 3,
                    'pclass': item['pclass'],
                    'age': item['age'],
                    'sibsp': event.message.text
                }
            )
            ## メッセージ送信
            line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='乗船している両親・子供の人数を教えてください。')) 
            
        elif question == 3:
            ## ユーザの入力保存
            cosmos_container.upsert_item({
                    'id': event.source.user_id,
                    'user_id': event.source.user_id,
                    'question': 4,
                    'pclass': item['pclass'],
                    'age': item['age'],
                    'sibsp': item['sibsp'],
                    'parch': event.message.text
                }
            )
            ## メッセージ送信
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text='性別はどちらですか？',
                    quick_reply=QuickReply(
                        items=[
                            QuickReplyButton(
                                action=PostbackAction(label="男性", data="male", display_text="男性")
                            ),
                            QuickReplyButton(
                                action=PostbackAction(label="女性", data="female", display_text="女性")
                            )
                        ])))
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='『予測』とメッセージを送ってみてください。'))

def allowSelfSignedHttps(allowed):
    # bypass the server certificate verification on client side
    if allowed and not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None):
        ssl._create_default_https_context = ssl._create_unverified_context


def save_data(user_id, step, face_id):
    """
    手続きの状態を保存
    """
    cosmos_container.upsert_item({
            'id': user_id,
            'user_id': user_id,
            'step': step,
            'face_id': face_id
        }
    )