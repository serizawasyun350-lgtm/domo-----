import os
import discord
from discord import app_commands
from discord.ext import commands

# 1. Botの初期設定とインテントの有効化
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# プレフィックスとインテントの設定
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    # スラッシュコマンドをDiscord側に同期する
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
                await interaction.response.send_message("✅ 認証が完了し、ロールが付与されました！", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("⚠️ Botにロールを付与する権限がないか、Botの役職位置が対象ロールより低いです。", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ エラーが発生しました: {e}", ephemeral=True)


# ==========================================
# スラッシュコマンド
# ==========================================

# 1. /verify_setup [role] : 認証で付与するロールを事前に設定
@bot.tree.command(name="verify_setup", description="認証時に付与するロールを設定します。")
@app_commands.describe(role="付与したいロールを選択してください")
@app_commands.checks.has_permissions(administrator=True)
async def verify_setup(interaction: discord.Interaction, role: discord.Role):
    bot.verify_target_role = role
    await interaction.response.send_message(f"✅ 認証ロールを {role.mention} に設定しました。次に `/verify_panel` でパネルを生成してください。", ephemeral=True)

# 2. /verify_panel : 認証パネルを送信
@bot.tree.command(name="verify_panel", description="認証パネルをチャンネルに送信します。")
@app_commands.checks.has_permissions(administrator=True)
async def verify_panel(interaction: discord.Interaction):
    # 設定されたロールを取得、なければ「メンバー」を探す
    target_role = getattr(bot, "verify_target_role", None)
    if not target_role:
        target_role = discord.utils.get(interaction.guild.roles, name="メンバー")
        if not target_role:
            await interaction.response.send_message("⚠️ 先に `/verify_setup` でロールを設定するか、サーバーに「メンバー」ロールを作成してください。", ephemeral=True)
            return

    embed = discord.Embed(
        title="🔒 サーバー認証",
        description="下のボタンを押して認証を完了させてください。",
        color=discord.Color.blue()
    )
    view = VerifyView(target_role)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("認証パネルを送信しました！", ephemeral=True)

# 権限エラーなどのハンドリング
@verify_setup.error
@verify_panel.error
async def verify_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ このコマンドを実行する権限がありません（管理者限定）。", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ コマンド実行中にエラーが発生しました: {error}", ephemeral=True)


# Botの起動（環境変数からトークンを取得）
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("エラー: DISCORD_TOKEN の環境変数が設定されていません。")
else:
    bot.run(TOKEN)
