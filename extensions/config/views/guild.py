from discord.ui import Button,button,Select,string_select,channel_select,role_select,InputText
from discord import Interaction,Embed,SelectOption,Guild,Member
from extensions._shared_vars import config_info
from client import Client,EmptyView,CustomModal
from .configure_list import configure_list_view
from .custom_au import custom_au_view

class guild_config(EmptyView):
	def __init__(self,back_view:EmptyView,client:Client,user:Member,guild:Guild,embed_color:int=None) -> None:
		super().__init__(timeout=0)
		self.back_view   = back_view
		self.client      = client
		self.user        = user
		self.guild       = guild
		self.embed       = Embed(title='guild config',color=embed_color or back_view.embed.color)
		self.config      = {}
		self.category    = None
		self.selected    = None
		self.embed.set_author(name=self.guild.name,icon_url=self.guild.icon.url if self.guild.icon else 'https://regn.al/discord.png')
		if back_view is not None: self.add_item(self.back_button)
		self.add_items(self.category_select)
		options = [SelectOption(label='general',description='general options')]
		if self.user.guild_permissions.view_audit_log or self.user.id == self.client.owner_id:
			options.append(SelectOption(label='logging',description='logging config'))
		if self.user.guild_permissions.manage_channels or self.user.id == self.client.owner_id:
			options.append(SelectOption(label='qotd',description='qotd config'))
			options.append(SelectOption(label='talking_stick',description='talking stick config'))
		if self.user.guild_permissions.manage_messages or self.user.id == self.client.owner_id:
			options.append(SelectOption(label='auto_responses',description='auto response config'))
			options.append(SelectOption(label='dad_bot',description='dad bot config'))
		self.get_item('category_select').options = options

	@property
	def config_type(self) -> str|None:
		return config_info.get('guild',{}).get(self.category,{}).get(self.selected,{}).get('type',None)

	async def start(self) -> bool:
		pass

	def reload_embed(self) -> None:
		self.embed.clear_fields()
		category_data = config_info.get('guild',{}).get(self.category,{})
		for k,v in self.config.items():
			if v is not None:
				match category_data.get(k,{}).get('type'):
					case 'channel': v = f'<#{v}>'
					case 'role'   : v = f'<@&{v}>'
			self.embed.add_field(name=k,value=v)
		if self.selected is None: self.embed.description = None
		else: self.embed.description = category_data.get(self.selected,{}).get('description',None)

	async def reload_config(self) -> None:
		self.config = await self.client.db.guilds.read(self.guild.id,['config',self.category])
		options = [SelectOption(label=k,description=v.get('description','').split('\n')[0][:100]) for k,v in config_info.get('guild',{}).get(self.category,{}).items()]
		for option in options: option.default = option.label == self.selected
		self.get_item('option_select').options = options
		
	async def write_config(self,value) -> None:
		match self.selected:
			case 'embed_color': 
				value = value.replace('#','')
				self.embed.color = int(value,16)
			case 'max_roll':
				value = int(value)
				if not (16384 > value > 2): raise
			case 'cooldown':
				value = int(value)
		await self.client.db.guilds.write(self.guild.id,['config',self.category,self.selected],value)
		await self.reload_config()
		self.reload_embed()
	
	@button(
		label='<',style=2,
		custom_id='back_button',row=2)
	async def back_button(self,button:Button,interaction:Interaction) -> None:
		if self.category is None:
			await interaction.response.edit_message(view=self.back_view,embed=self.back_view.embed)
			return
		self.category = None
		self.selected = None
		self.embed.title = 'guild config'
		self.embed.description = None
		self.embed.clear_fields()
		self.clear_items()
		if self.back_view is not None: self.add_item(self.back_button)
		self.add_item(self.category_select)
		await interaction.response.edit_message(view=self,embed=self.embed)

	@string_select(
		placeholder='select a config category',
		custom_id='category_select',row=0)
	async def category_select(self,select:Select,interaction:Interaction) -> None:
		self.category = select.values[0]
		self.clear_items()
		self.add_items(self.back_button,self.option_select)
		if self.category == 'auto_responses': self.add_item(self.custom_au_button)
		await self.reload_config()
		self.reload_embed()
		await interaction.response.edit_message(view=self,embed=self.embed)

	@string_select(
		placeholder='select an option',
		custom_id='option_select',row=0,min_values=0)
	async def option_select(self,select:Select,interaction:Interaction) -> None:
		self.clear_items()
		if select.values:
			self.selected = select.values[0]
			self.reload_embed()
			self.add_items(self.back_button,self.option_select,self.reset_button)
			match self.config_type:
				case 'bool': self.add_items(self.enable_button,self.disable_button)
				case 'ewbd':
					self.add_items(self.enable_button,self.whitelist_button,self.blacklist_button,self.disable_button)
					if (mode:=self.config.get(self.selected,None)) in ['whitelist','blacklist']:
						self.add_item(self.configure_list_button)
						self.get_item('configure_list_button').label = f'configure {mode}'
				case 'modal': self.add_item(self.modal_button)
				case 'channel': self.add_item(self.channel_select)
				case 'role': self.add_item(self.role_select)
				case _: raise
			options = select.options.copy()
			for option in options: option.default = option.label == self.selected
			select.options = options
		else:
			self.selected = None
			self.reload_embed()
			self.add_items(self.back_button,self.option_select)
			for option in select.options: option.default = False
			if self.category == 'auto_responses': self.add_item(self.custom_au_button)
		await interaction.response.edit_message(view=self,embed=self.embed)
	
	@channel_select(
		placeholder='select a channel',
		custom_id='channel_select',row=1,min_values=0)
	async def channel_select(self,select:Select,interaction:Interaction) -> None:
		await self.write_config(select.values[0].id if select.values else None)
		await interaction.response.edit_message(embed=self.embed,view=self)
		if select.values:
			if not select.values[0].can_send():
				await interaction.followup.send(ephemeral=True,embed=Embed(title='warning!',color=0xffff69,
					description=f'i don\'t have permission to send messages in {select.values[0].mention}\nthe channel will still be set, but you should probably fix that.'))

	@role_select(
		placeholder='select a role',
		custom_id='role_select',row=1,min_values=0)
	async def role_select(self,select:Select,interaction:Interaction) -> None:
		await self.write_config(select.values[0].id if select.values else None)
		await interaction.response.edit_message(embed=self.embed,view=self)

	@button(
		label='enable',style=3,
		custom_id='enable_button',row=2)
	async def enable_button(self,button:Button,interaction:Interaction) -> None:
		match self.config_type:
			case 'ewbd': await self.write_config('enabled')
			case 'bool': await self.write_config(True)
			case _     : raise
		self.remove_item(self.configure_list_button)
		await interaction.response.edit_message(embed=self.embed,view=self)

	@button(
		label='whitelist',style=1,
		custom_id='whitelist_button',row=2)
	async def whitelist_button(self,button:Button,interaction:Interaction) -> None:
		await self.write_config('whitelist')
		self.add_item(self.configure_list_button)
		self.get_item('configure_list_button').label = f'configure whitelist'
		await interaction.response.edit_message(embed=self.embed,view=self)

	@button(
		label='blacklist',style=1,
		custom_id='blacklist_button',row=2)
	async def blacklist_button(self,button:Button,interaction:Interaction) -> None:
		await self.write_config('blacklist')
		self.add_item(self.configure_list_button)
		self.get_item('configure_list_button').label = f'configure blacklist'
		await interaction.response.edit_message(embed=self.embed,view=self)

	@button(
		label='disable',style=4,
		custom_id='disable_button',row=2)
	async def disable_button(self,button:Button,interaction:Interaction) -> None:
		match self.config_type:
			case 'ewbd': await self.write_config('disabled')
			case 'bool': await self.write_config(False)
			case _     : raise
		self.remove_item(self.configure_list_button)
		await interaction.response.edit_message(embed=self.embed,view=self)
	
	@button(
		label='set',style=1,
		custom_id='modal_button',row=2)
	async def modal_button(self,button:Button,interaction:Interaction) -> None:
		modal = CustomModal(self,f'set {self.selected}',
			[InputText(label=self.selected,
				max_length=config_info.get('guild',{}).get(self.category,{}).get(self.selected,{}).get('max_length',None))])
		await interaction.response.send_modal(modal)
		await modal.wait()
		await self.write_config(modal.children[0].value)
		await modal.interaction.response.edit_message(embed=self.embed,view=self)

	@button(
		label='reset to default',style=4,
		custom_id='reset_button',row=3)
	async def reset_button(self,button:Button,interaction:Interaction) -> None:
		await self.write_config(config_info.get('guild',{}).get(self.category,{}).get(self.selected,{}).get('default',None))
		await interaction.response.edit_message(view=self,embed=self.embed)

	@button(
		label='configure',style=1,row=3,
		custom_id='configure_list_button')
	async def configure_list_button(self,button:Button,interaction:Interaction) -> None:
		mode = self.config.get(self.selected,None)
		embed = Embed(
			title=f'configure {self.category} {mode}',
			description=f'currently {mode}ed:\n'+('\n'.join([f'<#{i}>' for i in await self.client.db.guilds.read(interaction.guild.id,['data',self.category,mode])]) or 'None'),
			color=self.embed.color)
		await interaction.response.edit_message(embed=embed,view=configure_list_view((self.category,mode),self,self.client,embed))

	@button(
		label='custom auto responses',style=1,row=2,
		custom_id='custom_au_button')
	async def custom_au_button(self,button:Button,interaction:Interaction) -> None:
		embed = Embed(
			title=f'custom auto responses',
			color=self.embed.color)
		await interaction.response.edit_message(embed=embed,view=custom_au_view(self,self.client,embed,await self.client.db.guilds.read(interaction.guild.id,['data','auto_responses','custom'])))

		