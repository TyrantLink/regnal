from google.cloud.texttospeech import TextToSpeechAsyncClient
from .models import UserTTSProfile,TTSMessage,GuildTTS
from discord import Member,Guild,VoiceChannel
from utils.pycord_classes import SubCog
from .models import TTSMessage
from asyncio import Queue
from client import Client


class ExtensionTTSSubCog(SubCog):
	def __init__(self,client:Client) -> None:
		self.client:Client
		self.tts:TextToSpeechAsyncClient
		self.guilds:dict[int,GuildTTS]
		self.text_corrections:dict[str,str]
		super().__init__()

	async def reload_voices(self) -> None: ...
	async def get_user_profile(self,user:Member) -> UserTTSProfile: ...
	async def generate_audio(self,message:str,profile:UserTTSProfile) -> TTSMessage: ...
	async def add_message_to_queue(self,message:TTSMessage,guild:Guild) -> None: ...
	def process_message(self,message:str) -> str: ...
	def process_text_correction(self,message:str) -> str: ...
	async def create_queue(self,guild_id:int) -> None: ...
	async def process_queue(self,guild:Guild) -> None: ...
	async def join_channel(self,channel:VoiceChannel) -> None: ...
	async def disconnect(self,guild:Guild) -> None: ...