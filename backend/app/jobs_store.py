import os
import json
import asyncio
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class JobStore:
    """Simple job storage for Railway deployment."""

    def __init__(self):
        self.store_dir = os.getenv("JOB_STORE_DIR", "/tmp/cinematrix_jobs")
        os.makedirs(self.store_dir, exist_ok=True)

    def create(self, job_id: str, data: Dict[str, Any]):
        """Create a new job record."""
        try:
            file_path = os.path.join(self.store_dir, f"{job_id}.json")
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Created job {job_id}")
        except Exception as e:
            logger.error(f"Failed to create job {job_id}: {e}")

    def update(self, job_id: str, data: Dict[str, Any]):
        """Update an existing job record."""
        try:
            file_path = os.path.join(self.store_dir, f"{job_id}.json")
            if not os.path.exists(file_path):
                logger.warning(f"Job {job_id} not found for update")
                return

            # Read existing data
            with open(file_path, "r") as f:
                existing_data = json.load(f)

            # Update with new data
            existing_data.update(data)

            # Write back
            with open(file_path, "w") as f:
                json.dump(existing_data, f, indent=2)

            logger.info(f"Updated job {job_id}")
        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {e}")

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data by ID."""
        try:
            file_path = os.path.join(self.store_dir, f"{job_id}.json")
            if not os.path.exists(file_path):
                return None

            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            return None

    def delete(self, job_id: str):
        """Delete a job record."""
        try:
            file_path = os.path.join(self.store_dir, f"{job_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted job {job_id}")
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")

    def list_jobs(self, status: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """List all jobs, optionally filtered by status."""
        try:
            jobs = {}
            for filename in os.listdir(self.store_dir):
                if filename.endswith(".json"):
                    job_id = filename[:-5]  # Remove .json extension
                    job_data = self.get(job_id)
                    if job_data:
                        if status is None or job_data.get("status") == status:
                            jobs[job_id] = job_data
            return jobs
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return {}

    def cleanup_old_jobs(self, days: int = 7):
        """Clean up jobs older than specified days."""
        try:
            import time
            cutoff_time = time.time() - (days * 24 * 60 * 60)

            for filename in os.listdir(self.store_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(self.store_dir, filename)
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        logger.info(f"Cleaned up old job file: {filename}")
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")

# Global instance
job_store = JobStore()

# Periodic cleanup task
async def cleanup_old_jobs_task():
    """Background task to cleanup old jobs."""
    while True:
        try:
            job_store.cleanup_old_jobs()
            await asyncio.sleep(86400)  # Run daily
        except Exception as e:
            logger.error(f"Job cleanup task error: {e}")
            await asyncio.sleep(3600)  # Retry in 1 hour

# Start cleanup task
def start_cleanup_task():
    """Start the background cleanup task."""
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            loop.create_task(cleanup_old_jobs_task())
        else:
            asyncio.create_task(cleanup_old_jobs_task())
    except Exception as e:
        logger.error(f"Failed to start cleanup task: {e}")