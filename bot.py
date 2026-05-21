import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from github_fetcher import get_project_context
from pipeline_client import call_pipeline, call_followup

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# In-memory session store: maps user_id -> { project_context, last_analysis }
# Keeps conversation context without needing a database
sessions: dict[int, dict] = {}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ── Startup ──────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"✅ CodeCompass is online as {bot.user}")
    print(f"   RocketRide URL: {os.getenv('ROCKETRIDE_URL', 'http://localhost:5565')}")


# ── Helper: split long messages for Discord's 2000 char limit ─────────────────

def chunk_message(text: str, limit: int = 1900) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:limit])
        text = text[limit:]
    return chunks


# ── !analyze command ──────────────────────────────────────────────────────────

@bot.command(name="analyze")
async def analyze(ctx, *, input_text: str = ""):
    """
    Analyze a project. Usage:
      !analyze https://github.com/user/repo
      !analyze [paste your code here]
    """
    # Also check for code blocks in the message
    if not input_text:
        await ctx.send(
            "👋 **Welcome to CodeCompass!**\n\n"
            "Send me your project and I'll help you understand what you built.\n\n"
            "**Usage:**\n"
            "`!analyze https://github.com/yourname/yourrepo`\n"
            "or\n"
            "`!analyze` followed by pasting your code"
        )
        return

    # Show typing indicator while pipeline runs
    async with ctx.typing():
        thinking_msg = await ctx.send("🧭 **Analyzing your project...** This takes ~15 seconds.\n`Step 1/4: Fetching project context...`")

        try:
            # Step 1: Get project content (URL or paste)
            project_context, source_label = get_project_context(input_text)

            await thinking_msg.edit(content="🧭 **Analyzing your project...**\n`Step 2/4: Detecting technologies...`")

            # Step 2: Run the full RocketRide pipeline
            await thinking_msg.edit(content="🧭 **Analyzing your project...**\n`Step 3/4: Identifying knowledge gaps...`")

            result = await call_pipeline(project_context)

            await thinking_msg.edit(content="🧭 **Analyzing your project...**\n`Step 4/4: Generating your learning guide...`")

            # Store session for follow-up questions
            sessions[ctx.author.id] = {
                "project_context": project_context,
                "source_label": source_label,
                "last_analysis": result
            }

            # Delete the thinking message
            await thinking_msg.delete()

            # Send the result (split if needed)
            header = f"📍 *Source: `{source_label}`*\n\n"
            full_response = header + result
            for chunk in chunk_message(full_response):
                await ctx.send(chunk)

            # Add a footer prompt
            await ctx.send(
                "---\n"
                "💬 **Ask a follow-up question** by typing it directly, or use:\n"
                "`!ask What is React state management?`\n"
                "`!quiz` — Test your knowledge\n"
                "`!reset` — Start over with a new project"
            )

        except RuntimeError as e:
            await thinking_msg.delete()
            await ctx.send(f"⚠️ {e}")
        except Exception as e:
            await thinking_msg.delete()
            await ctx.send(f"❌ Something went wrong: `{e}`\nMake sure RocketRide is running in VS Code.")


# ── !ask command — follow-up questions ───────────────────────────────────────

@bot.command(name="ask")
async def ask(ctx, *, question: str):
    """Ask a follow-up question about your project."""
    session = sessions.get(ctx.author.id)
    if not session:
        await ctx.send(
            "❓ I don't have a project loaded for you yet.\n"
            "Use `!analyze <github_url_or_code>` first!"
        )
        return

    async with ctx.typing():
        thinking_msg = await ctx.send(f"💭 Thinking about: *{question[:80]}...*")
        try:
            result = await call_followup(
                question=question,
                project_context=session["project_context"],
                previous_analysis=session["last_analysis"]
            )
            await thinking_msg.delete()
            for chunk in chunk_message(result):
                await ctx.send(chunk)

        except RuntimeError as e:
            await thinking_msg.delete()
            await ctx.send(f"⚠️ {e}")


# ── !quiz command ─────────────────────────────────────────────────────────────

@bot.command(name="quiz")
async def quiz(ctx):
    """Generate a quick quiz question about your project's tech."""
    session = sessions.get(ctx.author.id)
    if not session:
        await ctx.send("❓ Use `!analyze` first, then I can quiz you on your project!")
        return

    async with ctx.typing():
        thinking_msg = await ctx.send("📝 Generating a quiz question for you...")
        try:
            result = await call_followup(
                question="Generate ONE multiple-choice quiz question (A/B/C/D) about the most important technology concept in this project. Make it practical and specific to what was actually built.",
                project_context=session["project_context"],
                previous_analysis=session["last_analysis"]
            )
            await thinking_msg.delete()
            await ctx.send(f"🧠 **Quick Quiz**\n\n{result}\n\n*Reply with `!ask A` (or B/C/D) to check your answer!*")

        except RuntimeError as e:
            await thinking_msg.delete()
            await ctx.send(f"⚠️ {e}")


# ── !reset command ────────────────────────────────────────────────────────────

@bot.command(name="reset")
async def reset(ctx):
    """Clear your current project session."""
    if ctx.author.id in sessions:
        del sessions[ctx.author.id]
    await ctx.send("🔄 Session cleared! Send a new project with `!analyze`.")


# ── !help override ────────────────────────────────────────────────────────────

@bot.command(name="compass")
async def compass_help(ctx):
    """Show CodeCompass help."""
    await ctx.send(
        "## 🧭 CodeCompass — Learn Through Building\n\n"
        "**Commands:**\n"
        "`!analyze <github_url>` — Analyze a GitHub repo\n"
        "`!analyze <paste code>` — Analyze pasted code\n"
        "`!ask <question>` — Ask a follow-up about your project\n"
        "`!quiz` — Get a quiz question on your project's tech\n"
        "`!reset` — Start over with a new project\n\n"
        "**Example:**\n"
        "`!analyze https://github.com/myname/myapp`\n\n"
        "*CodeCompass helps you understand what you built — not just that it works.*"
    )


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN not set in .env file!")
        exit(1)
    bot.run(DISCORD_TOKEN)
