import discord
from discord.ext import commands, tasks
import config
import asyncio
from datetime import datetime, time
from pytz import timezone
import openai
from openai import OpenAI
import json

# Botトークンを設定
TOKEN = config.DISCORD_TOKEN


# OpenAI APIキーを設定
client = OpenAI(api_key = config.OPENAI_KEY)

# logファイルパス
player_point_log = "player_point_log.json"
player_right_log = "player_right_log.json"

# 問題作成
messages = [
    {"role": "system", "content": "あなたは優れた謎なぞ作成者です。"},
    {"role": "user", "content": """一次方程式を一文だけ出力し、それをキー(str型)として、解答を値(int型)とする辞書型({問題:答え})をPythonの辞書の形で出力してください。
     解答は **正の整数(1以上の自然数)** であること。
     
     余計な説明やコメントは不要です。
     
     出力例:
     {"6x - 60 = 240": 50}
     """}
]

def is_single_key_value_dict(var): #chatGPT
    # 変数が辞書型かつ1組のキーと値のペアを持つか確認
    return isinstance(var, dict) and len(var) == 1

def check_none_in_dict(d): #chatGPT
    # 辞書内のキーか値がNoneの場合はFalseを返す
    for key, value in d.items():
        if key is None or value is None:
            return False
    return True


def make_question(messages): #chatGPT
    # OpenAIのAPIを呼び出し、与えられたメッセージに対する応答を取得
    completion = client.chat.completions.create(
        model="gpt-4",
        messages=messages
    )
    try:
        response = eval(completion.choices[0].message.content)
        if is_single_key_value_dict(response) == True and check_none_in_dict(response) == True:
           return response
        else:
           make_question(messages)

    except Exception as e:
        make_question(messages)

# 問題登録
quest_ans = {"世界一高い山は?" : "富士山", "世界一大きい湖は？" : "琵琶湖" , "村井くんの好きな食べ物は？": "ラーメン"}

# 参加者登録
player_id = {"maron" : 386135056323706883,"げんが" : 361419327037243392,"UC_fly18" : 826376106919067678, "としき" : 1329367045476847616, "アイリス" : 959108811333992478, "shohei_tanabe" : 1120305598421028865, "kairi_sasaki_t20": 1331111102074851360,"からと" : 1329723939722756259}

# チームを構成する最小人数
team_number = 2

# プレイヤー毎のポイント
player_point = {386135056323706883 : 0,361419327037243392 : 0,826376106919067678 : 0, 1329367045476847616 : 0, 959108811333992478 : 0, 1120305598421028865 : 0, 1331111102074851360 : 0, 1329723939722756259 : 0}


# プレイヤーごとの解答権
player_right = {386135056323706883 : True, 361419327037243392 : True, 826376106919067678 : True, 1329367045476847616 : True, 959108811333992478 : True, 1120305598421028865 : True, 1331111102074851360 : True, 1329723939722756259 : True}




# 変数をファイルに保存する関数(chatGPT)
def save_variables_to_json(data, file_path):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

# ファイルから変数を読み取る関数(chatGPT)
def load_variables_from_json(file_path):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON in {file_path}.")
        return None



# 今日の問題を選定
import random
def today_quest():
  # 問題を生成する
  q = list(make_question(messages).items())
  print(q[0])
  return q[0] #(問題, 答え)のタプル


# チーム分けの人数を決定 
def team(player_number, few_number): #(プレイヤーの数, チームの最小人数)
  global how_many_team
  a = []
  if player_number < few_number:
    print("チームが作れません")
  else:
    div = player_number // few_number # チームの数
    rem = player_number % few_number # 余っている人数
    a = [0] * div  
    for i in range(player_number):
      # 修正: j を div で割った余りをインデックスとして使用
      if i < player_number:  # 不要な条件を削除
        a[i % div] += 1  # i を div で割った余りをインデックスとして使用
    how_many_team = len(a)
  return a, how_many_team


# チーム分け
def team_make(player_id, team_number): #(参加者 → チーム)
  if len(player_id) < team_number:
    print("チームが組めません")
  else:
    player_list = list(player_id.values())
    #リストをランダムに入れ替え
    random.shuffle(player_list)
    # プレイヤーごとのチーム割り当て辞書
    team_assignments = {}
    count = 0
    # プレイヤーを割り振る
    team_div, how_many_team = team(len(player_id), team_number)
    for i,a in enumerate(team_div):
      for j in range(a):
        team_assignments[player_list[count]] = i + 1
        count += 1

  return team_assignments, how_many_team

