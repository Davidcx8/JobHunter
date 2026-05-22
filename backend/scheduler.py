"""
JobHunter Pro - Automated Scheduler
Runs periodic scraping, calculates skills matching scores, and triggers webhook alerts.
"""

import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

# Adjust path to find backend packages if run from parent folder
import sys
sys.path.insert(0, os.path.dirname(__file__))

# Load configurations
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "config.env"))
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import required modules
try:
    import schedule
except ImportError:
    logger.error("The 'schedule' library is not installed. Run 'pip install schedule' or add it to dependencies.")
    sys.exit(1)

from db_manager import DatabaseManager
from matching_engine import MatchingEngine
from integrations import WebhookDispatcher

# Scrapers
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.indeed_scraper import IndeedScraper
from scrapers.remotive_scraper import RemotiveScraper
from scrapers.weworkremotely_scraper import WeWorkRemotelyScraper
from scrapers.glassdoor_scraper import GlassdoorScraper
from scrapers.ziprecruiter_scraper import ZipRecruiterScraper

# Initialize database manager
db = DatabaseManager(db_path=os.getenv("DB_PATH", "./data/jobhunter.db"))

def job_daily_scrape():
    """Execute scheduled crawling of multiple channels"""
    logger.info("=== Starting Scheduled Scrape ===")
    
    keywords = os.getenv("SCRAPE_KEYWORDS", "Python Developer, Full Stack, Remote")
    limit = int(os.getenv("SCRAPE_LIMIT", "15"))
    location = os.getenv("SCRAPE_LOCATION", "remote")
    
    # Load user skills for matching
    profile = db.get_profile()
    user_skills = profile.get("skills", [])
    
    scrapers = {
        'linkedin': LinkedInScraper(),
        'indeed': IndeedScraper(),
        'remotive': RemotiveScraper(),
        'weworkremotely': WeWorkRemotelyScraper(),
        'glassdoor': GlassdoorScraper(),
        'ziprecruiter': ZipRecruiterScraper()
    }
    
    total_found = 0
    for name, scraper in scrapers.items():
        try:
            logger.info(f"Crawling jobs from: {name}...")
            jobs = scraper.search(keywords=keywords, location=location, limit=limit)
            logger.info(f"Scraped {len(jobs)} candidates from {name}")
            
            for job in jobs:
                # Calculate matching score dynamically
                score, matching, missing = MatchingEngine.calculate_score(
                    job.get("title", ""),
                    job.get("description", ""),
                    job.get("requirements", ""),
                    user_skills
                )
                job["match_score"] = score
                job["status"] = "new"
                job["source"] = name
                
                # Add to local SQLite DB
                saved = db.add_job(job)
                
                # Trigger alert if match score is high
                if score >= 80.0:
                    try:
                        WebhookDispatcher.send_notification(saved)
                    except Exception as webhook_err:
                        logger.error(f"Error triggering webhook for high-match job: {webhook_err}")
                        
            total_found += len(jobs)
        except Exception as e:
            logger.error(f"Error during scheduled scraping for source {name}: {e}")
            
    logger.info(f"=== Scheduled Scrape Complete. Processed {total_found} vacancies. ===")

def job_update_metrics():
    """Trigger daily metrics aggregation"""
    logger.info("Recalculating and aggregating system metrics...")
    try:
        metrics = db.get_dashboard_metrics()
        # Save metrics count in DB
        today = datetime.now().strftime("%Y-%m-%d")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO metrics (date, jobs_viewed, jobs_saved, applications_sent)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                jobs_viewed=excluded.jobs_viewed,
                jobs_saved=excluded.jobs_saved,
                applications_sent=excluded.applications_sent
            """, (
                today,
                metrics.get("jobs", {}).get("total", 0),
                metrics.get("jobs", {}).get("total", 0),
                metrics.get("applications", {}).get("total", 0)
            ))
            conn.commit()
        logger.info(f"Metrics synced for date {today}")
    except Exception as e:
        logger.error(f"Error executing metrics collection: {e}")

def job_email_reminder():
    """Perform checks on pending job applications and log reminders"""
    logger.info("Running applications follow-up checking...")
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        apps = db.get_applications()
        for app in apps:
            if app.get("follow_up_date") == today:
                logger.info(f"👉 FOLLOW-UP REMINDER: Send application updates to {app.get('company')} for position '{app.get('position')}'")
    except Exception as e:
        logger.error(f"Error running follow-up reminder job: {e}")

def run_scheduler():
    """Launch scheduling loop"""
    logger.info("JobHunter Pro automated background scheduler started.")
    
    # Configure schedules
    schedule.every().day.at("09:00").do(job_daily_scrape)
    schedule.every().day.at("08:00").do(job_update_metrics)
    schedule.every().day.at("10:00").do(job_email_reminder)
    
    # Scrape cycle every 6 hours
    schedule.every(6).hours.do(job_daily_scrape)
    
    logger.info("Schedule triggers loaded. Press Ctrl+C to terminate.")
    
    # Run once on startup to verify setup
    logger.info("Performing warm-up metrics verification...")
    job_update_metrics()
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler process interrupted by user.")

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════╗
║     JOBHUNTER PRO - AUTOMATED SCHEDULER      ║
╠═══════════════════════════════════════════════╣
║  📅 Daily scrape at 09:00                   ║
║  📊 Metrics update at 08:00                 ║
║  📧 Reminders at 10:00                      ║
║  🔄 Full scrape every 6 hours               ║
╚═══════════════════════════════════════════════╝
    """)
    run_scheduler()