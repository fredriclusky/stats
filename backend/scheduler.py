from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Single shared scheduler instance — imported by main.py (to start/stop)
# and by sync.py (to reschedule after a manual sync).
scheduler = AsyncIOScheduler()
