from discord.commands import Option as option,slash_command
from discord import Embed,Role,ApplicationContext
from discord.ext.commands import Cog
from ._shared_vars import bees,eightball
from aiohttp import ClientSession
from random import randint,choice
from datetime import datetime
from client import Client
from asyncio import sleep
from re import sub

class fun_commands(Cog):
	def __init__(self,client:Client) -> None:
		self.client = client
		self.bees_running = {}

	@slash_command(
		name='hello',
		description='say hello to /reg/nal?')
	async def slash_hello(self,ctx:ApplicationContext) -> None:
		await ctx.response.send_message(
			f'https://regn.al/{"regnal" if randint(0,100) else "erglud"}.png',
			ephemeral=await self.client.hide(ctx))

	@slash_command(
		name='roll',
		description='roll dice with standard roll format',
		options=[
			option(str,name='roll',description='standard roll format e.g. (2d6+1+2+1d6-2)')])
	async def slash_roll(self,ctx:ApplicationContext,roll:str) -> None:
		rolls,modifiers = [],0
		embed = Embed(
			title=f'roll: {roll}',
			color=await self.client.embed_color(ctx))

		roll = sub(r'[^0-9\+\-d]','',roll).split('+')
		for i in roll:
			if '-' in i and not i.startswith('-'):
				roll.remove(i)
				roll.append(i.split('-')[0])
				for e in i.split('-')[1:]:
					roll.append(f'-{e}')

		for i in roll:
			e = i.split('d')
			try: [int(r) for r in e]
			except:
				await ctx.response.send_message('no.',ephemeral=await self.client.hide(ctx))
				return
			match len(e):
				case 1:
					modifiers += int(e[0])
				case 2:
					if int(e[1]) < 1:
						await ctx.response.send_message('no.',ephemeral=await self.client.hide(ctx))
						return
					for f in range(int(e[0])):
						res = randint(1,int(e[1]))
						rolls.append(res)
				case _: await ctx.response.send_message('invalid input',ephemeral=await self.client.hide(ctx))
		if rolls and not len(rolls) > 1024: embed.add_field(name='rolls:',value=rolls,inline=False)
		if modifiers != 0: embed.add_field(name='modifiers:',value=f"{'+' if modifiers > 0 else ''}{modifiers}",inline=False)
		embed.add_field(name='result:',value='{:,}'.format(sum(rolls)+modifiers))
		await ctx.response.send_message(embed=embed,ephemeral=await self.client.hide(ctx))

	@slash_command(
		name='time',
		description='/reg/nal can tell time.')
	async def slash_time(self,ctx:ApplicationContext) -> None:
		await ctx.response.send_message(datetime.now().strftime("%H:%M:%S.%f"),ephemeral=await self.client.hide(ctx))
	
	@slash_command(
		name='8ball',
		description='ask the 8ball a question',
		options=[
			option(str,name='question',description='question to ask',max_length=256)])
	async def slash_eightball(self,ctx:ApplicationContext,question:str) -> None:
		embed = Embed(title=question,description=f'**{choice(eightball)}**',color=await self.client.embed_color(ctx))
		embed.set_author(name=f'{self.client.user.name}\'s eighth ball',icon_url='https://regn.al/8ball.png')
		await ctx.response.send_message(embed=embed,ephemeral=await self.client.hide(ctx))

	@slash_command(
		name='color',
		description='generate a random color')
	async def slash_color(self,ctx) -> None:
		color = hex(randint(0,16777215)).upper()
		res = [f'#{color[2:]}']
		res.append(f'R: {int(color[2:4],16)}')
		res.append(f'G: {int(color[4:6],16)}')
		res.append(f'B: {int(color[6:8],16)}')
		await ctx.response.send_message(
			embed=Embed(
				title='random color:',
				description=f"""#{color[2:]}
				R: {int(color[2:4],16)}
				G: {int(color[4:6],16)}
				B: {int(color[6:8],16)}""",
				color=int(color,16)),
			ephemeral=await self.client.hide(ctx))

	@slash_command(
		name='random',
		description='get random user with role',
		guild_only=True,
		options=[
			option(Role,name='role',description='role to roll users from'),
			option(bool,name='ping',description='ping the result user? (requires mention_everyone)')])
	async def slash_random(self,ctx:ApplicationContext,role:Role,ping:bool) -> None:
		if ping and not ctx.author.guild_permissions.mention_everyone: return
		result = choice(role.members)
		await ctx.response.send_message(f"{result.mention if ping else result} was chosen!",ephemeral=await self.client.hide(ctx))

	async def acquire_hentai(self) -> tuple:
		id = randint(1,423204)
		async with ClientSession() as session:
			async with session.get(f'https://nhentai.net/api/gallery/{id}') as res:
				match res.status:
					case 200: return (await res.json(),id)
					case _: return ({'error':'cock'},id)

	@slash_command(
		name='hentai',
		description='get a random nhentai doujin to read.',
		nsfw=True)
	async def slash_hentai(self,ctx:ApplicationContext) -> None:
		await ctx.response.send_message(f'this is broken because i\'m too lazy to bypass cloudflare\nplease try again if i mention this command in the change-log',ephemeral=await self.client.hide(ctx))
		return
		await ctx.defer(ephemeral=await self.client.hide(ctx))
		for i in range(10):
			out,id = await self.acquire_hentai()
			if 'error' not in out.keys(): break
		else:
			await ctx.followup.send(f'failed to acquire hentai, try again in like, five minutes',ephemeral=await self.client.hide(ctx))
			return
	
		embed = Embed(
				title='random nhentai:',
				description=f'https://nhentai.net/g/{id}',
				color=await self.client.embed_color(ctx))
		img_url = f'https://t.nhentai.net/galleries/{out["media_id"]}/cover.'
		match out['images']['cover']['t']:
			case 'p': img_url += 'png'
			case 'j': img_url += 'jpg'
			case 'g': img_url += 'gif'
		embed.set_image(url=img_url)
		info = {'parodies':[],'characters':[],'tags':[],'artists':[],'groups':[],'languages':[],'pages':[str(len(out["images"]["pages"]))]}
		for i in out['tags']:
			match i['type']:
				case 'parody': info['parodies'].append(i['name'])
				case 'character': info['characters'].append(i['name'])
				case 'tag': info['tags'].append(i['name'])
				case 'artist': info['artists'].append(i['name'])
				case 'group': info['groups'].append(i['name'])
				case 'language': info['languages'].append(i['name'])
				case 'category': pass
				case _: raise
		for k,v in info.items():
			if v: embed.add_field(name=k,value=', '.join(v),inline=True)
		await ctx.followup.send(embed=embed,ephemeral=await self.client.hide(ctx))

	@slash_command(
		name='bees',
		description='bees.',
		guild_only=True)
	async def slash_bees(self,ctx:ApplicationContext) -> None:
		if ctx.channel.name != 'spam':
			await ctx.response.send_message('bees are not allowed here.',ephemeral=await self.client.hide(ctx))
			return
		if self.bees_running.get(ctx.guild.id,False):
			await ctx.response.send_message('there may only be one bees at a time.',ephemeral=await self.client.hide(ctx))
			return
		await ctx.response.send_message('why. you can\'t turn it off. this is going to go on for like, 2 hours, 44 minutes, and 30 seconds. why.',ephemeral=await self.client.hide(ctx))
		self.bees_running[ctx.guild.id] = True
		for line in bees:
			try: await ctx.channel.send(line)
			except Exception: pass
			await sleep(5)
		self.bees_running[ctx.guild.id] = False

def setup(client:Client) -> None:
	client._extloaded()
	client.add_cog(fun_commands(client))