@echo off
REM RenewCast Demo Sequence — run this during the hackathon presentation
REM Each step is timed. Read the instructions out loud while it runs.

echo.
echo ============================================
echo  STEP 1: Inject cloud event on RJ01
echo  SAY: "Watch what happens when cloud cover
echo        hits the Rajasthan plant..."
echo ============================================
docker compose run --rm pathway_pipeline python scripts/inject_event.py --type=cloud --plant=RJ01 --severity=high
echo.
echo Wait 15 seconds then press any key for Step 2...
pause

echo.
echo ============================================
echo  STEP 2: Inject inverter fault on GJ01
echo  SAY: "Now I'll simulate an inverter
echo        degradation on the Gujarat plant..."
echo ============================================
docker compose run --rm pathway_pipeline python scripts/inject_event.py --type=inverter_fault --plant=GJ01
echo.
echo Wait 20 seconds for anomaly report then press any key for Step 3...
pause

echo.
echo ============================================
echo  STEP 3: Update regulatory document
echo  SAY: "Now watch the document store
echo        pick up a new CERC regulation..."
echo ============================================
echo CERC EMERGENCY CIRCULAR 2025-02: During high renewable penetration periods above 60 percent, gas backup must be pre-positioned 20 minutes before forecast drop. This supersedes Section 4.2 ramp event protocol. Effective immediately. >> docs\cerc_merit_order_2025.txt
echo Document updated. Watch the pipeline logs for re-indexing message.
echo.
echo Wait 10 seconds then press any key to clear all events...
pause

echo.
echo ============================================
echo  STEP 4: Clear all events
echo  SAY: "System recovers automatically..."
echo ============================================
docker compose run --rm pathway_pipeline python scripts/inject_event.py --clear
echo.
echo Demo complete. All events cleared.
pause
