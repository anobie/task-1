import { Grid, List, ListItem, ListItemText, Typography } from "@mui/material";

import { getAuditLogs, getOrganizations } from "../../api/admin";
import { DashboardPanel } from "../../components/DashboardPanel";
import { ErrorBlock, LoadingBlock } from "../../components/StateBlock";
import { useAsyncResource } from "../../hooks/useAsyncResource";

export function AdminDashboard({ token }: { token: string }) {
  const orgs = useAsyncResource(() => getOrganizations(token), [token]);
  const logs = useAsyncResource(() => getAuditLogs(token), [token]);

  return (
    <Grid container spacing={2.5}>
      <Grid size={{ xs: 12, md: 5 }}>
        <DashboardPanel title="Organizations" subtitle="Governance scope and active campuses">
          {orgs.isLoading && <LoadingBlock label="Loading organizations" />}
          {orgs.error && <ErrorBlock message={orgs.error} />}
          {orgs.data && (
            <List dense>
              {orgs.data.map((org) => (
                <ListItem key={org.id} disablePadding>
                  <ListItemText primary={`${org.name} (${org.code})`} secondary={org.is_active ? "Active" : "Inactive"} />
                </ListItem>
              ))}
              {orgs.data.length === 0 && <Typography variant="body2">No organizations configured.</Typography>}
            </List>
          )}
        </DashboardPanel>
      </Grid>
      <Grid size={{ xs: 12, md: 7 }}>
        <DashboardPanel title="Audit Stream" subtitle="Recent privileged write operations">
          {logs.isLoading && <LoadingBlock label="Loading audit events" />}
          {logs.error && <ErrorBlock message={logs.error} />}
          {logs.data && (
            <List dense>
              {logs.data.map((log) => (
                <ListItem key={log.id} disablePadding>
                  <ListItemText primary={`${log.action} - ${log.entity_name}`} secondary={new Date(log.created_at).toLocaleString()} />
                </ListItem>
              ))}
              {logs.data.length === 0 && <Typography variant="body2">No audit events yet.</Typography>}
            </List>
          )}
        </DashboardPanel>
      </Grid>
    </Grid>
  );
}
