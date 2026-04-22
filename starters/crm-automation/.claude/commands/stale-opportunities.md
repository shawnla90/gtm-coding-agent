Run the stale-opportunity check and summarize the result.

Steps:

1. Read `starters/crm-automation/stale_opportunity_check.py` so you understand what it does and what flags it takes.
2. Execute the script with `--dry-run` first:
   ```bash
   cd starters/crm-automation && python stale_opportunity_check.py --days 60 --stages qualifiedtobuy,presentationscheduled --dry-run
   ```
3. Read the stdout. For each deal marked `actionable`, show me:
   - Deal name + amount
   - The one-sentence narrative the script generated
   - Your recommendation: re-engage now, re-assign to a different rep, or close-lost with reason
4. Ask me whether to re-run without `--dry-run` to write the `agent_*` properties back to HubSpot.
5. If yes, run the live command and confirm the count of deals updated.

Do not write to HubSpot without explicit confirmation in step 4.
