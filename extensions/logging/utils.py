from discord.errors import NotFound,Forbidden
from discord import Embed,Guild
from client import Client


class utils:
	def __init__(self,client:Client) -> None:
		self.client = client

	async def gen_embed(self,guild:Guild,message_id:int,limit:int=25,doc:dict=None) -> Embed:
		if doc is None: doc:dict = await self.client.db.message(message_id).read()
		if doc is None: return False
		try: channel = guild.get_channel_or_thread(doc.get('channel')) or await guild.fetch_channel(doc.get('channel'))
		except (NotFound,Forbidden): raise ValueError(f'channel not found\nplease use </logging get:{[cmd.id for cmd in self.client.walk_application_commands() if cmd.qualified_name == "logging get"][0]}> with the message_id `{doc.get("_id")}` and the raw option set to `True`')
		try: author = guild.get_member(doc.get('author')) or await guild.fetch_member(doc.get('author')) or self.client.get_user(doc.get('author')) or await self.client.fetch_user(doc.get('author'))
		except (NotFound,Forbidden): raise ValueError(f'author not found, they may have deleted their account\nplease use </logging get:{[cmd.id for cmd in self.client.walk_application_commands() if cmd.qualified_name == "logging get"][0]}> with the message_id `{doc.get("_id")}` and the raw option set to `True`')
		logs = doc.get('logs')[limit*-1:]
		mode = logs[-1][1]
		embed = Embed()
		embed.set_author(name=author.display_name,icon_url=author.display_avatar.url,url=author._user.jump_url)
		footer = [('message',f'id: {doc.get("_id")}'),('author',f'id: {author.id}')]
		match mode:
			case 'original':
				embed.color = 0x69ff69
				embed.description = f'{author.mention} sent a '
				try: message = await channel.fetch_message(doc.get('_id'))
				except (NotFound,Forbidden): embed.description += f'message in {channel.mention}'
				else: embed.description += f'[message](<{message.jump_url}>) in {channel.mention}'
			case 'edited':
				embed.color = 0xffff69
				embed.description = f'{author.mention} edited a '
				try: message = await channel.fetch_message(doc.get('_id'))
				except (NotFound,Forbidden): embed.description += f'message in {channel.mention}'
				else: embed.description += f'[message](<{message.jump_url}>) in {channel.mention}'
			case 'deleted':
				embed.color = 0xff6969
				embed.description = f'message by {author.mention} was deleted in {channel.mention}'
				if (deleted_by:=doc.get('deleted_by')) is not None: deleted_by = guild.get_member(deleted_by) or await guild.fetch_member(deleted_by)
				if deleted_by is not None:
					embed.description += f' by {deleted_by.mention}'
					footer.append(('deleter',f'id: {deleted_by.id}'))
					embed.set_footer(icon_url=deleted_by.avatar)
		try:
			if (replying_to:=doc.get('replying_to')) is not None: replying_to = await channel.fetch_message(replying_to)
		except (NotFound,Forbidden): pass
		else:
			if replying_to is not None:
				embed.description += f'\n\n[replying to {str(replying_to.author)}](<{replying_to.jump_url}>)'
				footer.append(('reply',f'id: {replying_to.id}'))
		width = max([len(l) for l in logs])
		for log in logs: embed.add_field(name=f'{log[1].upper().ljust(width)} <t:{log[0]}:t>',value=log[2] or '​',inline=False)
		width = max([len(f) for f,i in footer])
		embed.set_footer(text='\n'.join([f'{l.ljust(width)} {i}' for l,i in footer]),icon_url=embed.footer.icon_url)
		
		return embed
