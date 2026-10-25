import os
import random
import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput

# Botの初期設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"ログインしました: {bot.user.name} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Game(name="宣伝鯖 & マイクラ鯖 運営中！"))


# ==========================================
# 1. 認証機能 (普通・計算・キャプチャー)
# ==========================================

# 計算認証用モーダル
class MathModal(Modal, title="計算認証"):
    answer_input = TextInput(label="以下の計算結果を入力してください", placeholder="例: 12", required=True)

    def __init__(self, correct_answer: int):
        super().__init__()
        self.correct_answer = correct_answer

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_ans = int(self.answer_input.value)
            if user_ans == self.correct_answer:
                role = discord.utils.get(interaction.guild.roles, name="メンバー")
                if role:
                    await interaction.user.add_roles(role)
                    await interaction.response.send_message("✅ 計算認証に成功しました！ロールを付与しました。", ephemeral=True)
                else:
                    await interaction.response.send_message("⚠️ 「メンバー」ロールが見つかりません。", ephemeral=True)
            else:
                await interaction.response.send_message("❌ 計算が間違っています。もう一度パネルからやり直してください。", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ 半角の数字で入力してください。", ephemeral=True)

# キャプチャー認証用ビュー
class CaptchaView(View):
    def __init__(self, code: str):
        super().__init__(timeout=180)
        self.code = code

    @discord.ui.button(label="🔤 キャプチャー認証を行う", style=discord.ButtonStyle.blurple, custom_id="captcha_btn")
    async def captcha_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CaptchaModal(self.code))

class CaptchaModal(Modal, title="キャプチャー認証"):
    code_input = TextInput(label="表示された文字列をそのまま入力", placeholder="例: A3f9K", required=True)

    def __init__(self, correct_code: str):
        super().__init__()
        self.correct_code = correct_code

    async def on_submit(self, interaction: discord.Interaction):
        if self.code_input.value == self.correct_code:
            role = discord.utils.get(interaction.guild.roles, name="メンバー")
            if role:
                await interaction.user.add_roles(role)
                await interaction.response.send_message("✅ キャプチャー認証に成功しました！", ephemeral=True)
            else:
                await interaction.response.send_message("⚠️ 「メンバー」ロールが見つかりません。", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 文字列が一致しません。", ephemeral=True)

# 認証パネル全体ビュー
class VerificationPanelView(View):
    def __init__(self, auth_type: str):
        super().__init__(timeout=None)
        self.auth_type = auth_type

        if auth_type == "normal":
            btn = Button(label="✅ 通常認証", style=discord.ButtonStyle.green, custom_id="verify_normal")
            btn.callback = self.normal_callback
            self.add_item(btn)
        elif auth_type == "math":
            btn = Button(label="🔢 計算認証", style=discord.ButtonStyle.blurple, custom_id="verify_math")
            btn.callback = self.math_callback
            self.add_item(btn)
        elif auth_type == "captcha":
            btn = Button(label="🔤 キャプチャー認証", style=discord.ButtonStyle.grey, custom_id="verify_captcha")
            btn.callback = self.captcha_callback
            self.add_item(btn)

    async def normal_callback(self, interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, name="メンバー")
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ 認証が完了しました！", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ ロールが見つかりません。", ephemeral=True)

    async def math_callback(self, interaction: discord.Interaction):
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        ans = num1 + num2
        await interaction.response.send_modal(MathModal(ans))
        # 注: モーダル連携の都合上、プロンプトで数式を提示する形にします
        await interaction.followup.send(f"問題: {num1} + {num2} の答えをモーダルに入力してください。", ephemeral=True)

    async def captcha_callback(self, interaction: discord.Interaction):
        code = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
        view = CaptchaView(code)
        await interaction.response.send_message(f"認証コード: **`{code}`** （下のボタンから入力してください）", view=view, ephemeral=True)

@bot.command(name="認証パネル生成")
@commands.has_permissions(administrator=True)
async def create_verification(ctx, auth_type: str = "normal"):
    """auth_typeには normal, math, captcha のいずれかを指定"""
    if auth_type not in ["normal", "math", "captcha"]:
        await ctx.send("指定できるタイプは `normal`, `math`, `captcha` です。")
        return
    
    embed = discord.Embed(title="サーバー認証パネル", description=f"形式: **{auth_type}**\nボタンを押して認証を進めてください。", color=discord.Color.blue())
    view = VerificationPanelView(auth_type)
    await ctx.send(embed=embed, view=view)


# ==========================================
# 2. チケットパネル機能
# ==========================================

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 チケットを作成する", style=discord.ButtonStyle.blurple, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        category = discord.utils.get(guild.categories, name="チケット")
        if not category:
            category = await guild.create_category("チケット")

        channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites, category=category)
        
        close_view = TicketCloseView()
        await channel.send(f"{interaction.user.mention}さん、ようこそ！スタッフが対応します。", view=close_view)
        await interaction.response.send_message(f"チケットチャンネルを作成しました: {channel.mention}", ephemeral=True)

class TicketCloseView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 チケットを閉じる", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("チャンネルを削除します...")
        await interaction.channel.delete()

@bot.command(name="チケットパネル生成")
@commands.has_permissions(administrator=True)
async def create_ticket_panel(ctx):
    embed = discord.Embed(title="お問い合わせ・宣伝申請", description="ボタンを押すと専用のチャンネルが作成されます。", color=discord.Color.green())
    view = TicketView()
    await ctx.send(embed=embed, view=view)


# ==========================================
# 3. 宣伝鯖・マイクラ鯖向けの基本コマンド（拡張用サンプル）
# ==========================================

@bot.command(name="宣伝ルール")
async def promo_rules(ctx):
    embed = discord.Embed(title="📢 宣伝サーバーのルール", description="1. スパム行為の禁止\n2. 規約遵守\n3. クールダウンを守る", color=discord.Color.orange())
    await ctx.send(embed=embed)

@bot.command(name="マイクラ状況")
async def mc_status(ctx):
    embed = discord.Embed(title="⛏️ マイクラサーバー情報", description="IP: `play.example.com`\nバージョン: `1.20.4`\n状態: `🟢 オンライン`", color=discord.Color.dark_green())
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"Pong! 🏓 `{round(bot.latency * 1000)}ms`")


# Bot起動
bot.run(os.getenv("DISCORD_TOKEN"))
