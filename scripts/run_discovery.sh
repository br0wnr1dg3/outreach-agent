#!/bin/bash
# Discovery agent runner for cron
# Runs at 9am weekdays to find new leads

set -e

# Change to project directory
cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate

# Load environment
source .venv/bin/activate

# Run the agent
python run_agent.py >> logs/discovery_$(date +%Y-%m-%d).log 2>&1
