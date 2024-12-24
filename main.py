import json
import os

from langchain_community.llms import Tongyi
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()


class CustomHistoryManager:
    def __init__(self):
        self.history = []

    def add_message(self, role, content):
        self.history.append({"role": role, "content": content})

    def get_history(self):
        return "\n".join(f"{msg['role']}: {msg['content']}" for msg in self.history)

    def clear_history(self):
        self.history.clear()


class BaseRole:
    def __init__(self):
        self.llm = Tongyi(model="qwen-turbo", temperature=1)

    def invoke(self, text):
        return self.llm.invoke(text)  # 运行


class Npc(BaseRole):
    def __init__(self, name, traits, backstory):
        super().__init__()
        self.name = name
        self.traits = traits
        self.backstory = backstory
        self.system_prompt = f"""现在由你来扮演{name}, 你的特点是{traits}, 你的背景是{backstory}。根据以下对话历史:"""

        self.template = (
            self.system_prompt + """{history}。你的回答是:""" + f"{self.name}:"
        )
        self.prompt_template = PromptTemplate(
            input_variables=["history"], template=self.template
        )


class System(BaseRole):
    def __init__(self):
        super().__init__()
        self.template = """你是一个评判专家。根据用户的目标和他的对话记录，判断该用户是否实现了他的目标。对话历史:{history}。用户的目标：{user_target}。根据以上对话历史，你认为用户完成了他的目标吗？用yes或no回答。你的回答:"""
        self.prompt_template = PromptTemplate(
            input_variables=["history", "user_target"], template=self.template
        )

    def check_user_target_completed(self, user_target, history):
        # 判断当前一幕用户的目标是否达成, 需要return True or False
        formatted_prompt = self.prompt_template.format(
            history=history, user_target=user_target
        )
        if debug:
            print(f"【DEBUG】system: {formatted_prompt}")
        response = self.invoke(formatted_prompt)
        if debug:
            print(f"【DEBUG】system: {response}")
        return "yes" in response.lower()


class Game:
    def __init__(self, config_path):
        with open(config_path, "r", encoding="utf-8") as file:
            self.config = json.load(file)
        #
        self.current_episode = 0
        self.current_scene = 0
        # 初始化自定义历史管理器
        self.custom_history_manager = CustomHistoryManager()
        # 初始化NPC
        self.user_name = self.config["game"]["player"]["name"]
        self.system = System()
        self.npcs = {
            npc["name"]: Npc(npc["name"], npc["traits"], npc["backstory"])
            for npc in self.config["game"]["npcs"]
        }

    def start_game(self):
        print("【系统】:", self.config["game"]["background"])
        self.play_scene()

    def play_scene(self):
        episode = self.config["game"]["episodes"][self.current_episode]
        scene = episode["scenes"][self.current_scene]
        print(
            f'【系统】:第{episode["episodeNumber"]}章节, 第{scene["sceneId"]}幕, {scene["description"]}'
        )

        target_completed = False
        for dialogue in scene["start_dialogues"]:
            print(f"【{dialogue['speaker']}】: {dialogue['text']}")
        while not target_completed:
            # 获取用户输入
            user_input = input("【用户】:")
            self.custom_history_manager.add_message(self.user_name, user_input)
            # NPC回答（当前同一幕仅支持NPC）
            npc_name = scene["npcs"][0]
            npc = self.npcs[npc_name]

            formatted_prompt = npc.prompt_template.format(
                history=self.custom_history_manager.get_history()
            )
            if debug:
                print(f"【DEBUG】:{npc_name}: {formatted_prompt}")
            response = npc.invoke(formatted_prompt)
            if debug:
                print(f"【DEBUG】:{npc_name}: {response}")
            self.custom_history_manager.add_message(npc_name, response)
            target_completed = self.system.check_user_target_completed(
                scene["target"], self.custom_history_manager.get_history()
            )
        for dialogue in scene["end_dialogues"]:
            print(f"【{dialogue['speaker']}】: {dialogue['text']}")
        self.advance_scene()

    def advance_scene(self):
        self.current_scene += 1
        episode = self.config["game"]["episodes"][self.current_episode]
        if self.current_scene >= len(episode["scenes"]):
            self.current_episode += 1
            self.current_scene = 0
        # 清空聊天历史
        self.custom_history_manager.clear_history()
        if self.current_episode >= len(self.config["game"]["episodes"]):
            print("游戏结束")
        else:
            # 开启下一幕
            self.play_scene()


if __name__ == "__main__":
    debug = True
    game = Game("./game/小蝌蚪找妈妈.json")
    game.start_game()
