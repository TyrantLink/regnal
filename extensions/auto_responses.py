from regex import sub,search,split,fullmatch,escape,finditer,IGNORECASE
from utils.classes import MixedUser,AutoResponse
from asyncio import sleep,create_task
from discord.ext.commands import Cog
from discord.errors import Forbidden
from discord import Message,Thread
from urllib.parse import quote
from random import choices
from client import Client
from time import time
from re import split


class auto_response_listeners(Cog):
	def __init__(self,client:Client) -> None:
		self.client = client
		self.cooldowns = {'au':{},'db':{}}
		self.timeouts = []

	async def timeout(self,message_id:int) -> None:
		self.timeouts.append(message_id)
		await sleep(5)
		try: self.timeouts.remove(message_id)
		except ValueError: pass

	@Cog.listener()
	async def on_message(self,message:Message,user:MixedUser=None) -> None:
		if message is None or message.author.id == self.client.user.id: return
		# ignore webhooks except pk
		if message.webhook_id is not None and user is None: return
		create_task(self.timeout(message.id))

		if message.guild:
			try: guild = await self.client.db.guild(message.guild.id).read()
			except: guild = await self.client.db.guild(0).read()
		else: guild = await self.client.db.guild(0).read()
		if guild is None: return

		if guild.get('config',{}).get('general',{}).get('pluralkit',False) and user is None:
			if (pk:=await self.client.pk.get_message(message.id)):
				if pk is not None and pk.original == message.id:
					await self.on_message(self.client.get_message(pk.id),MixedUser('pluralkit',message.author,
						id=pk.member.uuid,
						bot=False))
					return
		if user is None: user = message.author

		try:
			if (user.bot or
				await self.client.db.user(user.id).config.general.ignored.read() or
				user.id in await self.client.db.inf('/reg/nal').banned_users.read()):
					return
		except: return

		if message.content is None: return
		if message.guild is None:
			await message.channel.send('https://regn.al/dm.png')
			return

		channel = message.channel.parent if isinstance(message.channel,Thread) else message.channel
		if time()-self.cooldowns['au'].get(message.author.id if guild['config']['auto_responses']['cooldown_per_user'] else message.channel.id,0) > guild['config']['auto_responses']['cooldown']:
			match guild['config']['auto_responses']['enabled']:
				case 'enabled':
					if await self.listener_auto_response(message,user): return
				case 'whitelist' if channel.id in guild['data']['auto_responses']['whitelist']:
					if await self.listener_auto_response(message,user): return
				case 'blacklist' if channel.id not in guild['data']['auto_responses']['blacklist']:
					if await self.listener_auto_response(message,user): return
				case 'disabled': pass
		if time()-self.cooldowns['db'].get(message.author.id if guild['config']['auto_responses']['cooldown_per_user'] else message.channel.id,0) > guild['config']['dad_bot']['cooldown']:
			match guild['config']['dad_bot']['enabled']:
				case 'enabled':
					if await self.listener_dad_bot(message,user): return
				case 'whitelist' if channel.id in guild['data']['dad_bot']['whitelist']:
					if await self.listener_dad_bot(message,user): return
				case 'blacklist' if channel.id not in guild['data']['dad_bot']['blacklist']:
					if await self.listener_dad_bot(message,user): return
				case 'disabled': pass

	def au_check(self,responses:list[AutoResponse],message:str) -> AutoResponse|None:
		for au in responses:
			match au.method:
				case 'exact':
					if fullmatch((au.trigger if au.regex else escape(au.trigger))+r'(\.|\?|\!)*',message,0 if au.case_sensitive else IGNORECASE):
						return au
				case 'contains':
					if search(rf'(^|\s){au.trigger if au.regex else escape(au.trigger)}(\.|\?|\!)*(\s|$)',message,0 if au.case_sensitive else IGNORECASE):
						return au
				case _: continue
		return None

	async def listener_auto_response(self,message:Message,user:MixedUser) -> None:
		content = message.content[:-9] if (delete_original:=message.content.endswith(' --delete')) else message.content
		au = (self.client.au.match(content,{'custom':True,'guild':str(message.guild.id)}) or
			self.client.au.match(content,{'custom':False,'guild':str(message.guild.id)}) or
			self.client.au.match(content,{'custom':False,'guild':None}))
		if au is None: return False

		if au.trigger in await self.client.db.guild(message.guild.id).data.auto_responses.disabled.read(): return False
		weights,responses = zip(*[(w,r) for w,r in [(None,au.response)]+au.alt_responses])
		auto_weight = (100-sum(filter(None,weights)))/weights.count(None)
		response = choices(responses,[w or auto_weight for w in weights])[0]
		if response is None: return False
		if au.nsfw and not message.channel.nsfw: return False
		if au.user is not None and str(message.author.id) != au.user: return False
		if au.file: response = (f'https://regn.al/gau/{message.guild.id}/' if au.guild else 'https://regn.al/au/')+quote(response)

		if message.id not in self.timeouts: return False
		try: await message.channel.send(response)
		except Forbidden: return False
		original_deleted = False
		if delete_original and (content.lower() == au.trigger or au.regex) and au.file:
			try: await message.delete(reason='auto response deletion')
			except Forbidden: pass
			else:
				original_deleted = True
				await self.client.log.info(f'auto response trigger deleted by {message.author}')
		for delay,followup in au.followups:
			async with message.channel.typing():
				await sleep(delay)
			await message.channel.send(followup)

		if not au.custom:
			user_data = await self.client.db.user(user.id).read()
			if au._id not in user_data.get('data',{}).get('au') and not user_data.get('config',{}).get('general',{}).get('no_track',True):
				await self.client.db.user(user.id).data.au.append(au._id)

		self.cooldowns['au'].update({user.id if await self.client.db.guild(message.guild.id).config.auto_responses.cooldown_per_user.read() else message.channel.id:int(time())})
		await self.client.log.listener(message,id=au._id,category=au.method,trigger=au.trigger,response=response,original_deleted=original_deleted)
		return True

	def rand_name(self,message:Message,splitter:str) -> str:
		options,weights = [message.guild.me.display_name if message.guild else self.client.user.name],[]
		if splitter in ["i'm"]:
			options += ['proud of you','not mad, just disappointed']
			weights += [0.005,0.01]
		weights.insert(0,1-sum(weights))
		return choices(options,weights)[0]

	async def listener_dad_bot(self,message:Message,user:MixedUser) -> None:
		response = ''
		input = sub(r"""<(@!|@|@&)\d{10,25}>|@everyone|@here|(https?:\/\/[^\s]+.)""",'[REDACTED]',sub(r'\*|\_|\~|\`|\|','',message.content))
		splitters = "i'm|im|i am|i will be|i've|ive"
		for s in finditer(splitters,input,IGNORECASE):
			if (s is None or
				(s.span()[0] != 0 and input[s.span()[0]-1] != ' ') or
				(s.span()[1] < len(input) and input[s.span()[1]] != ' ')): continue
			response,splitter = ''.join(split(s.captures()[0],input,1,IGNORECASE)[1:]),s.captures()[0].lower()

		if response == '': return
		name = self.rand_name(message,splitter)

		if message.id not in self.timeouts: return False
		nl = '\n'
		out_message = f'hi{split(f"[,.;{nl}]",response)[0]}, {splitter} {name}'
		if len(out_message) > 2000: out_message = f'hi{response.split(".")[0][:1936]} (character limit), {splitter} {name}'
		try: await message.channel.send(out_message)
		except Forbidden: return False

		self.cooldowns['db'].update({user.id if await self.client.db.guild(message.guild.id).config.dad_bot.cooldown_per_user.read() else message.channel.id:int(time())})
		await self.client.log.listener(message,splitter=splitter,name=name)


def setup(client:Client) -> None:
	client._extloaded()
	client.add_cog(auto_response_listeners(client))