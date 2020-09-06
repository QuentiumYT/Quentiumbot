import discord, requests, re
from discord.ext import commands
from bs4 import BeautifulSoup
from QuentiumBot import HandleData, get_translations, get_config

# Basic command configs
cmd_name = "lyrics"
tran = get_translations()
aliases = [] if not tran[cmd_name]["fr"]["aliases"] else tran[cmd_name]["fr"]["aliases"].split("/")

class LyricsUtilities(commands.Cog):
    """Lyrics command in Utilities section"""

    def __init__(self, client):
        self.client = client

    @commands.command(
        name=cmd_name,
        aliases=aliases,
        pass_context=True
    )
    async def lyrics_cmd(self, ctx, *, music=None):
        # Get specific server data
        if isinstance(ctx.channel, discord.TextChannel):
            data = await HandleData.retrieve_data(self, ctx.message.guild)
            lang_server = data[0]
        else:
            lang_server = "en"
        cmd_tran = tran[cmd_name][lang_server]

        # Doesn't respond to bots
        if not ctx.message.author.bot == True:
            # No music given
            if not music:
                return await ctx.send(cmd_tran["msg_specify_music"])

            # Fetch the best results with the args
            request_url = "https://api.genius.com/search/"
            query = {"q": music}
            headers = {"Authorization": "Bearer " + get_config("GLOBAL", "token_genius")}
            r = requests.get(request_url, params=query, headers=headers).json()

            # Genius API return no music
            if not r["response"]["hits"]:
                return await ctx.send(cmd_tran["msg_not_found"])

            # Get the lyrics path and request the webpage
            path_lyrics = r["response"]["hits"][0]["result"]["path"]
            genius_url = "https://genius.com" + path_lyrics
            page = requests.get(genius_url)
            html = BeautifulSoup(page.text, "html.parser")

            # Find the old or new version of the webpage
            old_div = html.find("div", class_="lyrics")
            new_div = html.find("div", class_="SongPageGrid-sc-1vi6xda-0 DGVcp Lyrics__Root-sc-1ynbvzw-0 jvlKWy")
            if old_div:
                lyrics = old_div.get_text()
            elif new_div:
                # Clean the lyrics since get_text() fails to convert "</br/>"
                lyrics = str(lyrics).replace('<br/>', '\n')
                lyrics = re.sub(r'(\<.*?\>)', '', lyrics)
            else:
                return await ctx.send(cmd_tran["msg_no_lyrics"])
            # If length is too long, the song does not contain lyrics
            if len(lyrics) > 6000:
                return await ctx.send(cmd_tran["msg_too_long"])
            # Get music details
            title = r["response"]["hits"][0]["result"]["full_title"]
            image = r["response"]["hits"][0]["result"]["header_image_url"]
            # Lyric found doesn't contain any arg given, warn the user
            if not any(x.lower() in title.lower() for x in music.split()):
                await ctx.send(cmd_tran["msg_not_match"])
                await ctx.send(cmd_tran["msg_result_found"].format(music))

            # Send an embed with lyrics
            embed = discord.Embed(color=0x11FFFF)
            embed.title = cmd_tran["msg_lyrics"].format(title)
            embed.description = None
            embed.set_thumbnail(url=image)
            # Every block of lyrics is added in a field
            for block in lyrics.split("\n\n")[1:-1]:
                splitted = block.split("\n", 1)
                if splitted[0] != "":
                    if not len(splitted) == 1:
                        if len(splitted[1]) >= 1024:
                            embed.add_field(name=splitted[0],
                                            value=splitted[1][0:1023])
                        else:
                            embed.add_field(name=splitted[0],
                                            value=splitted[1])
                    else:
                        # Filed contains nothing add notes
                        embed.add_field(name=splitted[0], value=":notes:" * 6)
            embed.set_footer(text=tran["GLOBAL"][lang_server]["requested_by"].format(ctx.message.author.name),
                             icon_url=ctx.message.author.avatar_url)
            await ctx.send(embed=embed)

def setup(client):
    client.add_cog(LyricsUtilities(client))