# チーム毎に問題を決定 
def team_quest(team_number):
  team_quest = {}
  team_ans = {}
  team, how_many_team = team_make(player_id,team_number)
  team_keys = list(set(team.values()))
  
  for i in range(how_many_team):
    team_quest[team_keys[i]],  team_ans[team_keys[i]] = today_quest()
  return team_quest, team_ans

# 問題分割
def divquestion (question, team_number): 
    if team_number <= 0:
        raise ValueError("分割後の要素数は正の整数である必要があります。")

    length = len(question)
    base_size = length // team_number  # 各要素の基本の長さ
    remainder = length % team_number   # 余り

    result = []
    start = 0

    for i in range(team_number):
        # 余りがある間は1文字多く割り当てる
        end = start + base_size + (1 if i < remainder else 0)
        result.append(question[start:end])
        start = end

    return result


# 参加者に問題を割り振る
def distribute (player_id, team_number): #(参加者 → 問題) questionにはquest_regiを代入
    player_question = {}
    player_answer = {}
    team_question, team_answer = team_quest(team_number) #(チーム → 問題) (チーム → 答え)
    player_team, how_many_team = team_make(player_id, team_number) #(参加者 → チーム)
    for player, team in player_team.items():
      if team_question.get(team) != None:
        player_question[player] = team_question[team]
        player_answer[player] = team_answer[team]
    return player_question, player_answer

# 割り振った問題を分割する
from collections import Counter
def re_distribute(player_id, team_number):
  player_question, player_answer = distribute(player_id, team_number)
  question_counts = Counter(player_question.values()) # 出題の問題の種類をカウントする
  split_questions = {}
  for question, count in question_counts.items():
    split_parts = divquestion(question, count)

    part_index = 0
    for player, q in player_question.items():
      if q == question:
        split_questions[player] = split_parts[part_index]
        part_index += 1
  return split_questions, player_answer


# ポイント加算
def point_add(player_point,id):
   player_point = load_variables_from_json(player_point_log)
   player_point = {int(key) : value for key, value in player_point.items()}  
   if player_point.get(id) != None:
      player_point[id] += 1
   save_variables_to_json(player_point, player_point_log)
   return player_point


#日付
current_date = None
new_date = None

#その日の(参加者ID → 問題)
player_question = {}

#その日の(参加者ID → 答え)
player_answer = {}

#以下discordの関

#インスタンスの設定
intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
intents.message_content = True
intents.members = True

# コマンド
bot = commands.Bot(command_prefix="!", intents=intents)

# 参加者にDMを送信
async def send_dm():
   global player_question
   global player_answer
   player_question, player_answer = re_distribute(player_id, team_number)
   for players, questions in player_question.items():
      user = bot.get_user(players)
      await user.send(questions)


# 1日1回DMを送る
@tasks.loop(time=time(0, 0))
async def send_message_every_day():
    global player_right
    for i in list(player_right.values()):
       i = True
    await send_dm()



# 答え合わせ
@bot.command()
async def answer(ctx,*, user_answer: int):
    global player_question
    global player_answer
    global player_right
    global player_point
    user_id = ctx.author.id
    player_right = load_variables_from_json(player_right_log)
    player_right = {int(key) : value for key, value in player_right.items()}  
    if player_right[user_id] == False:
        await ctx.send("解答は1日1度までです")
        return
    
    if player_answer.get(user_id) == user_answer:
       await ctx.send("正解です")
       point_add(player_point,user_id)
       player_right[user_id] = False
       save_variables_to_json(player_right, player_right_log)
    else:
       await ctx.send("違います")
       player_right[user_id] = False
       save_variables_to_json(player_right, player_right_log)



# ポイント確認
@bot.command()
async def check_point(ctx):
   global player_point
   player_point = load_variables_from_json(player_point_log)
   player_point = {int(key) : value for key, value in player_point.items()}  
   user_id = ctx.author.id
   await ctx.send(f"Your point is : {player_point.get(user_id)} ")

# 起動時
@bot.event
async def on_ready():
    #bot起動時に最初に実行すするprint文
    print(f"Logged in as {bot.user}")
    save_variables_to_json(player_point, player_point_log)
    save_variables_to_json(player_right, player_right_log)
    for i in player_id.values():
       user = bot.get_user(i)
       await user.send("ガチでゲームスタート")
    send_message_every_day.start()

# Botを実行
bot.run(TOKEN)