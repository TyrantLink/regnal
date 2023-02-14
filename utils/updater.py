from asyncio import create_subprocess_shell,sleep
from os.path import exists
from client import Client
from os import _exit


class UpdateHandler:
	def __init__(self,client:Client,payload:dict) -> None:
		self.client = client
		self.payload = payload
		self.commits:list[dict] = payload.get('commits',[])
		self.modified = list(set([f for c in self.commits for f in c.get('modified')]))
		if self.modified == []: return
		self.actions:list[str] = []

	async def run(self) -> None:
		self.modified_handler()
		await self.pull()
		if self.actions: self.act()

	async def pull(self) -> None:
		"""pull commit from github"""
		if self.client.MODE == '/reg/nal':
			await (await create_subprocess_shell('touch updating;git reset --hard && git pull;rm updating')).wait()
		else:
			for i in range(100):
				await sleep(0.1)
				if not exists('updating'): break
		self.client.git_hash()

	def modified_handler(self) -> None:
		for filename in self.modified:
			match filename.split('/'):
				case [
					'main.py'|
					'client.py'|
					'utils',*_]:
					self.client.log.info(f'update detected, reboot required',to_db=False)
					self.actions.insert(0,'reboot')
				case ['extensions',*extension]: self.actions.append(f'extensions.{extension[0].split(".")[0]}')
				case _: pass

	def act(self) -> None:
		if 'reboot' in self.actions or 'extensions._shared_vars' in self.actions:
			self.client.log.info(f'rebooting...',to_db=False)
			_exit(0)
		for extension in self.actions:
			if extension == 'extensions.tet' and not self.client.MODE == 'tet': continue
			self.client.reload_extension(extension)
			self.client.log.info(f'[EXT_RELOAD] {extension.split(".")[-1]}',to_db=False)