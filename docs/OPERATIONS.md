# Operations

- **[backup_dump.sh]** Creates a compressed dump and receipt (SHA256, row counts).
- **[backup_rotate.sh]** Keeps 7 daily, 8 weekly, monthly forever.
- **Restore drill**:
```
createdb sa_portal_drill
pg_restore -d sa_portal_drill $HOME/Backups/sa-portal/db/daily/<latest>.dump
# compare row counts, then
dropdb sa_portal_drill
```
