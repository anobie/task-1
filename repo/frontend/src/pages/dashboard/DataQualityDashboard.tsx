import { Grid, List, ListItem, ListItemText, Typography } from "@mui/material";

import { getQualityReport, getQuarantine } from "../../api/dataQuality";
import { DashboardPanel } from "../../components/DashboardPanel";
import { ErrorBlock, LoadingBlock } from "../../components/StateBlock";
import { useAsyncResource } from "../../hooks/useAsyncResource";

export function DataQualityDashboard({ token }: { token: string }) {
  const quarantine = useAsyncResource(() => getQuarantine(token), [token]);
  const report = useAsyncResource(() => getQualityReport(token), [token]);

  return (
    <Grid container spacing={2.5}>
      <Grid size={{ xs: 12, md: 7 }}>
        <DashboardPanel title="Quarantine Queue" subtitle="Pending records blocked by quality controls">
          {quarantine.isLoading && <LoadingBlock label="Loading quarantine entries" />}
          {quarantine.error && <ErrorBlock message={quarantine.error} />}
          {quarantine.data && (
            <List dense>
              {quarantine.data.map((item) => (
                <ListItem key={item.id} disablePadding>
                  <ListItemText primary={`${item.entity_type} #${item.id}`} secondary={`Status: ${item.status} | Score: ${item.quality_score}`} />
                </ListItem>
              ))}
              {quarantine.data.length === 0 && <Typography variant="body2">No quarantined records.</Typography>}
            </List>
          )}
        </DashboardPanel>
      </Grid>
      <Grid size={{ xs: 12, md: 5 }}>
        <DashboardPanel title="Quality Report" subtitle="Entity-level quality trend snapshot">
          {report.isLoading && <LoadingBlock label="Loading quality report" />}
          {report.error && <ErrorBlock message={report.error} />}
          {report.data && (
            <List dense>
              {report.data.map((item) => (
                <ListItem key={item.entity_type} disablePadding>
                  <ListItemText
                    primary={item.entity_type}
                    secondary={`Open items: ${item.open_items} | Avg score: ${item.avg_quality_score.toFixed(2)}`}
                  />
                </ListItem>
              ))}
              {report.data.length === 0 && <Typography variant="body2">No report data available.</Typography>}
            </List>
          )}
        </DashboardPanel>
      </Grid>
    </Grid>
  );
}
