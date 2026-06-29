"""Bot instance manager - ensures only one bot instance runs at a time."""

import logging
import os
import signal
import time
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.models import BotInstance

logger = logging.getLogger(__name__)

PID_FILE = Path("/tmp/job_apply_bot.pid")


class BotInstanceManager:
    """Manages singleton bot instance - kills previous instance if new one starts."""

    @staticmethod
    def acquire_lock() -> bool:
        """
        Acquire bot lock. If another instance is running, kill it and take over.
        Returns True if lock acquired successfully.
        """
        if PID_FILE.exists():
            try:
                old_pid = int(PID_FILE.read_text().strip())
                if BotInstanceManager._process_exists(old_pid):
                    logger.info(f"Killing old bot instance (PID {old_pid})...")
                    try:
                        os.kill(old_pid, signal.SIGTERM)
                        time.sleep(2)  # Wait for graceful shutdown
                        if BotInstanceManager._process_exists(old_pid):
                            logger.warning(f"Forcing kill of old instance (PID {old_pid})...")
                            os.kill(old_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        logger.info(f"Old process (PID {old_pid}) already dead")
            except (ValueError, OSError) as e:
                logger.warning(f"Could not kill old instance: {e}")

        # Write new PID
        current_pid = os.getpid()
        PID_FILE.write_text(str(current_pid))
        logger.info(f"Bot instance lock acquired (PID {current_pid})")
        return True

    @staticmethod
    def release_lock() -> None:
        """Release bot lock on shutdown."""
        try:
            if PID_FILE.exists():
                PID_FILE.unlink()
            logger.info("Bot instance lock released")
        except OSError as e:
            logger.error(f"Error releasing lock: {e}")

    @staticmethod
    def _process_exists(pid: int) -> bool:
        """Check if process with given PID exists."""
        try:
            os.kill(pid, 0)  # Signal 0 checks existence without killing
            return True
        except (ProcessLookupError, OSError):
            return False

    @staticmethod
    def record_instance(db: Session, status: str, message: str = "") -> None:
        """Record bot instance lifecycle event in database."""
        try:
            instance = BotInstance(
                pid=os.getpid(),
                status=status,  # 'started', 'stopped', 'error'
                message=message,
                timestamp=datetime.utcnow(),
            )
            db.add(instance)
            db.commit()
            logger.info(f"Recorded bot instance: {status}")
        except Exception as e:
            logger.error(f"Failed to record instance: {e}")
            try:
                db.rollback()
            except:
                pass

    @staticmethod
    def cleanup_on_shutdown(db: Session) -> None:
        """Cleanup on bot shutdown."""
        BotInstanceManager.record_instance(db, "stopped", "Graceful shutdown")
        BotInstanceManager.release_lock()
