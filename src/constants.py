"""Constants for the GitHub App."""

# Bot comment templates
BOT_COMMENT_TEMPLATE = """🤖 **Bot Message**

Background processing completed successfully:

1. ✅ Cloned repository to `{clone_dir}`
2. ✅ Checked out branch: `{branch}`
3. ✅ Analyzed repository structure: **{file_count} files** in **{dir_count} directories**
4. ✅ Ready for code analysis

📅 Timestamp: {timestamp}"""
