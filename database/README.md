# Database

## Apply schema
1. Configure `DATABASE_URL` in `.env`.
2. Run:
   - `python3 database/setup_db.py`

## Notes
- Schema is normalized for MVP analytics workflows.
- `team_game_results` view simplifies win/loss and team-level trend queries.
