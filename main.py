import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from aiohttp import web

# 1. 簡易Webサーバーの設定（Renderのポート検知用）
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Renderが指定する環境変数 PORT を取得（デフォルトは 10000）
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Webサーバーをポート {port} で起動しました。")

# 2. Botの初期設定とインテントの有効化
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"同期エラー: {e}")
    print(f"ログインしました: {bot.user.name} (ID: {bot.user.id})")


# ==========================================
# 認証用ビュー (ボタン)
# ==========================================
class VerifyView(discord.ui.View):
    def __init__(self, verify_role: discord.Role):
        super().__init__(timeout=None)
        self.verify_role = verify_role

    @discord.ui.button(label="✅ 認証する", style=discord.ButtonStyle.green, custom_id="persistent_verify_btn")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.verify_role in interaction.user.roles:
                await interaction.response.send_message("すでに認証は完了しています！", ephemeral=True)
            else:
                await interaction.user.add_roles(self.verify_role)
                await interaction.response.send_message("✅ 認証が完了しロールが付与されました！", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("⚠️ Botにロールを付与する権限がないか、役職の位置が低いです。", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ エラーが発生しました: {e}", ephemeral=True)


# ==========================================
# スラッシュコマンド
# ==========================================
@bot.tree.command(name="verify_setup", description="認証時に付与するロールを設定します。")
@app_commands.describe(role="付与したいロールを選択してください")
@app_commands.checks.has_permissions(administrator=True)
async def verify_setup(interaction: discord.Interaction, role: discord.Role):
    bot.verify_target_role = role
    await interaction.response.send_message(f"✅ 認証ロールを {role.mention} に設定しました。", ephemeral=True)

@bot.tree.command(name="verify_panel", description="認証パネルをチャンネルに送信します。")
@app_commands.checks.has_permissions(administrator=True)
async def verify_panel(interaction: discord.Interaction):
    target_role = getattr(bot, "verify_target_role", None)
    if not target_role:
        target_role = discord.utils.get(interaction.guild.roles, name="メンバー")
        if not target_role:
            await interaction.response.send_message("⚠️ 先に `/verify_setup` でロールを設定してください。", ephemeral=True)
            return

    embed = discord.Embed(title="🔒 サーバー認証", description="下のボタンを押して認証を完了させてください。", color=discord.Color.blue())
    view = VerifyView(target_role)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("認証パネルを送信しました！", ephemeral=True)

@verify_setup.error
@verify_panel.error
async def verify_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ 管理者権限が必要です。", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ エラー: {error}", ephemeral=True)


# 3. メインの起動処理（WebサーバーとBotを同時に非同期実行）
async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("エラー: DISCORD_TOKEN の環境変数が設定されていません。")
        return

    # Webサーバーをバックグラウンドで起動
    await start_web_server()

    # Botを起動
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
