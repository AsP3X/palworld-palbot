import json
import os
import nextcord
from nextcord.ext import commands
from util.gamercon_async import GameRCON
import asyncio
import datetime

class PalguardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.load_config()
        self.load_pals()
        self.timeout = 30

    def load_config(self):
        config_path = os.path.join('data', 'config.json')
        with open(config_path) as config_file:
            config = json.load(config_file)
            self.servers = config["PALWORLD_SERVERS"]

    def load_pals(self):
        pals_path = os.path.join('gamedata', 'pals.json')
        with open(pals_path) as pals_file:
            self.pals = json.load(pals_file)["creatures"]

    async def rcon_command(self, server_name, command):
        server = self.servers.get(server_name)
        if not server:
            return f"Server '{server_name}' not found."

        try:
            async with GameRCON(server["RCON_HOST"], server["RCON_PORT"], server["RCON_PASS"]) as pc:
                response = await asyncio.wait_for(pc.send(command), timeout=self.timeout)
                return response
        except Exception as error:
            return f"Error sending command: {error}"

    async def autocomplete_server(self, interaction: nextcord.Interaction, current: str):
        choices = [server for server in self.servers if current.lower() in server.lower()]
        await interaction.response.send_autocomplete(choices)

    async def autocomplete_palid(self, interaction: nextcord.Interaction, current: str):
        choices = [pal["name"] for pal in self.pals if current.lower() in pal["name"].lower()][:25]
        await interaction.response.send_autocomplete(choices)

    @nextcord.slash_command(default_member_permissions=nextcord.Permissions(administrator=True))
    async def palguard(self, _interaction: nextcord.Interaction):
        pass

    @palguard.subcommand(name="reload" ,description="Reload server configuration.")
    async def reloadcfg(self, interaction: nextcord.Interaction, server: str = nextcord.SlashOption(description="Select a server", autocomplete=True)):
        await interaction.response.defer(ephemeral=True)
        response = await self.rcon_command(server, "reloadcfg")
        await interaction.followup.send(f"**Response:** {response}")

    @reloadcfg.on_autocomplete("server")
    async def on_autocomplete_rcon(self, interaction: nextcord.Interaction, current: str):
        await self.autocomplete_server(interaction, current)

    @palguard.subcommand(description="Give a Pal to a player.")
    async def givepal(self, interaction: nextcord.Interaction, steamid: str = nextcord.SlashOption(description="SteamID/UID of the player."), palid: str = nextcord.SlashOption(description="The ID of the Pal.", autocomplete=True), level: str = nextcord.SlashOption(description="Level of the Pal"), server: str = nextcord.SlashOption(description="Select a server", autocomplete=True)):
        await interaction.response.defer(ephemeral=True)
        pal_id = next((pal["id"] for pal in self.pals if pal["name"] == palid), None)
        if not pal_id:
            await interaction.followup.send("Pal ID not found.", ephemeral=True)
            return
        asyncio.create_task(self.rcon_command(server, f"givepal {steamid} {pal_id} {level}"))
        embed = nextcord.Embed(title=f"Palguard Pal - {server}", color=nextcord.Color.blue())
        embed.description = f"Giving {palid} to {steamid}."
        await interaction.followup.send(embed=embed)

    @givepal.on_autocomplete("server")
    async def on_autocomplete_rcon(self, interaction: nextcord.Interaction, current: str):
        await self.autocomplete_server(interaction, current)

    @givepal.on_autocomplete("palid")
    async def on_autocomplete_pals(self, interaction: nextcord.Interaction, current: str):
        await self.autocomplete_palid(interaction, current)

def setup(bot):
    config_path = os.path.join('data', 'config.json')
    with open(config_path) as config_file:
        config = json.load(config_file)
    
    if config.get("PALGUARD_ACTIVE", False):
        cog = PalguardCog(bot)
        bot.add_cog(cog)
    else:
        print("Palguard disabled by default. Please enable it in config.json")