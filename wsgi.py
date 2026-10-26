"""
StockTrade Production WSGI Entry Point (wsgi.py)
Used by Gunicorn, uWSGI, or Waitress in containerized or cloud deployments.
"""
import os
import sys
from app import create_app
from services.market_simulator import MarketSimulator

# Initialize application using the active environment configuration
env = os.getenv("FLASK_ENV", "production")
app = create_app(env)

# Start market simulator background worker if enabled
if os.getenv("START_SIMULATOR", "true").lower() in ("true", "1", "yes"):
    try:
        sim = MarketSimulator.get_instance()
        sim.start()
        app.logger.info("MarketSimulator background worker started.")
    except Exception as ex:
        app.logger.warning(f"MarketSimulator background worker could not start: {ex}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
